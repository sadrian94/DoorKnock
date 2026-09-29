"""Local, read-only Gmail scan with conservative application matching."""

import json
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from .config import DATA_DIR
from .crud import KANBAN_STAGES
from .database import get_db

TOKEN_PATH = DATA_DIR / "gmail-token.json"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
_pending_states: dict[str, float] = {}


def configured() -> bool:
    return bool(os.getenv("GMAIL_CLIENT_ID") and os.getenv("GMAIL_CLIENT_SECRET"))


def connected() -> bool:
    return TOKEN_PATH.is_file()


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


async def _access_token(client: httpx.AsyncClient) -> str:
    if not connected():
        raise ValueError("Gmail is not connected")
    token = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    if token.get("expires_at", 0) > time.time() + 60:
        return token["access_token"]
    if not token.get("refresh_token"):
        raise ValueError("Gmail authorization has expired; reconnect Gmail")
    response = await client.post(TOKEN_URL, data={
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    })
    response.raise_for_status()
    refreshed = response.json()
    refreshed["refresh_token"] = token["refresh_token"]
    _save_token(refreshed)
    return refreshed["access_token"]


def _decode_part(part: dict) -> str:
    import base64

    if part.get("mimeType") in ("text/plain", "text/html") and part.get("body", {}).get("data"):
        data = part["body"]["data"]
        decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
        return BeautifulSoup(decoded, "html.parser").get_text(" ", strip=True) if part["mimeType"] == "text/html" else decoded
    children = part.get("parts", [])
    plain = "\n".join(_decode_part(child) for child in children if child.get("mimeType") != "text/html")
    return plain or "\n".join(_decode_part(child) for child in children)


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


def _application_matches(conn, subject: str, body: str) -> list[tuple[str, str]]:
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
                  event_code: str, received_at: str, message_id: str, reviewed: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    outcome = "rejected" if to_stage == "closed" and event_code == "rejected" else None
    followup = (datetime.now(timezone.utc).date() + timedelta(days=3)).isoformat() if to_stage in ("applied", "knocked") else None
    conn.execute("""
        UPDATE applications SET current_stage = ?, outcome = ?,
            applied_date = CASE WHEN ? = 'applied' THEN COALESCE(applied_date, substr(?, 1, 10)) ELSE applied_date END,
            next_followup_date = CASE WHEN ? IN ('closed', 'offer') THEN NULL WHEN ? IN ('applied', 'knocked') THEN ? ELSE next_followup_date END,
            updated_at = ? WHERE id = ?
    """, (to_stage, outcome, to_stage, received_at, to_stage, to_stage, followup, now, application_id))
    job_status = "archived" if to_stage == "closed" else "saved" if to_stage == "saved" else "applied" if to_stage == "applied" else "in_progress"
    conn.execute("UPDATE jobs SET status = ?, updated_at = ? WHERE id = (SELECT job_id FROM applications WHERE id = ?)", (job_status, now, application_id))
    conn.execute("""
        INSERT INTO timeline_events (id, application_id, event_type, from_stage, to_stage, title, occurred_at, metadata)
        VALUES (?, ?, 'stage_change', ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), application_id, current, to_stage,
          "Stage confirmed from Gmail review" if reviewed else "Stage updated from Gmail evidence",
          received_at, json.dumps({"source": "gmail", "message_id": message_id,
                                   "event_code": event_code, "reviewed": reviewed})))


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
                """, (datetime.now(timezone.utc).isoformat(), message["id"]))
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
        older_than_application = bool(app["applied_date"] and received_at[:10] < app["applied_date"])
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
    after = window_start or int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    if after > time.time() or after < (datetime.now(timezone.utc) - timedelta(days=30)).timestamp() - 60:
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
        response = await client.get(GMAIL_URL, headers=headers, params=params)
        response.raise_for_status()
        listing = response.json()
        result = {"scanned": 0, "saved": 0, "stage_changed": 0, "needs_review": 0,
                  "ignored_job_board": 0,
                  "more_available": bool(listing.get("nextPageToken")),
                  "next_page_token": listing.get("nextPageToken"), "window_start": after}
        for item in listing.get("messages", []):
            with get_db() as conn:
                review = conn.execute("SELECT status FROM gmail_review_items WHERE message_id = ?",
                                      (item["id"],)).fetchone()
                saved = conn.execute("SELECT 1 FROM gmail_application_messages WHERE message_id = ?",
                                     (item["id"],)).fetchone()
                if (review and review["status"] != "pending") or (saved and not review):
                    continue
            detail = await client.get(f"{GMAIL_URL}/{item['id']}", headers=headers,
                                      params={"format": "full"})
            detail.raise_for_status()
            outcome = _record_message(detail.json())
            result["scanned"] += 1
            result["saved"] += int(outcome["saved"])
            result["stage_changed"] += int(outcome["stage_changed"])
            result["needs_review"] += int(outcome["needs_review"])
            result["ignored_job_board"] += int(outcome.get("ignored_job_board", False))
        return result


def saved_messages(limit: int = 30) -> list[dict]:
    with get_db() as conn:
        return [dict(row) for row in conn.execute("""
            SELECT m.message_id, m.application_id, m.received_at, m.event_code,
                m.match_reason, m.stage_applied, j.company, j.title
            FROM gmail_application_messages m
            JOIN applications a ON a.id = m.application_id
            JOIN jobs j ON j.id = a.job_id
            WHERE m.match_reason != 'job_board_alert'
            ORDER BY m.received_at DESC LIMIT ?
        """, (limit,)).fetchall()]


def pending_reviews(limit: int = 50) -> dict:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT message_id, received_at, event_code, proposed_stage, reason_code,
                   candidate_application_ids
            FROM gmail_review_items WHERE status = 'pending'
            ORDER BY received_at DESC LIMIT ?
        """, (limit,)).fetchall()
        applications = [dict(row) for row in conn.execute("""
            SELECT a.id, a.current_stage, j.company, j.title
            FROM applications a JOIN jobs j ON j.id = a.job_id
            ORDER BY j.company, j.title
        """).fetchall()]
        reviews = []
        for row in rows:
            review = dict(row)
            review["candidate_application_ids"] = json.loads(review["candidate_application_ids"])
            reviews.append(review)
        return {"reviews": reviews, "applications": applications}


def resolve_review(message_id: str, action: str, application_id: str | None = None,
                   to_stage: str | None = None) -> dict:
    if action not in ("apply", "dismiss"):
        raise ValueError("Choose apply or dismiss")
    if action == "apply" and (not application_id or to_stage not in KANBAN_STAGES):
        raise ValueError("Choose an application and a valid stage")
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        review = conn.execute("SELECT * FROM gmail_review_items WHERE message_id = ?", (message_id,)).fetchone()
        if not review or review["status"] != "pending":
            raise ValueError("Review item is no longer pending")
        changed = False
        if action == "apply":
            app = conn.execute("SELECT current_stage, outcome FROM applications WHERE id = ?", (application_id,)).fetchone()
            if not app:
                raise ValueError("Application not found")
            changed = app["current_stage"] != to_stage or (
                to_stage == "closed" and review["event_code"] == "rejected" and app["outcome"] != "rejected"
            )
            if changed:
                _change_stage(conn, application_id, app["current_stage"], to_stage,
                              review["event_code"], review["received_at"], message_id, reviewed=True)
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
        conn.execute("UPDATE gmail_review_items SET status = ?, resolved_at = ? WHERE message_id = ?",
                     ("applied" if action == "apply" else "dismissed",
                      datetime.now(timezone.utc).isoformat(), message_id))
        conn.commit()
        return {"stage_changed": changed, "status": action}
