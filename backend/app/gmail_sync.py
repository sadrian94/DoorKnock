"""Local, read-only Gmail scan with conservative application matching."""

import json
import os
import re
import secrets
import time
import uuid
from datetime import date, datetime, timezone
from .clock import utc_now, local_date_of
from email.utils import parseaddr
from urllib.parse import quote, urlencode

import httpx
from bs4 import BeautifulSoup

from .config import DATA_DIR
from .crud import KANBAN_STAGES
from .cadence import business_days, event_day, _application_state, _restore_state, visible_event
from .database import get_db

TOKEN_PATH = DATA_DIR / "gmail-token.json"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
_pending_states: dict[str, float] = {}
RECONNECT_MESSAGE = "Gmail authorization has expired or is no longer valid; reconnect Gmail"


def configured() -> bool:
    return bool(os.getenv("GMAIL_CLIENT_ID") and os.getenv("GMAIL_CLIENT_SECRET"))


def connected() -> bool:
    return connection_status()["connected"]


def connection_status() -> dict[str, bool]:
    if not TOKEN_PATH.is_file():
        return {"connected": False, "reconnect_required": False}
    try:
        token = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
        usable = isinstance(token, dict) and not token.get("reconnect_required") and (
            bool(token.get("refresh_token")) or (
                bool(token.get("access_token")) and float(token.get("expires_at", 0)) > time.time() + 60
            )
        )
    except (OSError, ValueError, TypeError):
        usable = False
    return {"connected": bool(usable), "reconnect_required": not usable}


def _redirect_uri() -> str:
    return os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/gmail/callback")


