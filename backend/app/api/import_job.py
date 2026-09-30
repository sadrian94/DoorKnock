import asyncio
import ipaddress
import json
import socket
import uuid
import zlib
from dataclasses import dataclass
from ..clock import utc_now
from typing import Optional, Dict, Any
from urllib.parse import quote, unquote, urljoin, urlsplit
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import httpcore
from bs4 import BeautifulSoup
from ..ai.provider import require_ai_client
from ..ai.gemini import GeminiError
from ..ai.codex import CodexError
from ..ai.analyzer import analyze_job_posting
from ..database import get_db

router = APIRouter(prefix="/api/jobs", tags=["import"])

MIN_JOB_TEXT_LENGTH = 50
MAX_FETCH_BYTES = 2 * 1024 * 1024
MAX_FETCH_REDIRECTS = 5
FETCH_TOTAL_TIMEOUT_SECONDS = 30.0
FETCH_TIMEOUT_SECONDS = 20.0

class AnalyzeRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None

class ImportConfirmedJobRequest(BaseModel):
    title: str
    company: str
    company_url: Optional[str] = None
    location: Optional[str] = None
    workplace_type: Optional[str] = "onsite"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "USD"
    salary_interval: Optional[str] = "year"
    job_url: Optional[str] = None
    job_description: str
    job_brief: Optional[str] = None
    suitability_score: Optional[float] = None
    suitability_reason: Optional[str] = None
    analysis_json: Optional[str] = None
    source: str = "direct_import"

@dataclass(frozen=True)
class FetchedJobText:
    text: str
    extraction_method: str


class _HttpcoreResponseStream(httpx.AsyncByteStream):
    def __init__(self, stream):
        self._stream = stream

    async def __aiter__(self):
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


