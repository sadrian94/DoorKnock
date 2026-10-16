import json
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app import gmail_sync
from app.database import get_db
from app.main import app


@pytest.fixture
def gmail_http(tmp_path, monkeypatch):
    """Keep token writes local and replace only Google's HTTP transport."""
    token_path = tmp_path / "gmail-token.json"
    token_path.write_text(json.dumps({
        "access_token": "synthetic-access",
        "refresh_token": "synthetic-refresh",
        "expires_at": time.time() + 3600,
    }), encoding="utf-8")
    monkeypatch.setattr(gmail_sync, "TOKEN_PATH", token_path)
    monkeypatch.setenv("GMAIL_CLIENT_ID", "synthetic-client")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "synthetic-secret")
    original_client = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr(gmail_sync.httpx, "AsyncClient", lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs))

    return token_path, install


@pytest.mark.parametrize("days", [14, 30])
def test_scan_continues_same_window_after_waiting(days, gmail_http, monkeypatch):
    _, install = gmail_http
    now = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(gmail_sync, "utc_now", lambda: now)
    queries = []

    def google(request):
        assert request.headers["Authorization"] == "Bearer synthetic-access"
        queries.append(dict(request.url.params))
        return httpx.Response(200, json={"messages": [], "nextPageToken": "page-two"})

    install(google)
    with TestClient(app) as client:
        first = client.post("/api/gmail/scan", json={"recent_days": days})
        assert first.status_code == 200
        now += timedelta(minutes=90)
        second = client.post("/api/gmail/scan", json={
            "recent_days": days,
            "page_token": first.json()["next_page_token"],
            "window_start": first.json()["window_start"],
        })
    assert second.status_code == 200, second.text
    assert second.json()["window_start"] == first.json()["window_start"]
    assert queries[1]["q"] == queries[0]["q"]
    assert queries[1]["pageToken"] == "page-two"


def test_scan_requires_window_when_continuing(gmail_http):
    _, install = gmail_http
    install(lambda request: httpx.Response(200, json={"messages": []}))
    with TestClient(app) as client:
        response = client.post("/api/gmail/scan", json={"page_token": "page-two"})
    assert response.status_code == 400
    assert "start a new scan" in response.json()["detail"].lower()


def test_scan_continuation_expires_after_24_hours(gmail_http, monkeypatch):
    _, install = gmail_http
    now = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(gmail_sync, "utc_now", lambda: now)
    install(lambda request: httpx.Response(200, json={"messages": [], "nextPageToken": "page-two"}))
    with TestClient(app) as client:
        first = client.post("/api/gmail/scan", json={"recent_days": 14}).json()
        now += timedelta(hours=24, seconds=1)
        response = client.post("/api/gmail/scan", json={
            "recent_days": 14, "page_token": first["next_page_token"],
            "window_start": first["window_start"],
        })
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.parametrize("expired", [False, True])
def test_revoked_refresh_requires_reconnect_and_recovers_after_sign_in(gmail_http, monkeypatch, expired):
    token_path, install = gmail_http
    token = json.loads(token_path.read_text(encoding="utf-8"))
    if expired:
        token["expires_at"] = 0
    token_path.write_text(json.dumps(token), encoding="utf-8")
    revoked = True

    def google(request):
        if request.url.path == "/token":
            if revoked:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json={
                "access_token": "synthetic-new", "refresh_token": "synthetic-new-refresh",
                "token_type": "Bearer", "expires_in": 3600,
            })
        if revoked:
            return httpx.Response(401, json={"error": {"code": 401, "message": "Invalid Credentials"}})
        return httpx.Response(200, json={"messages": []})

    install(google)
    with TestClient(app) as client:
        failed = client.post("/api/gmail/scan", json={})
        assert failed.status_code == 400
        assert "reconnect" in failed.json()["detail"].lower()
        status = client.get("/api/gmail/status").json()
        assert status["connected"] is False
        assert status["reconnect_required"] is True
        retry = client.post("/api/gmail/scan", json={})
        assert retry.status_code == 400
        assert "reconnect" in retry.json()["detail"].lower()

        revoked = False
        monkeypatch.setattr(gmail_sync, "_pending_states", {"synthetic-state": time.time() + 600})
        callback = client.get("/api/gmail/callback", params={"state": "synthetic-state", "code": "synthetic-code"})
        assert callback.status_code == 200
        status = client.get("/api/gmail/status").json()
        assert status["connected"] is True
        assert status["reconnect_required"] is False
        assert client.post("/api/gmail/scan", json={}).status_code == 200