def authorization_url() -> str:
    if not configured():
        raise ValueError("Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in the local environment")
    state = secrets.token_urlsafe(32)
    _pending_states[state] = time.time() + 600
    for key, expiry in list(_pending_states.items()):
        if expiry < time.time():
            del _pending_states[key]
    query = urlencode({
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return f"{AUTH_URL}?{query}"


async def exchange_code(code: str, state: str) -> None:
    expiry = _pending_states.pop(state, 0)
    if expiry < time.time():
        raise ValueError("Gmail sign-in expired; start again")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(TOKEN_URL, data={
            "code": code,
            "client_id": os.environ["GMAIL_CLIENT_ID"],
            "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
        })
        response.raise_for_status()
    _save_token(response.json())


def _save_token(token: dict) -> None:
    if "expires_in" in token:
        token["expires_at"] = time.time() + int(token["expires_in"])
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = TOKEN_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(token), encoding="utf-8")
    temp.replace(TOKEN_PATH)


async def _access_token(client: httpx.AsyncClient, *, force_refresh: bool = False) -> str:
    status = connection_status()
    if not status["connected"]:
        raise ValueError(RECONNECT_MESSAGE if status["reconnect_required"] else "Gmail is not connected")
    token = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    if not force_refresh and token.get("access_token") and float(token.get("expires_at", 0)) > time.time() + 60:
        return token["access_token"]
    if not token.get("refresh_token"):
        _save_token({"reconnect_required": True})
        raise ValueError("Gmail authorization has expired; reconnect Gmail")
    response = await client.post(TOKEN_URL, data={
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    })
    if response.status_code == 400 and response.json().get("error") == "invalid_grant":
        # Persist the reconnect state across page reloads and backend restarts.
        _save_token({"reconnect_required": True})
        raise ValueError(RECONNECT_MESSAGE)
    response.raise_for_status()
    refreshed = response.json()
    refreshed["refresh_token"] = token["refresh_token"]
    _save_token(refreshed)
    return refreshed["access_token"]


async def _gmail_get(client: httpx.AsyncClient, url: str, headers: dict, params: dict) -> httpx.Response:
    response = await client.get(url, headers=headers, params=params)
    if response.status_code == 401:
        headers["Authorization"] = f"Bearer {await _access_token(client, force_refresh=True)}"
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 401:
            _save_token({"reconnect_required": True})
            raise ValueError(RECONNECT_MESSAGE)
    response.raise_for_status()
    return response


def _decode_part(part: dict) -> str:
    import base64

    if part.get("mimeType") in ("text/plain", "text/html") and part.get("body", {}).get("data"):
        data = part["body"]["data"]
        decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
        return BeautifulSoup(decoded, "html.parser").get_text(" ", strip=True) if part["mimeType"] == "text/html" else decoded
    children = part.get("parts", [])
    plain = "\n".join(_decode_part(child) for child in children if child.get("mimeType") != "text/html")
    return plain or "\n".join(_decode_part(child) for child in children)


def _preview_text(part: dict) -> str:
    """Read message text only; never render markup or fetch attachment bodies."""
    import base64
    from email.message import Message

    headers = {item['name'].lower(): item['value'] for item in part.get('headers', [])}
    if part.get('filename') or headers.get('content-disposition', '').split(';', 1)[0].strip().lower() == 'attachment':
        return ''
    mime = part.get('mimeType', '').lower()
    if mime in ('text/plain', 'text/html'):
        data = part.get('body', {}).get('data')
        if not data:
            return ''
        content_type = Message()
        content_type['content-type'] = headers.get('content-type', mime)
        raw = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
        try:
            text = raw.decode(content_type.get_content_charset() or 'utf-8', 'replace')
        except LookupError:
            text = raw.decode('utf-8', 'replace')
        if mime == 'text/html':
            soup = BeautifulSoup(text, 'html.parser')
            for node in soup(['head', 'script', 'style', 'noscript', 'template']):
                node.decompose()
            text = soup.get_text('\n', strip=True)
        return text.strip()
    if mime and not mime.startswith('multipart/'):
        return ''
    children = part.get('parts', [])
    if mime == 'multipart/alternative':
        for child in sorted(children, key=lambda item: item.get('mimeType') != 'text/plain'):
            text = _preview_text(child)
            if text:
                return text
        return ''
    return '\n\n'.join(text for child in children if (text := _preview_text(child)))


async def preview_message(message_id: str) -> dict:
    """Fetch one known review on demand. Content is returned, never persisted."""
    with get_db() as conn:
        known = conn.execute("SELECT 1 FROM gmail_review_items WHERE message_id=? AND status IN ('pending','linked','applied','dismissed')", (message_id,)).fetchone()
    if not known:
        raise LookupError('Review item not found')
    async with httpx.AsyncClient(timeout=20) as client:
        headers = {'Authorization': f'Bearer {await _access_token(client)}'}
        response = await _gmail_get(client, f'{GMAIL_URL}/{quote(message_id, safe="")}', headers, {'format': 'full'})
        message = response.json()
    if message.get('id') != message_id:
        raise ValueError('Could not load email preview. Try again or open the original in Gmail.')
    payload = message.get('payload', {})
    headers = {item['name'].lower(): item['value'] for item in payload.get('headers', [])}
    body = _preview_text(payload)
    return {'message_id': message_id, 'subject': headers.get('subject', ''),
            'body': body[:20000], 'truncated': len(body) > 20000}


def _current_content(body: str) -> str:
    return re.split(r"(?im)^\s*(?:on .+ wrote:|[-]+\s*original message\s*[-]+|begin forwarded message:)", body, maxsplit=1)[0]


def _is_job_board_alert(headers: dict[str, str], subject: str, body: str) -> bool:
    """Identify recommendation digests, without excluding transactional board mail."""
    sender_name, sender_address = parseaddr(headers.get("from", ""))
    domain = sender_address.rsplit("@", 1)[-1].casefold() if "@" in sender_address else ""
    board_domains = ("linkedin.com", "joinhandshake.com", "handshake.com",
                     "hiring.cafe", "hiringcafe.com")
    board_sender = any(domain == known or domain.endswith("." + known) for known in board_domains)
    board_sender = board_sender or bool(re.search(r"\b(linkedin|handshake|hiring\s*cafe)\b", sender_name, re.I))
    bulk = ("list-unsubscribe" in headers or "list-id" in headers
            or headers.get("precedence", "").casefold() in ("bulk", "list"))
    alert_subject = bool(re.search(
        r"\b(job alerts?|job recommendations?|recommended jobs?|new jobs?|jobs for you|jobs matching|daily job|weekly job|saved search)\b",
        subject, re.I,
    ))
    alert_body = bool(re.search(
        r"\b(jobs? (?:that )?match (?:your|you)|recommended jobs? for you|jobs? for you|new jobs? based on your|your (?:daily|weekly) job (?:alert|digest))\b",
        body[:3000], re.I,
    ))
    return (board_sender and (alert_subject or (bulk and alert_body))) or (bulk and alert_subject)


def _event(subject: str, body: str) -> tuple[str, str] | None:
    text = f"{subject}\n{body[:10000]}".lower()
    if re.search(r"\b(regret to inform you|not moving forward with (your|the) application|your application (was|has been) not selected|decided to (move|proceed) forward with other candidates|position has been filled)\b", text):
        if re.search(r"\b(application|candidate|position|role|job)\b", text):
            return "rejected", "closed"
    if re.search(r"\b(interview (is |has been )?(scheduled|confirmed)|confirmed (your |the )?interview)\b", text):
        if re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}[:/]\d{2}|\d{4}-\d{2}-\d{2})\b", text):
            if re.search(r"\b(recruiter|phone screen|screening call|initial screen)\b", text):
                return "recruiter_screen_scheduled", "recruiter_screen"
    if re.search(r"\b(thank you for applying|application (has been )?received|received your application|application submitted)\b", text):
        return "application_received", "applied"
    return None


