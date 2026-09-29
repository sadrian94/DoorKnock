import asyncio
import gzip
import importlib
import json
from pathlib import Path

import httpx
import httpcore
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.testclient import TestClient

import_job = importlib.import_module("app.api.import_job")
from app.main import app
from scripts.generate_comparison import generate_compact_english_html


def test_spa_serves_only_files_inside_frontend_build(tmp_path, monkeypatch):
    main_module = importlib.import_module("app.main")
    assert callable(main_module.serve_spa)
    dist = tmp_path / "dist"
    dist.mkdir()
    index = dist / "index.html"
    index.write_text("SPA INDEX", encoding="utf-8")
    public_file = dist / "robots.txt"
    public_file.write_text("PUBLIC FILE", encoding="utf-8")
    private_file = tmp_path / "secret.txt"
    private_file.write_text("PRIVATE SENTINEL", encoding="utf-8")
    monkeypatch.setattr(main_module, "FRONTEND_DIST", dist)

    valid = asyncio.run(main_module.serve_spa("robots.txt"))
    assert isinstance(valid, FileResponse)
    assert Path(valid.path).resolve() == public_file.resolve()

    escaped = asyncio.run(main_module.serve_spa("../secret.txt"))
    assert isinstance(escaped, FileResponse)
    assert Path(escaped.path).resolve() == index.resolve()

    spa_app = FastAPI()
    spa_app.add_api_route("/{full_path:path}", main_module.serve_spa, methods=["GET"])
    with TestClient(spa_app) as client:
        response = client.get("/%2e%2e%2fsecret.txt")
    assert response.status_code == 200
    assert response.text == "SPA INDEX"
    assert "PRIVATE SENTINEL" not in response.text


def test_spa_fallback_rejects_index_resolved_outside_build(tmp_path, monkeypatch):
    main_module = importlib.import_module("app.main")
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("BUILD INDEX", encoding="utf-8")
    outside_index = tmp_path / "outside-index.html"
    outside_index.write_text("OUTSIDE SENTINEL", encoding="utf-8")
    monkeypatch.setattr(main_module, "FRONTEND_DIST", dist)

    original_resolve = Path.resolve

    def resolve_external_index(path, strict=False):
        if path == dist / "index.html":
            return original_resolve(outside_index, strict=True)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve_external_index)
    assert main_module._frontend_file("index.html") is None

    response = asyncio.run(main_module.serve_spa("missing-route"))
    assert response.status_code == 404


def test_url_fetch_rejects_private_literal_before_opening_http_client(monkeypatch):
    def forbidden_client(*args, **kwargs):
        pytest.fail("A private destination must be rejected before a request is opened")

    monkeypatch.setattr(import_job.httpx, "AsyncClient", forbidden_client)
    with pytest.raises(HTTPException, match="public"):
        asyncio.run(import_job.fetch_url_page("http://127.0.0.1/admin"))


def test_url_fetch_rejects_mixed_public_and_private_dns_answers(monkeypatch):
    async def mixed_addresses(host, port):
        return ["93.184.216.34", "10.0.0.8"]

    monkeypatch.setattr(import_job, "_resolve_dns_addresses", mixed_addresses)
    with pytest.raises(HTTPException, match="public"):
        asyncio.run(import_job._resolve_public_addresses("jobs.example", 443))


def test_public_url_redirect_to_private_address_is_rejected(monkeypatch):
    real_client = httpx.AsyncClient
    requests = []

    async def resolve_public_only(host, port):
        if host == "127.0.0.1":
            raise HTTPException(status_code=400, detail="URL must resolve only to public addresses")
        return ["93.184.216.34"]

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})

    def mock_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs["trust_env"] = False
        return real_client(*args, **kwargs)

    monkeypatch.setattr(import_job, "_resolve_public_addresses", resolve_public_only, raising=False)
    monkeypatch.setattr(import_job.httpx, "AsyncClient", mock_client)

    with pytest.raises(HTTPException, match="public"):
        asyncio.run(import_job.fetch_url_page("https://jobs.example/careers/role"))
    assert requests == ["https://jobs.example/careers/role"]


