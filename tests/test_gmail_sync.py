import base64
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest

from app.database import get_db
from app.gmail_sync import _record_message, _event, _match_application, pending_reviews, resolve_review
from app.main import app


def _seed(company="Example Analytics", title="Operations Analyst", stage="applied"):
    job_id, app_id = str(uuid.uuid4()), str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO jobs (id, company, title, status) VALUES (?, ?, ?, 'applied')",
                     (job_id, company, title))
        conn.execute("INSERT INTO applications (id, job_id, current_stage) VALUES (?, ?, ?)",
                     (app_id, job_id, stage))
        conn.commit()
    return app_id


def _mail(subject, body, message_id=None, headers=None):
    encoded = base64.urlsafe_b64encode(body.encode()).decode().rstrip("=")
    return {
        "id": message_id or str(uuid.uuid4()), "threadId": "synthetic-thread",
        "internalDate": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        "payload": {"headers": [{"name": "Subject", "value": subject}] + [
            {"name": name, "value": value} for name, value in (headers or {}).items()
        ],
                    "mimeType": "text/plain", "body": {"data": encoded}},
    }


def test_clear_rejection_updates_once_and_saves_reference():
    app_id = _seed()
    mail = _mail("Example Analytics Operations Analyst", "We regret to inform you that your application for the Operations Analyst position at Example Analytics was not selected.")
    assert _record_message(mail) == {"saved": True, "stage_changed": False, "needs_review": True}
    assert _record_message(mail) == {"saved": False, "stage_changed": False, "needs_review": False}
    with get_db() as conn:
        app = conn.execute("SELECT current_stage, outcome FROM applications WHERE id = ?", (app_id,)).fetchone()
        assert (app["current_stage"], app["outcome"]) == ("applied", None)
        assert conn.execute("SELECT COUNT(*) FROM timeline_events WHERE application_id = ?", (app_id,)).fetchone()[0] == 0
        saved = conn.execute("SELECT event_code, stage_applied FROM gmail_application_messages WHERE message_id = ?", (mail["id"],)).fetchone()
        assert tuple(saved) == ("rejected", 0)
    review = next(item for item in pending_reviews()["reviews"] if item["message_id"] == mail["id"])
    assert review["reason_code"] == "human_confirmation_required"
    assert resolve_review(mail["id"], "apply", app_id, "closed") == {"stage_changed": True, "status": "apply"}
    with get_db() as conn:
        app = conn.execute("SELECT current_stage, outcome FROM applications WHERE id = ?", (app_id,)).fetchone()
        assert (app["current_stage"], app["outcome"]) == ("closed", "rejected")
        assert conn.execute("SELECT COUNT(*) FROM timeline_events WHERE application_id = ?", (app_id,)).fetchone()[0] == 1


def test_ambiguous_role_does_not_change_application():
    _seed(company="Sample Group", title="Data Analyst")
    _seed(company="Sample Group", title="Data Analyst")
    mail = _mail("Sample Group Data Analyst", "We regret to inform you that your application for the Data Analyst position at Sample Group was not selected.")
    assert _record_message(mail) == {"saved": False, "stage_changed": False, "needs_review": True}
    assert any(item["message_id"] == mail["id"] for item in pending_reviews()["reviews"])


def test_announcement_is_not_a_stage_event():
    _seed(company="Demo Works", title="Business Analyst")
    mail = _mail("Demo Works Business Analyst", "See new jobs and other candidates at Demo Works.")
    assert _record_message(mail) == {"saved": True, "stage_changed": False, "needs_review": True}


def test_scheduled_interview_advances_only_from_early_stage():
    app_id = _seed(company="North Star", title="Program Analyst")
    mail = _mail("North Star Program Analyst phone screen", "Your recruiter interview is scheduled for Monday at 10:30 for the Program Analyst position at North Star.")
    assert _record_message(mail) == {"saved": True, "stage_changed": False, "needs_review": True}
    with get_db() as conn:
        assert conn.execute("SELECT current_stage FROM applications WHERE id = ?", (app_id,)).fetchone()[0] == "applied"
    review = next(item for item in pending_reviews()["reviews"] if item["message_id"] == mail["id"])
    assert review["reason_code"] == "human_confirmation_required"


def test_company_and_role_both_required():
    _seed(company="Cedar Labs", title="Research Coordinator")
    with get_db() as conn:
        assert _match_application(conn, "Research Coordinator", "") is None
        assert _match_application(conn, "Cedar Labs", "") is None


def test_vague_rejection_not_auto_classified():
    assert _event("Update", "Unfortunately we had many candidates.") is None