class _PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Dial only the address set checked for this one HTTP request."""

    def __init__(self, expected_host: str, expected_port: int, addresses: list[str]):
        self._expected_host = expected_host.rstrip(".").lower()
        self._expected_port = expected_port
        self._addresses = addresses
        self._backend = httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host.rstrip(".").lower() != self._expected_host or port != self._expected_port:
            raise httpcore.ConnectError("Connection target was not validated")

        last_error = None
        for address in self._addresses:
            try:
                return await self._backend.connect_tcp(
                    host=address,
                    port=port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise httpcore.ConnectError("No validated address is available")

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise httpcore.ConnectError("Unix socket connections are disabled")

    async def sleep(self, seconds):
        await self._backend.sleep(seconds)


class _PinnedHTTPTransport(httpx.AsyncBaseTransport):
    """HTTPX adapter backed by httpcore's public custom-network-backend API."""

    def __init__(self, host: str, port: int, addresses: list[str]):
        self._pool = httpcore.AsyncConnectionPool(
            max_connections=1,
            max_keepalive_connections=0,
            network_backend=_PinnedNetworkBackend(host, port, addresses),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        try:
            response = await self._pool.handle_async_request(core_request)
        except (
            httpcore.TimeoutException,
            httpcore.NetworkError,
            httpcore.ProtocolError,
            httpcore.ProxyError,
            httpcore.ConnectionNotAvailable,
        ) as exc:
            raise httpx.RequestError(str(exc), request=request) from exc
        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            stream=_HttpcoreResponseStream(response.stream),
            extensions=response.extensions,
            request=request,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()


def _clean_html_text(value: str) -> str:
    fragment = BeautifulSoup(value, "html.parser")
    for tag in fragment(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = [line.strip() for line in fragment.get_text(separator="\n").splitlines() if line.strip()]
    return "\n".join(lines)


def _clean_element_text(element: Any) -> str:
    for tag in element(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = [line.strip() for line in element.get_text(separator="\n").splitlines() if line.strip()]
    return "\n".join(lines)


def _iter_json_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_json_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_json_objects(child)


def _extract_jsonld_job_description(soup: BeautifulSoup) -> Optional[str]:
    for script in soup.select('script[type="application/ld+json"]'):
        raw_json = script.string or script.get_text()
        try:
            payload = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError):
            continue

        for item in _iter_json_objects(payload):
            posting_type = item.get("@type", [])
            types = posting_type if isinstance(posting_type, list) else [posting_type]
            type_names = {
                str(value).rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
                for value in types
            }
            if "jobposting" not in type_names:
                continue

            description = item.get("description")
            if isinstance(description, str):
                text = _clean_html_text(description)
                if len(text) >= MIN_JOB_TEXT_LENGTH:
                    return text
    return None


def _ashby_job_board_name(url: str) -> Optional[str]:
    parsed = urlsplit(url)
    if (parsed.hostname or "").lower() != "jobs.ashbyhq.com":
        return None
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    return path_parts[0] if len(path_parts) >= 2 else None


def _normalized_path(url: str) -> str:
    return urlsplit(url).path.rstrip("/")


def _normalize_fetch_url(url: str) -> httpx.URL:
    try:
        target = httpx.URL(url.strip())
    except (TypeError, ValueError, httpx.InvalidURL) as exc:
        raise HTTPException(status_code=400, detail="Please provide a valid public HTTP or HTTPS URL") from exc

    if target.scheme not in ("http", "https") or not target.host:
        raise HTTPException(status_code=400, detail="Please provide a valid public HTTP or HTTPS URL")
    if target.username or target.password:
        raise HTTPException(status_code=400, detail="Credentials are not allowed in a job page URL")

    expected_port = 80 if target.scheme == "http" else 443
    if target.port is not None and target.port != expected_port:
        raise HTTPException(status_code=400, detail="Job page URLs must use the standard HTTP or HTTPS port")
    return target.copy_with(fragment=None)


async def _resolve_dns_addresses(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    lookup_host = host.rstrip(".") + "."
    records = await loop.getaddrinfo(lookup_host, port, type=socket.SOCK_STREAM)
    return [record[4][0] for record in records]


def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if not address.is_global:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped and not address.ipv4_mapped.is_global:
            return False
        if address in ipaddress.ip_network("64:ff9b::/96"):
            embedded_ipv4 = ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
            return embedded_ipv4.is_global
        if address.sixtofour and not address.sixtofour.is_global:
            return False
        if address.teredo and not all(ip.is_global for ip in address.teredo):
            return False
    return True


async def _resolve_public_addresses(host: str, port: int) -> list[str]:
    """Resolve a host once and reject the entire answer if any address is non-public."""
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        try:
            addresses = await _resolve_dns_addresses(host, port)
        except (OSError, UnicodeError) as exc:
            raise HTTPException(status_code=400, detail="Could not resolve the job page host") from exc
    else:
        addresses = [str(literal)]

    public_addresses = []
    for raw_address in addresses:
        try:
            address = ipaddress.ip_address(raw_address.split("%", 1)[0])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="The job page host returned an invalid address") from exc
        if not _is_public_address(address):
            raise HTTPException(status_code=400, detail="The job page URL must resolve only to public addresses")
        normalized = str(address)
        if normalized not in public_addresses:
            public_addresses.append(normalized)

    if not public_addresses:
        raise HTTPException(status_code=400, detail="The job page host did not resolve to a public address")
    return public_addresses


def _create_fetch_client(target: httpx.URL, addresses: list[str], headers: dict[str, str]) -> httpx.AsyncClient:
    transport = _PinnedHTTPTransport(target.host, target.port or (80 if target.scheme == "http" else 443), addresses)
    safe_headers = {"Accept-Encoding": "identity", **headers}
    return httpx.AsyncClient(
        transport=transport,
        timeout=FETCH_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
        headers=safe_headers,
    )


async def _read_limited_response(response: httpx.Response) -> bytes:
    declared_length = response.headers.get("content-length")
    if declared_length:
        try:
            if int(declared_length) > MAX_FETCH_BYTES:
                raise HTTPException(status_code=400, detail="The job page exceeded the response size limit")
        except ValueError:
            pass

    encoding = response.headers.get("content-encoding", "identity").strip().lower()
    if encoding in ("", "identity"):
        decoder = None
    elif encoding == "gzip":
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decoder = zlib.decompressobj()
    else:
        raise HTTPException(status_code=400, detail="The job page uses an unsupported compression format")

    chunks = bytearray()
    received_bytes = 0

    def append_limited(chunk: bytes) -> None:
        if len(chunks) + len(chunk) > MAX_FETCH_BYTES:
            raise HTTPException(status_code=400, detail="The job page exceeded the response size limit")
        chunks.extend(chunk)

    async for raw_chunk in response.aiter_raw():
        received_bytes += len(raw_chunk)
        if received_bytes > MAX_FETCH_BYTES:
            raise HTTPException(status_code=400, detail="The job page exceeded the response size limit")
        if decoder is None:
            append_limited(raw_chunk)
            continue

        pending = raw_chunk
        while pending:
            max_output = max(1, MAX_FETCH_BYTES - len(chunks) + 1)
            append_limited(decoder.decompress(pending, max_output))
            pending = decoder.unconsumed_tail

    if decoder is not None:
        while True:
            max_output = max(1, MAX_FETCH_BYTES - len(chunks) + 1)
            decoded = decoder.decompress(b"", max_output)
            if not decoded:
                break
            append_limited(decoded)
        if not decoder.eof or decoder.unused_data:
            raise HTTPException(status_code=400, detail="The job page returned invalid compressed content")
    return bytes(chunks)


async def _fetch_public_page(url: str, headers: Optional[dict[str, str]] = None) -> httpx.Response:
    request_headers = headers or {}
    current = _normalize_fetch_url(url)
    visited = set()

    try:
        async with asyncio.timeout(FETCH_TOTAL_TIMEOUT_SECONDS):
            for redirect_count in range(MAX_FETCH_REDIRECTS + 1):
                target = _normalize_fetch_url(str(current))
                target_key = str(target)
                if target_key in visited:
                    raise HTTPException(status_code=400, detail="The job page redirected in a loop")
                visited.add(target_key)

                port = target.port or (80 if target.scheme == "http" else 443)
                addresses = await _resolve_public_addresses(target.host, port)
                request = httpx.Request("GET", target, headers=request_headers)
                async with _create_fetch_client(target, addresses, request_headers) as client:
                    async with client.stream("GET", target, follow_redirects=False) as response:
                        if response.status_code in (301, 302, 303, 307, 308):
                            location = response.headers.get("location")
                            if location:
                                if redirect_count >= MAX_FETCH_REDIRECTS:
                                    raise HTTPException(status_code=400, detail="The job page exceeded the redirect limit")
                                current = _normalize_fetch_url(urljoin(str(target), location))
                                continue

                        content = await _read_limited_response(response)
                        return httpx.Response(
                            status_code=response.status_code,
                            headers=response.headers,
                            content=content,
                            request=request,
                        )
    except HTTPException:
        raise
    except TimeoutError as exc:
        raise HTTPException(status_code=400, detail="Fetching the job page exceeded the time limit") from exc
    except (httpx.RequestError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not connect to the job page. Check the URL or paste the job description below.",
        ) from exc

    raise HTTPException(status_code=400, detail="The job page exceeded the redirect limit")


async def _fetch_ashby_job_description(url: str) -> Optional[str]:
    board_name = _ashby_job_board_name(url)
    if not board_name:
        return None

    endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{quote(board_name, safe='')}"
    try:
        response = await _fetch_public_page(endpoint, {"Accept": "application/json"})
    except HTTPException as exc:
        if exc.detail == "The job page exceeded the response size limit":
            raise
        return None

    if response.status_code != 200:
        return None

    try:
        payload = response.json()
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    except (ValueError, AttributeError):
        return None
    if not isinstance(jobs, list):
        return None

    target_path = _normalized_path(url)
    target_job_id = target_path.rsplit("/", 1)[-1]
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_url = job.get("jobUrl")
        if not isinstance(job_url, str):
            continue
        if (urlsplit(job_url).hostname or "").lower() != "jobs.ashbyhq.com":
            continue
        job_path = _normalized_path(job_url)
        if job_path != target_path and job_path.rsplit("/", 1)[-1] != target_job_id:
            continue

        description = job.get("descriptionPlain")
        if isinstance(description, str):
            text = _clean_html_text(description)
            if len(text) >= MIN_JOB_TEXT_LENGTH:
                return text
        description_html = job.get("descriptionHtml")
        if isinstance(description_html, str):
            text = _clean_html_text(description_html)
            if len(text) >= MIN_JOB_TEXT_LENGTH:
                return text
    return None


def _extract_ats_description(soup: BeautifulSoup, hostname: str) -> Optional[FetchedJobText]:
    if hostname.endswith(".myworkdayjobs.com") or hostname == "myworkdayjobs.com":
        selectors = (
            '[data-automation-id="jobPostingDescription"]',
            "#job-description",
            "#jobDescriptionText",
            ".job-description",
            ".jobDescription",
        )
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = _clean_element_text(element)
                if len(text) >= MIN_JOB_TEXT_LENGTH:
                    return FetchedJobText(text, "Workday job description")

    description_selectors = (
        '[itemprop="description"]',
        "#job-description",
        "#jobDescriptionText",
        ".job-description",
        ".jobDescription",
        ".posting-description",
    )
    for selector in description_selectors:
        element = soup.select_one(selector)
        if element:
            text = _clean_element_text(element)
            if len(text) >= MIN_JOB_TEXT_LENGTH:
                return FetchedJobText(text, "job description section")
    return None


def _is_access_wall(text: str) -> bool:
    normalized = text.lower()
    markers = (
        "authwall",
        "security check",
        "verify you are human",
        "checking your browser",
        "enable javascript and cookies to continue",
        "captcha",
    )
    return any(marker in normalized for marker in markers) or (
        "sign in" in normalized and "join linkedin" in normalized
    )


def _fetch_http_error(status_code: int) -> HTTPException:
    if status_code in (401, 403, 429):
        detail = (
            f"The job site denied the fetch request (HTTP {status_code}). "
            "If the posting opens in your browser, copy its job description and paste it below."
        )
    elif status_code == 404:
        detail = "The job page was not found (HTTP 404). Check the URL or paste the job description below."
    else:
        detail = f"The job site returned HTTP {status_code}. Please try again or paste the job description below."
    return HTTPException(status_code=400, detail=detail)


async def fetch_url_page(url: str) -> FetchedJobText:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    safe_url = str(_normalize_fetch_url(url))
    ashby_text = await _fetch_ashby_job_description(safe_url)
    if ashby_text:
        return FetchedJobText(ashby_text, "Ashby job posting")

    response = await _fetch_public_page(safe_url, headers)
    if response.status_code != 200:
        raise _fetch_http_error(response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(separator="\n", strip=True)
    if _is_access_wall(page_text):
        raise HTTPException(
            status_code=400,
            detail=(
                "This job page requires sign-in or blocks automated access. "
                "Copy the job description from your browser and paste it below."
            ),
        )

    structured_description = _extract_jsonld_job_description(soup)
    if structured_description:
        return FetchedJobText(structured_description, "structured job data")

    hostname = (urlsplit(str(response.url)).hostname or "").lower()
    ats_description = _extract_ats_description(soup, hostname)
    if ats_description:
        return ats_description

    for selector in ("main", "article", '[role="main"]'):
        element = soup.select_one(selector)
        if element:
            text = _clean_element_text(element)
            if len(text) >= MIN_JOB_TEXT_LENGTH:
                return FetchedJobText(text, "main page content")

    # Last resort for postings that don't mark up their description semantically.
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)
    if len(cleaned_text) < MIN_JOB_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                "The page returned too little job text. It may need JavaScript or sign-in to display the posting. "
                "Open it in your browser and paste the job description below."
            ),
        )
    return FetchedJobText(cleaned_text, "page text")