@pytest.mark.parametrize("failure_at", ["listing", "detail"])
@pytest.mark.parametrize("retry_succeeds", [False, True])
def test_rejected_access_token_refreshes_and_retries_once(gmail_http, failure_at, retry_succeeds):
    _, install = gmail_http
    authorizations = []

    def google(request):
        if request.url.path == "/token":
            return httpx.Response(200, json={
                "access_token": "synthetic-renewed", "expires_in": 3600, "token_type": "Bearer",
            })
        is_detail = request.url.path.endswith("/synthetic-auth-message")
        target = is_detail if failure_at == "detail" else not is_detail
        if target:
            authorizations.append(request.headers["Authorization"])
        if target and (not retry_succeeds or request.headers["Authorization"] == "Bearer synthetic-access"):
            return httpx.Response(401, json={"error": {"code": 401}})
        if is_detail:
            return httpx.Response(200, json={
                "id": "synthetic-auth-message", "threadId": "synthetic-auth-thread",
                "internalDate": "1792152000000", "payload": {"headers": []},
            })
        return httpx.Response(200, json={"messages": [{"id": "synthetic-auth-message"}]})

    install(google)
    with TestClient(app) as client:
        response = client.post("/api/gmail/scan", json={})
        assert response.status_code == (200 if retry_succeeds else 400)
        status = client.get("/api/gmail/status").json()
        assert status["connected"] is retry_succeeds
        assert status["reconnect_required"] is not retry_succeeds
    assert authorizations == ["Bearer synthetic-access", "Bearer synthetic-renewed"]


def test_transient_refresh_failure_preserves_connection(gmail_http):
    token_path, install = gmail_http
    token = json.loads(token_path.read_text(encoding="utf-8"))
    token["expires_at"] = 0
    token_path.write_text(json.dumps(token), encoding="utf-8")
    install(lambda request: httpx.Response(503, json={"error": "temporarily_unavailable"}))
    with TestClient(app) as client:
        response = client.post("/api/gmail/scan", json={})
        assert response.status_code == 502
        assert client.get("/api/gmail/status").json()["connected"] is True
    assert json.loads(token_path.read_text(encoding="utf-8"))["refresh_token"] == "synthetic-refresh"


@pytest.mark.parametrize("contents", ["{broken", "{}", '{"access_token":"synthetic","expires_at":0}'])
def test_unusable_credentials_report_reconnect_in_status(gmail_http, contents):
    token_path, _ = gmail_http
    token_path.write_text(contents, encoding="utf-8")
    with TestClient(app) as client:
        status = client.get("/api/gmail/status").json()
    assert status["connected"] is False
    assert status["reconnect_required"] is True


def test_scan_skips_recorded_messages_including_pending_reviews(gmail_http):
    _, install = gmail_http
    prefix = "synthetic-skip-"
    with get_db() as conn:
        for status in ("pending", "dismissed", "filtered"):
            conn.execute("""INSERT INTO gmail_review_items
                (message_id,thread_id,received_at,event_code,reason_code,candidate_application_ids,status)
                VALUES (?,?,'2026-10-16T12:00:00Z','related','unclear_event','[]',?)""",
                (prefix + status, "synthetic-thread", status))
        conn.execute("INSERT INTO jobs (id,company,title) VALUES (?, 'Synthetic Skip', 'Analyst')", (prefix + "job",))
        conn.execute("INSERT INTO applications (id,job_id,current_stage) VALUES (?,?,'applied')",
                     (prefix + "application", prefix + "job"))
        conn.execute("""INSERT INTO gmail_application_messages
            (message_id,thread_id,application_id,received_at,event_code,match_reason)
            VALUES (?, ?, ?, '2026-10-16T12:00:00Z', 'related', 'company_and_title')""",
            (prefix + "saved", "synthetic-thread", prefix + "application"))
        conn.commit()
    fetched = []

    def google(request):
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [
                {"id": prefix + suffix} for suffix in ("pending", "dismissed", "filtered", "saved", "new")
            ]})
        fetched.append(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(200, json={
            "id": prefix + "new", "threadId": "synthetic-thread",
            "internalDate": "1792152000000", "payload": {"headers": []},
        })

    install(google)
    with TestClient(app) as client:
        response = client.post("/api/gmail/scan", json={})
    assert response.status_code == 200
    assert response.json()["scanned"] == 1
    assert response.json()["skipped"] == 4
    assert fetched == [prefix + "new"]
    with get_db() as conn:
        assert conn.execute("SELECT status FROM gmail_review_items WHERE message_id=?",
                            (prefix + "pending",)).fetchone()[0] == "pending"