def test_review_requires_human_selection_before_ambiguous_stage_change():
    first_id = _seed(company="Synthetic Harbor", title="Data Specialist")
    _seed(company="Synthetic Harbor", title="Data Specialist")
    mail = _mail("Synthetic Harbor Data Specialist", "We regret to inform you that your application for the Data Specialist position at Synthetic Harbor was not selected.")
    assert _record_message(mail)["needs_review"] is True
    with get_db() as conn:
        assert conn.execute("SELECT current_stage FROM applications WHERE id = ?", (first_id,)).fetchone()[0] == "applied"
    assert resolve_review(mail["id"], "apply", first_id, "closed") == {"stage_changed": True, "status": "apply"}
    with get_db() as conn:
        app = conn.execute("SELECT current_stage, outcome FROM applications WHERE id = ?", (first_id,)).fetchone()
        assert tuple(app) == ("closed", "rejected")
        assert conn.execute("SELECT status FROM gmail_review_items WHERE message_id = ?", (mail["id"],)).fetchone()[0] == "applied"
        assert conn.execute("SELECT COUNT(*) FROM timeline_events WHERE application_id = ?", (first_id,)).fetchone()[0] == 1


def test_review_can_be_dismissed_without_stage_change():
    app_id = _seed(company="Synthetic Vale", title="Project Coordinator")
    mail = _mail("Synthetic Vale Project Coordinator", "We would like to talk about the Project Coordinator role at Synthetic Vale.")
    assert _record_message(mail)["needs_review"] is True
    assert resolve_review(mail["id"], "dismiss") == {"stage_changed": False, "status": "dismiss"}
    with get_db() as conn:
        assert conn.execute("SELECT current_stage FROM applications WHERE id = ?", (app_id,)).fetchone()[0] == "applied"
        assert conn.execute("SELECT status FROM gmail_review_items WHERE message_id = ?", (mail["id"],)).fetchone()[0] == "dismissed"


def test_clear_event_without_application_is_queued_for_manual_assignment():
    app_id = _seed(company="Synthetic Bridge", title="Operations Associate")
    mail = _mail("Update from another employer", "We regret to inform you that your application for another position was not selected.")
    assert _record_message(mail) == {"saved": False, "stage_changed": False, "needs_review": True}
    review = next(item for item in pending_reviews()["reviews"] if item["message_id"] == mail["id"])
    assert review["reason_code"] == "no_application_match"
    assert review["candidate_application_ids"] == []
    with get_db() as conn:
        assert conn.execute("SELECT current_stage FROM applications WHERE id = ?", (app_id,)).fetchone()[0] == "applied"


@pytest.mark.parametrize("sender", [
    "LinkedIn Job Alerts <alerts@linkedin.com>",
    "Handshake <jobs@joinhandshake.com>",
    "HiringCafe <updates@hiring.cafe>",
])
def test_job_board_digest_is_filtered_before_application_matching(sender):
    app_id = _seed(company="Synthetic Bay", title="Operations Analyst")
    mail = _mail("New jobs for you: Operations Analyst at Synthetic Bay",
                 "Synthetic Bay Operations Analyst. We regret to inform you that your application was not selected.",
                 headers={"From": sender, "List-Unsubscribe": "<mailto:unsubscribe@example.invalid>"})
    assert _record_message(mail) == {"saved": False, "stage_changed": False,
                                     "needs_review": False, "ignored_job_board": True}
    with get_db() as conn:
        assert conn.execute("SELECT current_stage FROM applications WHERE id = ?", (app_id,)).fetchone()[0] == "applied"
        row = conn.execute("SELECT status, reason_code FROM gmail_review_items WHERE message_id = ?", (mail["id"],)).fetchone()
        assert tuple(row) == ("filtered", "job_board_alert")


def test_direct_board_application_update_is_not_filtered():
    app_id = _seed(company="Synthetic Oak", title="Business Analyst", stage="saved")
    mail = _mail("Your application to Synthetic Oak for Business Analyst",
                 "Thank you for applying to the Business Analyst position at Synthetic Oak.",
                 headers={"From": "LinkedIn <updates@linkedin.com>"})
    assert _record_message(mail) == {"saved": True, "stage_changed": False, "needs_review": True}
    with get_db() as conn:
        assert conn.execute("SELECT current_stage FROM applications WHERE id = ?", (app_id,)).fetchone()[0] == "saved"
    assert any(item["message_id"] == mail["id"] for item in pending_reviews()["reviews"])


def test_rescan_filters_existing_pending_job_board_review():
    _seed(company="Synthetic Field", title="Program Assistant")
    mail = _mail("Synthetic Field Program Assistant", "See jobs at Synthetic Field.")
    assert _record_message(mail)["needs_review"] is True
    mail["payload"]["headers"].extend([
        {"name": "From", "value": "Handshake <jobs@joinhandshake.com>"},
        {"name": "Subject", "value": "New jobs for you: Synthetic Field Program Assistant"},
    ])
    assert _record_message(mail)["ignored_job_board"] is True
    assert all(item["message_id"] != mail["id"] for item in pending_reviews()["reviews"])


def test_scan_api_enforces_requested_bounds_and_exposes_saved_refs():
    with TestClient(app) as client:
        assert client.post("/api/gmail/scan", json={"recent_days": 14, "limit": 99}).status_code == 422
        assert client.post("/api/gmail/scan", json={"recent_days": 14, "limit": 201}).status_code == 422
        response = client.get("/api/gmail/messages")
        assert response.status_code == 200
        assert "messages" in response.json()