def _application_matches(conn, subject: str, body: str, *, allow_company_only: bool = False) -> list[tuple[str, str]]:
    text = f"{subject}\n{body[:10000]}".casefold()
    rows = conn.execute("""
        SELECT a.id, a.current_stage, j.company, j.title, j.source_job_id
        FROM applications a JOIN jobs j ON j.id = a.job_id
        WHERE a.current_stage != 'closed'
    """).fetchall()
    matches = []
    for row in rows:
        company = row["company"].strip().casefold()
        title = row["title"].strip().casefold()
        requisition = (row["source_job_id"] or "").strip().casefold()
        if not company or not re.search(r"(?<!\w)" + re.escape(company) + r"(?!\w)", text):
            continue
        if requisition and len(requisition) >= 5 and re.search(r"(?<!\w)" + re.escape(requisition) + r"(?!\w)", text):
            matches.append((row["id"], "company_and_requisition"))
        elif len(title) >= 8 and re.search(r"(?<!\w)" + re.escape(title) + r"(?!\w)", text):
            matches.append((row["id"], "company_and_title"))
        elif allow_company_only and len(company) >= 3:
            matches.append((row["id"], "company_only"))
    return matches


def _match_application(conn, subject: str, body: str) -> tuple[str, str] | None:
    matches = _application_matches(conn, subject, body)
    return matches[0] if len(matches) == 1 else None


