import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import crud, gmail_sync
from app.database import get_db, init_db
from app.main import app


@pytest.fixture(autouse=True)
def review_db(tmp_path, monkeypatch):
    path = tmp_path / "review.db"
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(path))
    init_db(path)
    with get_db() as conn:
        conn.execute("INSERT INTO jobs(id,company,title,status) VALUES('review-job','Synthetic Review','Operations Analyst','saved')")
        conn.execute("INSERT INTO applications(id,job_id,current_stage) VALUES('review-app','review-job','saved')")
        conn.commit()


def queue(message_id="review-message", event_body="Please book your onboarding session."):
    message = {
        "id": message_id, "threadId": "thread-" + message_id, "internalDate": "1792152000000",
        "payload": {"headers": [{"name": "Subject", "value": "Synthetic Review Operations Analyst"}],
                    "mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(event_body.encode()).decode()}},
    }
    gmail_sync._record_message(message)
    return message_id


def application_state():
    with get_db() as conn:
        return dict(conn.execute("SELECT a.current_stage,a.outcome,a.applied_date,a.next_followup_date,j.status FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.id='review-app'").fetchone())


def test_link_only_preserves_progress_and_can_be_undone():
    message_id = queue()
    before = application_state()
    with TestClient(app) as client:
        result = client.post(f"/api/gmail/reviews/{message_id}/resolve", json={"action": "link", "application_id": "review-app"})
        assert result.status_code == 200, result.text
        assert result.json()["stage_changed"] is False
        assert application_state() == before
        history = client.get("/api/gmail/reviews", params={"status": "processed"}).json()
        assert history["processed_count"] == 1
        assert history["pending_count"] == 0
        assert history["reviews"][0]["status"] == "linked"
        assert history["reviews"][0]["application_id"] == "review-app"
        assert history["reviews"][0]["can_undo"] is True
        undone = client.post(f"/api/gmail/reviews/{message_id}/undo")
        assert undone.status_code == 200, undone.text
    assert application_state() == before
    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM timeline_events").fetchone()[0] == 0
        assert conn.execute("SELECT status FROM gmail_review_items WHERE message_id=?", (message_id,)).fetchone()[0] == "pending"
        assert conn.execute("SELECT match_reason FROM gmail_application_messages WHERE message_id=?", (message_id,)).fetchone()[0] == "company_and_title"


def test_dismiss_undo_survives_refresh():
    message_id = queue()
    with TestClient(app) as client:
        assert client.post(f"/api/gmail/reviews/{message_id}/resolve", json={"action": "dismiss"}).status_code == 200
    with TestClient(app) as client:
        history = client.get("/api/gmail/reviews", params={"status": "processed"}).json()
        assert history["reviews"][0]["status"] == "dismissed"
        assert client.post(f"/api/gmail/reviews/{message_id}/undo").status_code == 200
        assert client.post(f"/api/gmail/reviews/{message_id}/undo").status_code == 200
        assert client.get("/api/gmail/reviews").json()["pending_count"] == 1


def test_progress_update_and_undo_restore_exact_application_state():
    message_id = queue(event_body="Thank you for applying. Your application has been received.")
    before = application_state()
    with TestClient(app) as client:
        resolved = client.post(f"/api/gmail/reviews/{message_id}/resolve", json={"action": "progress", "application_id": "review-app", "to_stage": "applied"})
        assert resolved.status_code == 200, resolved.text
        assert application_state()["current_stage"] == "applied"
        assert client.post(f"/api/gmail/reviews/{message_id}/undo").status_code == 200
    assert application_state() == before
    with get_db() as conn:
        event = conn.execute("SELECT metadata FROM timeline_events").fetchone()
        assert json.loads(event[0])["_deleted_at"]


def test_undo_never_overwrites_later_progress():
    message_id = queue()
    with TestClient(app) as client:
        assert client.post(f"/api/gmail/reviews/{message_id}/resolve", json={"action": "progress", "application_id": "review-app", "to_stage": "applied"}).status_code == 200
        crud.transition_application_stage("review-app", "offer")
        result = client.post(f"/api/gmail/reviews/{message_id}/undo")
        assert result.status_code == 400
        assert "later" in result.json()["detail"].lower()
    assert application_state()["current_stage"] == "offer"


def test_interview_progress_requires_confirmed_date_and_schedules_cadence():
    message_id = queue()
    with TestClient(app) as client:
        payload = {"action": "progress", "application_id": "review-app", "to_stage": "recruiter_screen"}
        assert client.post(f"/api/gmail/reviews/{message_id}/resolve", json=payload).status_code == 400
        payload["due_date"] = "2026-10-22"
        response = client.post(f"/api/gmail/reviews/{message_id}/resolve", json=payload)
        assert response.status_code == 200, response.text
        cadence = client.get("/api/pipeline/applications/review-app/cadence").json()
        assert cadence["kind"] in ("interview", "interview_review")
        assert cadence["due_date"] == "2026-10-22"


def test_pending_and_processed_counts_and_pagination():
    for index in range(4):
        queue(f"page-{index}")
    with TestClient(app) as client:
        client.post("/api/gmail/reviews/page-0/resolve", json={"action": "dismiss"})
        first = client.get("/api/gmail/reviews", params={"limit": 2}).json()
        second = client.get("/api/gmail/reviews", params={"limit": 2, "offset": 2}).json()
    assert first["pending_count"] == 3
    assert first["processed_count"] == 1
    assert first["has_more"] is True
    assert second["has_more"] is False
    assert len({r["message_id"] for r in first["reviews"] + second["reviews"]}) == 3


def test_same_stage_date_update_and_undo_restore_previous_reminder():
    first = queue('first-date')
    second = queue('second-date')
    with TestClient(app) as client:
        payload = {"action": "progress", "application_id": "review-app", "to_stage": "recruiter_screen", "due_date": "2026-10-22"}
        assert client.post(f'/api/gmail/reviews/{first}/resolve', json=payload).status_code == 200
        payload['due_date'] = '2026-10-23'
        updated = client.post(f'/api/gmail/reviews/{second}/resolve', json=payload)
        assert updated.status_code == 200, updated.text
        assert updated.json()['stage_changed'] is False
        assert client.get('/api/pipeline/applications/review-app/cadence').json()['due_date'] == '2026-10-23'
        assert client.post(f'/api/gmail/reviews/{second}/undo').status_code == 200
        assert client.get('/api/pipeline/applications/review-app/cadence').json()['due_date'] == '2026-10-22'


def test_closing_outcome_cannot_be_attached_to_an_active_stage():
    message_id = queue(event_body="We regret to inform you that your application was not selected.")
    before = application_state()
    with TestClient(app) as client:
        response = client.post(f"/api/gmail/reviews/{message_id}/resolve", json={
            "action": "progress", "application_id": "review-app", "to_stage": "offer", "outcome": "rejected",
        })
        assert response.status_code == 400
    assert application_state() == before


def test_old_receipt_can_be_recorded_without_regressing_later_progress():
    message_id = queue(event_body="Thank you for applying. Your application has been received.")
    crud.transition_application_stage("review-app", "knocked")
    with get_db() as conn:
        conn.execute("UPDATE timeline_events SET occurred_at='2026-10-17T12:00:00Z'")
        conn.commit()
    before = application_state()
    with TestClient(app) as client:
        response = client.post(f"/api/gmail/reviews/{message_id}/resolve", json={
            "action": "progress", "application_id": "review-app", "to_stage": "applied",
        })
    assert response.status_code == 200, response.text
    assert application_state() == before
    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM timeline_events WHERE event_type='acknowledgement'").fetchone()[0] == 1


def test_old_email_cannot_change_newer_closing_outcome_at_same_stage():
    message_id = queue(event_body="We regret to inform you that your application was not selected.")
    crud.transition_application_stage("review-app", "closed", outcome="offer_accepted")
    with get_db() as conn:
        conn.execute("UPDATE timeline_events SET occurred_at='2026-10-17T12:00:00Z'")
        conn.commit()
    with TestClient(app) as client:
        response = client.post(f"/api/gmail/reviews/{message_id}/resolve", json={
            "action": "progress", "application_id": "review-app", "to_stage": "closed", "outcome": "rejected",
        })
    assert response.status_code == 400
    assert application_state()["outcome"] == "offer_accepted"


def test_existing_database_gets_undo_column_without_losing_rows(tmp_path):
    path = Path(tmp_path) / "legacy.db"
    import sqlite3
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE gmail_review_items(message_id TEXT PRIMARY KEY,thread_id TEXT,received_at TEXT,event_code TEXT,proposed_stage TEXT,reason_code TEXT,candidate_application_ids TEXT,status TEXT,resolved_at TEXT,created_at TEXT)")
        conn.execute("INSERT INTO gmail_review_items(message_id,status) VALUES('legacy','dismissed')")
    init_db(path)
    with get_db(path) as conn:
        assert "resolution_metadata" in {r["name"] for r in conn.execute("PRAGMA table_info(gmail_review_items)")}
        assert conn.execute("SELECT status FROM gmail_review_items WHERE message_id='legacy'").fetchone()[0] == "dismissed"