async def fetch_url_text(url: str) -> str:
    return (await fetch_url_page(url)).text

class FetchUrlRequest(BaseModel):
    url: str

@router.post("/fetch-url")
async def fetch_url_endpoint(req: FetchUrlRequest):
    """Fetch webpage content and extract clean text for JD textarea."""
    url = req.url.strip() if req.url else ""
    result = await fetch_url_page(url)
    return {"url": url, "text": result.text, "extraction_method": result.extraction_method}

@router.post("/analyze")
async def analyze_job(req: AnalyzeRequest):
    """Fetch/receive JD and run match analysis with the selected provider."""
    try:
        ai_client = require_ai_client()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # CRITICAL: Always prioritize the text explicitly in the textarea!
    # Only fall back to fetching the URL if the text box was left empty.
    raw_text = req.text
    if (not raw_text or len(raw_text.strip()) < 30) and req.url:
        raw_text = await fetch_url_text(req.url)
    elif not raw_text or len(raw_text.strip()) < 30:
        raise HTTPException(
            status_code=400,
            detail="Please provide job description text (paste into the box or click 'Fetch JD' above)."
        )

    try:
        analysis = await analyze_job_posting(raw_text=raw_text, source_url=req.url, gemini_client=ai_client)
        return analysis
    except (GeminiError, CodexError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/import")
def import_job(req: ImportConfirmedJobRequest):
    """Save the analyzed job into DoorKnock database and create an application in 'saved' stage."""
    job_id = str(uuid.uuid4())
    app_id = str(uuid.uuid4())
    now_str = utc_now().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO jobs (
                id, source, source_job_id, title, company, company_url,
                location, workplace_type, salary_min, salary_max, salary_currency, salary_interval,
                job_url, application_url, job_description, job_brief,
                suitability_score, suitability_reason, analysis_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
        """, (
            job_id,
            req.source,
            None,
            req.title,
            req.company,
            req.company_url,
            req.location,
            req.workplace_type,
            req.salary_min,
            req.salary_max,
            req.salary_currency or "USD",
            req.salary_interval or "year",
            req.job_url,
            req.job_url,
            req.job_description,
            req.job_brief,
            req.suitability_score,
            req.suitability_reason,
            req.analysis_json,
            now_str,
            now_str
        ))

        conn.execute("""
            INSERT INTO applications (
                id, job_id, current_stage, created_at, updated_at
            ) VALUES (?, ?, 'saved', ?, ?)
        """, (app_id, job_id, now_str, now_str))

        conn.commit()

        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return {"ok": True, "job": dict(job), "application_id": app_id}