def test_fetch_and_analyze_routes_share_private_url_validation(monkeypatch):
    def forbidden_client(*args, **kwargs):
        pytest.fail("A private destination must be rejected before a request is opened")

    monkeypatch.setattr(import_job, "require_ai_client", lambda: object())
    monkeypatch.setattr(import_job.httpx, "AsyncClient", forbidden_client)
    with TestClient(app) as client:
        fetched = client.post("/api/jobs/fetch-url", json={"url": "http://127.0.0.1/admin"})
        analyzed = client.post("/api/jobs/analyze", json={"url": "http://127.0.0.1/admin", "text": ""})
    assert fetched.status_code == 400
    assert "public" in fetched.json()["detail"]
    assert analyzed.status_code == 400
    assert "public" in analyzed.json()["detail"]


def test_pinned_network_backend_connects_to_the_validated_ip():
    backend = import_job._PinnedNetworkBackend(
        expected_host="jobs.example",
        expected_port=443,
        addresses=["93.184.216.34"],
    )

    class RecordingBackend:
        def __init__(self):
            self.hosts = []

        async def connect_tcp(self, **kwargs):
            self.hosts.append(kwargs["host"])
            return object()

    recorder = RecordingBackend()
    backend._backend = recorder
    asyncio.run(backend.connect_tcp(
        host="jobs.example", port=443, timeout=1.0,
        local_address=None, socket_options=None,
    ))
    assert recorder.hosts == ["93.184.216.34"]


def test_pinned_http_transport_preserves_hostname_request_and_response():
    transport = import_job._PinnedHTTPTransport("jobs.example", 443, ["93.184.216.34"])
    observed = {}

    class ResponseStream:
        async def __aiter__(self):
            yield b"safe response"

        async def aclose(self):
            return None

    class Pool:
        async def handle_async_request(self, request):
            observed["host"] = request.url.host.decode("ascii")
            observed["port"] = request.url.origin.port
            observed["target"] = request.url.target
            return httpcore.Response(status=200, headers=[], content=ResponseStream(), extensions={})

        async def aclose(self):
            return None

    transport._pool = Pool()
    request = httpx.Request("GET", "https://jobs.example/careers/role")

    async def send_request():
        response = await transport.handle_async_request(request)
        body = await response.aread()
        await response.aclose()
        await transport.aclose()
        return response.status_code, body

    assert asyncio.run(send_request()) == (200, b"safe response")
    assert observed == {"host": "jobs.example", "port": 443, "target": b"/careers/role"}


def test_small_public_html_page_still_extracts_job_text(monkeypatch):
    real_client = httpx.AsyncClient
    body = b"<main>Operations Analyst role with detailed reporting, SQL validation, stakeholder support, and weekly performance summaries.</main>"

    async def resolve_public_only(host, port):
        return ["93.184.216.34"]

    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, stream=httpx.ByteStream(body))

    def mock_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs["trust_env"] = False
        return real_client(*args, **kwargs)

    monkeypatch.setattr(import_job, "_resolve_public_addresses", resolve_public_only)
    monkeypatch.setattr(import_job.httpx, "AsyncClient", mock_client)
    result = asyncio.run(import_job.fetch_url_page("https://jobs.example/careers/role"))
    assert result.extraction_method == "main page content"
    assert "Operations Analyst" in result.text