def _queue_review(conn, message: dict, received_at: str, event_code: str,
                  to_stage: str | None, reason_code: str, candidates: list[str]) -> None:
    conn.execute("""
        INSERT INTO gmail_review_items
        (message_id, thread_id, received_at, event_code, proposed_stage, reason_code, candidate_application_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (message["id"], message["threadId"], received_at, event_code,
          to_stage, reason_code, json.dumps(candidates)))


def _change_stage(conn, application_id: str, current: str, to_stage: str,
                  event_code: str, received_at: str, message_id: str, reviewed: bool = False,
                  *, due_date: str | None = None, confirmed_outcome: str | None = None) -> str:
    before = _application_state(conn, application_id)
    now = utc_now().isoformat()
    outcome = (confirmed_outcome or ('rejected' if event_code == 'rejected' else None)) if to_stage == 'closed' else None
    previous = conn.execute('SELECT applied_date,next_followup_date FROM applications WHERE id=?', (application_id,)).fetchone()
    followup = previous['next_followup_date']
    if to_stage == 'applied' and current != 'applied':
        followup = business_days(event_day(previous['applied_date']) or date.fromisoformat(local_date_of(received_at)), 10).isoformat()
    elif to_stage == 'knocked' and current != 'knocked':
        followup = None
    conn.execute("""
        UPDATE applications SET current_stage = ?, outcome = ?,
            applied_date = CASE WHEN ? = 'applied' THEN COALESCE(applied_date, ?) ELSE applied_date END,
            next_followup_date = CASE WHEN ? IN ('closed', 'offer') THEN NULL WHEN ? IN ('applied', 'knocked') THEN ? ELSE next_followup_date END,
            updated_at = ? WHERE id = ?
    """, (to_stage, outcome, to_stage, local_date_of(received_at), to_stage, to_stage, followup, now, application_id))
    job_status = "archived" if to_stage == "closed" else "saved" if to_stage == "saved" else "applied" if to_stage == "applied" else "in_progress"
    conn.execute("UPDATE jobs SET status = ?, updated_at = ? WHERE id = (SELECT job_id FROM applications WHERE id = ?)", (job_status, now, application_id))
    event_id = str(uuid.uuid4())
    event_type = 'interview_scheduled' if due_date and to_stage in ('recruiter_screen', 'team_match', 'technical_interview', 'final_round') else 'assessment_assigned' if due_date and to_stage == 'assessment' else 'stage_change'
    metadata = {"source": "gmail", "message_id": message_id, "event_code": event_code, "reviewed": reviewed,
                "_stage_before": before, "_stage_after": _application_state(conn, application_id)}
    if due_date:
        metadata.update(cadence=True, due_date=due_date)
        if event_type == 'interview_scheduled':
            metadata['interview_stage'] = to_stage
    conn.execute("""
        INSERT INTO timeline_events (id, application_id, event_type, from_stage, to_stage, title, occurred_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (event_id, application_id, event_type, current, to_stage,
          "Stage confirmed from Gmail review" if reviewed else "Stage updated from Gmail evidence",
          received_at, json.dumps(metadata)))
    return event_id


def _record_message(message: dict) -> dict:
    headers = {item["name"].lower(): item["value"] for item in message.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    body = _current_content(_decode_part(message.get("payload", {})))
    event = _event(subject, body)
    received_at = datetime.fromtimestamp(int(message["internalDate"]) / 1000, timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if _is_job_board_alert(headers, subject, body):
            saved = conn.execute("SELECT stage_applied FROM gmail_application_messages WHERE message_id = ?",
                                 (message["id"],)).fetchone()
            if saved and saved["stage_applied"]:
                # Preserve an already recorded transition for human inspection.
                return {"saved": False, "stage_changed": False, "needs_review": False}
            review = conn.execute("SELECT status FROM gmail_review_items WHERE message_id = ?",
                                  (message["id"],)).fetchone()
            if review:
                conn.execute("""
                    UPDATE gmail_review_items SET status = 'filtered', reason_code = 'job_board_alert',
                        resolved_at = ? WHERE message_id = ? AND status = 'pending'
                """, (utc_now().isoformat(), message["id"]))
            else:
                _queue_review(conn, message, received_at, "related", None, "job_board_alert", [])
                conn.execute("UPDATE gmail_review_items SET status = 'filtered' WHERE message_id = ?",
                             (message["id"],))
            conn.execute("""
                UPDATE gmail_application_messages SET match_reason = 'job_board_alert'
                WHERE message_id = ? AND stage_applied = 0
            """, (message["id"],))
            conn.commit()
            return {"saved": False, "stage_changed": False, "needs_review": False,
                    "ignored_job_board": True}
        if (conn.execute("SELECT 1 FROM gmail_application_messages WHERE message_id = ?", (message["id"],)).fetchone()
                or conn.execute("SELECT 1 FROM gmail_review_items WHERE message_id = ?", (message["id"],)).fetchone()):
            return {"saved": False, "stage_changed": False, "needs_review": False}
        matches = _application_matches(conn, subject, body)
        event_code, to_stage = event if event else ("related", None)
        if not matches:
            # Hiring updates often omit the exact saved title. Keep these as
            # suggestions requiring review, never as confirmed application links.
            hiring_context = event or re.search(
                r"\b(application|interview|onboarding|assessment|recruiter|recruitment|hiring|offer letter|employment offer)\b",
                f"{subject}\n{body[:10000]}", re.I,
            )
            candidates = _application_matches(conn, subject, body, allow_company_only=True) if hiring_context else []
            review_reason = "company_only"
            if not candidates:
                candidates = [(row["application_id"], "thread_context") for row in conn.execute("""
                    SELECT DISTINCT m.application_id FROM gmail_application_messages m
                    JOIN applications a ON a.id = m.application_id
                    WHERE m.thread_id = ? AND a.current_stage != 'closed'
                        AND (m.match_reason = 'user_confirmed' OR m.stage_applied = 1)
                """, (message["threadId"],))]
                review_reason = "thread_context"
            if candidates:
                _queue_review(conn, message, received_at, event_code, to_stage,
                              review_reason, [candidate_id for candidate_id, _ in candidates])
                conn.commit()
                return {"saved": False, "stage_changed": False, "needs_review": True}
        if len(matches) != 1:
            if not matches and not event:
                return {"saved": False, "stage_changed": False, "needs_review": False}
            _queue_review(conn, message, received_at, event_code, to_stage,
                          "multiple_applications" if matches else "no_application_match",
                          [candidate_id for candidate_id, _ in matches])
            conn.commit()
            return {"saved": False, "stage_changed": False, "needs_review": True}
        application_id, reason = matches[0]
        app = conn.execute("SELECT current_stage, applied_date FROM applications WHERE id = ?", (application_id,)).fetchone()
        current = app["current_stage"]
        stage_compatible = (
            (event_code == "rejected" and current not in ("saved", "offer", "closed"))
            or (event_code == "application_received" and current == "saved")
            or (event_code == "recruiter_screen_scheduled" and current in ("applied", "knocked"))
        )
        bulk_or_automated = "list-unsubscribe" in headers or headers.get("auto-submitted", "").lower() not in ("", "no")
        older_than_application = bool(app["applied_date"] and local_date_of(received_at) < app["applied_date"])
        conn.execute("""
            INSERT INTO gmail_application_messages
            (message_id, thread_id, application_id, received_at, event_code, match_reason, stage_applied)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (message["id"], message["threadId"], application_id, received_at, event_code, reason, 0))
        review_reason = (
            "unclear_event" if not event else
            "bulk_or_automated" if bulk_or_automated else
            "older_message" if older_than_application else
            "stage_conflict" if not stage_compatible else
            "human_confirmation_required"
        )
        _queue_review(conn, message, received_at, event_code, to_stage,
                      review_reason, [application_id])
        conn.commit()
        return {"saved": True, "stage_changed": False, "needs_review": True}


async def scan_recent(days: int = 14, limit: int = 150, page_token: str | None = None,
                      window_start: int | None = None) -> dict:
    if not 1 <= days <= 30 or not 100 <= limit <= 200:
        raise ValueError("Choose 1–30 recent days and a 100–200 message limit")
    if page_token and window_start is None:
        raise ValueError("Scan window is missing; start a new scan")
    now = utc_now().timestamp()
    after = int(now - days * 86400) if window_start is None else window_start
    # The UI keeps days fixed during pagination, so the original scan time can
    # be recovered from its search boundary without moving that boundary.
    scan_started = after + days * 86400
    max_age = 86400 if page_token else 60
    if after > now or scan_started > now + 1 or scan_started < now - max_age:
        raise ValueError("Scan window has expired; start a new scan")
    async with httpx.AsyncClient(timeout=25) as client:
        token = await _access_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "q": f"after:{after} -in:sent -in:drafts -category:promotions -in:spam -in:trash",
            "maxResults": limit,
        }
        if page_token:
            params["pageToken"] = page_token
        response = await _gmail_get(client, GMAIL_URL, headers, params)
        listing = response.json()
        result = {"scanned": 0, "saved": 0, "stage_changed": 0, "needs_review": 0,
                  "ignored_job_board": 0, "skipped": 0,
                  "more_available": bool(listing.get("nextPageToken")),
                  "next_page_token": listing.get("nextPageToken"), "window_start": after}
        messages = listing.get("messages", [])
        known = set()
        if messages:
            ids = [item["id"] for item in messages]
            placeholders = ",".join("?" for _ in ids)
            with get_db() as conn:
                known = {row["message_id"] for row in conn.execute(f"""
                    SELECT message_id FROM gmail_application_messages WHERE message_id IN ({placeholders})
                    UNION
                    SELECT message_id FROM gmail_review_items WHERE message_id IN ({placeholders})
                """, ids + ids)}
        for item in messages:
            if item["id"] in known:
                result["skipped"] += 1
                continue
            detail = await _gmail_get(client, f"{GMAIL_URL}/{item['id']}", headers, {"format": "full"})
            outcome = _record_message(detail.json())
            known.add(item["id"])
            result["scanned"] += 1
            result["saved"] += int(outcome["saved"])
            result["stage_changed"] += int(outcome["stage_changed"])
            result["needs_review"] += int(outcome["needs_review"])
            result["ignored_job_board"] += int(outcome.get("ignored_job_board", False))
        return result


def saved_messages(limit: int = 30, application_id: str | None = None) -> list[dict]:
    with get_db() as conn:
        return [dict(row) for row in conn.execute("""
            SELECT m.message_id, m.application_id, m.received_at, m.event_code,
                m.match_reason, m.stage_applied, j.company, j.title
            FROM gmail_application_messages m
            JOIN applications a ON a.id = m.application_id
            JOIN jobs j ON j.id = a.job_id
            WHERE m.match_reason != 'job_board_alert'
                AND (? IS NULL OR m.application_id = ?)
            ORDER BY m.received_at DESC LIMIT ?
        """, (application_id, application_id, limit)).fetchall()]


def pending_reviews(limit: int = 50, *, status: str = 'pending', offset: int = 0) -> dict:
    if status not in ('pending', 'processed'):
        raise ValueError('Choose pending or processed reviews')
    with get_db() as conn:
        where = "r.status = 'pending'" if status == 'pending' else "r.status IN ('linked','applied','dismissed')"
        order = 'r.received_at' if status == 'pending' else 'r.resolved_at'
        rows = conn.execute(f"""
            SELECT r.message_id, r.received_at, r.event_code, r.proposed_stage, r.reason_code,
                   r.candidate_application_ids, r.status, r.resolved_at,
                   (r.resolution_metadata IS NOT NULL) AS can_undo, m.application_id
            FROM gmail_review_items r LEFT JOIN gmail_application_messages m ON m.message_id = r.message_id
            WHERE {where} ORDER BY {order} DESC, r.message_id DESC LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        pending_count = conn.execute("SELECT COUNT(*) FROM gmail_review_items WHERE status='pending'").fetchone()[0]
        processed_count = conn.execute("SELECT COUNT(*) FROM gmail_review_items WHERE status IN ('linked','applied','dismissed')").fetchone()[0]
        applications = [dict(row) for row in conn.execute("""
            SELECT a.id, a.current_stage, j.company, j.title
            FROM applications a JOIN jobs j ON j.id = a.job_id
            ORDER BY j.company, j.title
        """).fetchall()]
        reviews = []
        for row in rows:
            review = dict(row)
            review["candidate_application_ids"] = json.loads(review["candidate_application_ids"])
            review['can_undo'] = bool(review['can_undo'])
            reviews.append(review)
        total = pending_count if status == 'pending' else processed_count
        return {"reviews": reviews, "applications": applications, "pending_count": pending_count,
                "processed_count": processed_count, "has_more": offset + len(rows) < total,
                "next_offset": offset + len(rows)}


def resolve_review(message_id: str, action: str, application_id: str | None = None,
                   to_stage: str | None = None, *, due_date: str | None = None,
                   outcome: str | None = None) -> dict:
    if action not in ("apply", "progress", "link", "dismiss"):
        raise ValueError("Choose link, progress or dismiss")
    if action in ('apply', 'progress') and (not application_id or to_stage not in KANBAN_STAGES):
        raise ValueError("Choose an application and a valid stage")
    if action == 'link' and not application_id:
        raise ValueError('Choose an application')
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        review = conn.execute("SELECT * FROM gmail_review_items WHERE message_id = ?", (message_id,)).fetchone()
        if not review or review["status"] != "pending":
            raise ValueError("Review item is no longer pending")
        prior_message = conn.execute('SELECT application_id,match_reason,stage_applied FROM gmail_application_messages WHERE message_id=?', (message_id,)).fetchone()
        before = _application_state(conn, application_id) if application_id else None
        event_id = None
        changed = False
        if action in ('apply', 'progress', 'link'):
            app = conn.execute("SELECT current_stage, outcome FROM applications WHERE id = ?", (application_id,)).fetchone()
            if not app:
                raise ValueError("Application not found")
            receipt_only = action != 'link' and review["event_code"] == "application_received" and to_stage == "applied" and app["current_stage"] != "saved"
            if action == 'progress':
                if outcome and to_stage != 'closed':
                    raise ValueError('A closing outcome is only valid for a closed application')
                dated = to_stage in ('assessment', 'recruiter_screen', 'team_match', 'technical_interview', 'final_round')
                if dated and (not due_date or not event_day(due_date)):
                    raise ValueError('A confirmed date is required for this stage')
                if due_date and (len(due_date) != 10 or not event_day(due_date) or due_date < local_date_of(review['received_at'])):
                    raise ValueError('The confirmed date cannot precede the email')
                if to_stage == 'closed' and outcome not in ('rejected', 'withdrawn', 'offer_accepted', 'offer_declined'):
                    raise ValueError('Choose the confirmed closing outcome')
                later = conn.execute("SELECT * FROM timeline_events WHERE application_id=? AND to_stage IS NOT NULL AND julianday(occurred_at)>julianday(?)", (application_id, review['received_at'])).fetchall()
                changes_progress = app['current_stage'] != to_stage or bool(due_date) or (to_stage == 'closed' and outcome != app['outcome'])
                if not receipt_only and changes_progress and any(visible_event(row) for row in later):
                    raise ValueError('Later progress is already recorded. Save the email link without changing its stage.')
            changed = action != 'link' and (app["current_stage"] != to_stage or (
                to_stage == "closed" and review["event_code"] == "rejected" and app["outcome"] != "rejected"
            ) or (to_stage == 'closed' and outcome is not None and outcome != app['outcome']))
            # A receipt confirms submission, not a correction of later progress.
            # Keep Contacted/interview/terminal state even when the review UI
            # submits the receipt's proposed Applied stage.
            if receipt_only:
                changed = False
                event_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO timeline_events
                    (id, application_id, event_type, title, occurred_at, metadata)
                    VALUES (?, ?, 'acknowledgement', ?, ?, ?)
                """, (event_id, application_id, "Application receipt confirmed from Gmail review",
                      review["received_at"], json.dumps({"source": "gmail", "message_id": message_id,
                                                        "event_code": review["event_code"], "reviewed": True})))
            if changed or (action == 'progress' and due_date and not receipt_only):
                event_id = _change_stage(conn, application_id, app["current_stage"], to_stage,
                                        review["event_code"], review["received_at"], message_id, reviewed=True,
                                        due_date=due_date, confirmed_outcome=outcome)
            existing = conn.execute("SELECT 1 FROM gmail_application_messages WHERE message_id = ?", (message_id,)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE gmail_application_messages
                    SET application_id = ?, match_reason = 'user_confirmed', stage_applied = ?
                    WHERE message_id = ?
                """, (application_id, int(changed), message_id))
            else:
                conn.execute("""
                    INSERT INTO gmail_application_messages
                    (message_id, thread_id, application_id, received_at, event_code, match_reason, stage_applied)
                    VALUES (?, ?, ?, ?, ?, 'user_confirmed', ?)
                """, (message_id, review["thread_id"], application_id,
                      review["received_at"], review["event_code"], int(changed)))
        resolution = {'application_id': application_id, 'before_message': dict(prior_message) if prior_message else None,
                      'event_id': event_id, 'stage_changed': changed, 'before': before,
                      'after': _application_state(conn, application_id) if application_id else None}
        resolved_status = 'linked' if action == 'link' else 'applied' if action in ('apply', 'progress') else 'dismissed'
        conn.execute("UPDATE gmail_review_items SET status = ?, resolved_at = ?, resolution_metadata = ? WHERE message_id = ?",
                     (resolved_status, utc_now().isoformat(), json.dumps(resolution), message_id))
        conn.commit()
        return {"stage_changed": changed, "status": action}


def undo_review(message_id: str) -> dict:
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        review = conn.execute('SELECT * FROM gmail_review_items WHERE message_id=?', (message_id,)).fetchone()
        if not review:
            raise ValueError('Review item not found')
        if review['status'] == 'pending':
            return {'status': 'pending', 'stage_changed': False}
        if not review['resolution_metadata']:
            raise ValueError('This older review cannot be undone automatically')
        resolution = json.loads(review['resolution_metadata'])
        application_id = resolution['application_id']
        event_id = resolution['event_id']
        if resolution['before'] != resolution['after']:
            event = conn.execute('SELECT rowid FROM timeline_events WHERE id=?', (event_id,)).fetchone()
            later = conn.execute('SELECT * FROM timeline_events WHERE application_id=? AND to_stage IS NOT NULL AND rowid>?', (application_id, event['rowid'])).fetchall() if event else []
            if _application_state(conn, application_id) != resolution['after'] or any(visible_event(row) for row in later):
                raise ValueError('Later progress is already recorded. Undo cannot overwrite it.')
            _restore_state(conn, application_id, resolution['before'])
        if event_id:
            event = conn.execute('SELECT metadata FROM timeline_events WHERE id=?', (event_id,)).fetchone()
            if event:
                metadata = json.loads(event['metadata'] or '{}')
                metadata['_deleted_at'] = utc_now().isoformat()
                conn.execute('UPDATE timeline_events SET metadata=? WHERE id=?', (json.dumps(metadata), event_id))
        original = resolution['before_message']
        if original:
            conn.execute('UPDATE gmail_application_messages SET application_id=?,match_reason=?,stage_applied=? WHERE message_id=?',
                         (original['application_id'], original['match_reason'], original['stage_applied'], message_id))
        else:
            conn.execute('DELETE FROM gmail_application_messages WHERE message_id=?', (message_id,))
        conn.execute("UPDATE gmail_review_items SET status='pending',resolved_at=NULL,resolution_metadata=NULL WHERE message_id=?", (message_id,))
        conn.commit()
        return {'status': 'pending', 'stage_changed': resolution['stage_changed']}