def test_small_ashby_api_response_still_extracts_posting(monkeypatch):
    real_client = httpx.AsyncClient
    description = "Operations Analyst role with detailed reporting, SQL validation, stakeholder support, and weekly performance summaries."
    body = json.dumps({
        "jobs": [{
            "jobUrl": "https://jobs.ashbyhq.com/sample-board/sample-role",
            "descriptionPlain": description,
        }],
    }).encode("utf-8")

    async def resolve_public_only(host, port):
        return ["93.184.216.34"]

    def handler(request):
        return httpx.Response(200, headers={"content-type": "application/json"}, stream=httpx.ByteStream(body))

    def mock_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs["trust_env"] = False
        return real_client(*args, **kwargs)

    monkeypatch.setattr(import_job, "_resolve_public_addresses", resolve_public_only)
    monkeypatch.setattr(import_job.httpx, "AsyncClient", mock_client)
    result = asyncio.run(import_job.fetch_url_page("https://jobs.ashbyhq.com/sample-board/sample-role"))
    assert result.extraction_method == "Ashby job posting"
    assert result.text == description


def test_url_fetch_rejects_oversized_decompressed_response(monkeypatch):
    real_client = httpx.AsyncClient
    body = gzip.compress(b"<main>" + (b"x" * 300) + b"</main>")

    async def resolve_public_only(host, port):
        return ["93.184.216.34"]

    def handler(request):
        return httpx.Response(
            200,
            headers={"Content-Encoding": "gzip"},
            stream=httpx.ByteStream(body),
        )

    def mock_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs["trust_env"] = False
        return real_client(*args, **kwargs)

    monkeypatch.setattr(import_job, "MAX_FETCH_BYTES", 128, raising=False)
    monkeypatch.setattr(import_job, "_resolve_public_addresses", resolve_public_only, raising=False)
    monkeypatch.setattr(import_job.httpx, "AsyncClient", mock_client)

    with pytest.raises(HTTPException, match="size limit"):
        asyncio.run(import_job.fetch_url_page("https://jobs.example/careers/role"))


def test_oversized_ashby_api_response_is_rejected(monkeypatch):
    real_client = httpx.AsyncClient
    body = b"{" + (b" " * 300) + b"}"

    async def resolve_public_only(host, port):
        return ["93.184.216.34"]

    def handler(request):
        return httpx.Response(200, stream=httpx.ByteStream(body))

    def mock_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs["trust_env"] = False
        return real_client(*args, **kwargs)

    monkeypatch.setattr(import_job, "MAX_FETCH_BYTES", 128, raising=False)
    monkeypatch.setattr(import_job, "_resolve_public_addresses", resolve_public_only, raising=False)
    monkeypatch.setattr(import_job.httpx, "AsyncClient", mock_client)

    with pytest.raises(HTTPException, match="size limit"):
        asyncio.run(import_job.fetch_url_page("https://jobs.ashbyhq.com/sample-board/sample-role"))


def test_comparison_report_escapes_job_and_analysis_html(tmp_path):
    hostile = '<img src=x onerror="alert(1)">'
    report_path = tmp_path / "comparison.html"

    generate_compact_english_html(
        hostile,
        hostile,
        {
            "suitability_reason": hostile,
            "key_strengths": [hostile],
            "gaps_or_risks": [hostile],
        },
        {
            "triage": {
                "decision": hostile,
                "dealbreakers_detected": [hostile],
                "strategic_thesis": hostile,
            },
            "employer_mandate": {
                "acute_operational_frictions": [hostile],
                "immediate_value_hook": hostile,
            },
            "gaps_and_mitigation": [{"gap": hostile, "compensating_evidence": hostile}],
            "tactical_directives": {"tailor": {
                "hero_role_anchor": hostile,
                "supporting_roles": [hostile],
                "recommended_skill_taxonomy": [{"category_name": hostile}],
                "featured_projects": [{
                    "project_name": hostile,
                    "focal_bullet_label": hostile,
                }],
            }},
        },
        output_path=report_path,
    )

    rendered = report_path.read_text(encoding="utf-8")
    assert hostile not in rendered
    assert "&lt;img" in rendered
    assert "onerror=&quot;alert(1)&quot;" in rendered
