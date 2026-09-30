"""Regression coverage for clock boundaries and persisted time preferences."""

from datetime import datetime, timezone
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, init_db


def freeze_clock(monkeypatch, instant):
    from app import clock

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    monkeypatch.setattr(clock, "datetime", FrozenDatetime)


def test_settings_timezone_persists_and_rejects_unknown_names(tmp_path, monkeypatch):
    from app import clock

    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time-settings.json")
    client = TestClient(app)
    initial = client.get("/api/settings/time")
    assert initial.status_code == 200
    assert initial.json()["timezone"] == "America/Chicago"
    assert "Asia/Hong_Kong" in initial.json()["available_timezones"]
    response = client.put("/api/settings/time", json={"timezone": "Asia/Hong_Kong"})
    assert response.status_code == 200
    assert client.get("/api/settings/time").json()["timezone"] == "Asia/Hong_Kong"
    assert json.loads(clock.SETTINGS_PATH.read_text()) == {"timezone": "Asia/Hong_Kong"}
    for invalid in ("Central Standard Time", "../secret", "Mars/Olympus", "Factory", ""):
        assert client.put("/api/settings/time", json={"timezone": invalid}).status_code == 400
    assert client.get("/api/settings/time").json()["timezone"] == "Asia/Hong_Kong"


@pytest.mark.parametrize("saved", ["not-json", "[]", '{"timezone":"invalid"}', '{"timezone":null}'])
def test_invalid_settings_fall_back_without_rewriting_file(tmp_path, monkeypatch, saved):
    from app import clock

    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time-settings.json")
    clock.SETTINGS_PATH.write_text(saved)
    assert clock.get_time_settings()["timezone"] == "America/Chicago"
    assert clock.SETTINGS_PATH.read_text() == saved


@pytest.mark.parametrize("instant,want,offset", [
    ("2026-09-30T02:00:00+00:00", "2026-09-29", -5),
    ("2026-01-01T02:00:00+00:00", "2025-12-31", -6),
    ("2026-03-08T07:59:59+00:00", "2026-03-08", -6),
    ("2026-03-08T08:00:00+00:00", "2026-03-08", -5),
    ("2026-11-01T06:59:59+00:00", "2026-11-01", -5),
    ("2026-11-01T07:00:00+00:00", "2026-11-01", -6),
])
def test_local_clock_handles_midnight_and_dst(tmp_path, monkeypatch, instant, want, offset):
    from app import clock

    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time-settings.json")
    freeze_clock(monkeypatch, datetime.fromisoformat(instant))
    assert clock.local_today().isoformat() == want
    assert clock.local_now().utcoffset().total_seconds() == offset * 3600
    clock.save_time_settings("Asia/Hong_Kong")
    assert clock.local_now().utcoffset().total_seconds() == 8 * 3600


def test_manual_and_gmail_stages_use_same_local_calendar_day(tmp_path, monkeypatch):
    from app import clock, crud, gmail_sync

    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time-settings.json")
    freeze_clock(monkeypatch, datetime(2026, 9, 30, 2, tzinfo=timezone.utc))
    db_path = tmp_path / "time.db"
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(db_path))
    init_db()
    with get_db() as conn:
        for key in ("manual", "gmail"):
            conn.execute("INSERT INTO jobs (id, title, company) VALUES (?, 'Analyst', 'Example')", (key,))
        conn.commit()
    manual = crud.create_application_for_job("manual")
    gmail = crud.create_application_for_job("gmail")
    updated = crud.transition_application_stage(manual["id"], "applied")
    assert updated["applied_date"] == "2026-09-29"
    assert updated["next_followup_date"] == "2026-10-02"
    assert datetime.fromisoformat(updated["updated_at"]).utcoffset().total_seconds() == 0
    with get_db() as conn:
        gmail_sync._change_stage(conn, gmail["id"], "saved", "applied", "application_received",
                                 "2026-09-30T02:00:00+00:00", "synthetic-message", reviewed=True)
        result = conn.execute("SELECT * FROM applications WHERE id = ?", (gmail["id"],)).fetchone()
        assert result["applied_date"] == "2026-09-29"
        assert result["next_followup_date"] == "2026-10-02"


def test_document_directory_uses_local_day(tmp_path, monkeypatch):
    from app import clock
    from app.tailor.naming import generate_application_workspace_dirname

    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time-settings.json")
    freeze_clock(monkeypatch, datetime(2026, 9, 30, 2, tzinfo=timezone.utc))
    assert generate_application_workspace_dirname("Example", "Analyst") == "2026-09-29-example-analyst"
    clock.save_time_settings("Asia/Hong_Kong")
    assert generate_application_workspace_dirname("Example", "Analyst") == "2026-09-30-example-analyst"


def test_gmail_older_message_check_uses_local_day(tmp_path, monkeypatch):
    import base64
    from app import clock, gmail_sync

    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time-settings.json")
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(tmp_path / "gmail-day.db"))
    init_db()
    with get_db() as conn:
        conn.execute("INSERT INTO jobs (id, title, company) VALUES ('example', 'Operations Analyst', 'Example')")
        conn.execute("INSERT INTO applications (id, job_id, current_stage, applied_date) VALUES ('example-app', 'example', 'applied', '2026-09-30')")
        conn.commit()
    instant = datetime(2026, 9, 30, 2, tzinfo=timezone.utc)
    mail = {"id": "synthetic-old-mail", "threadId": "synthetic-thread",
            "internalDate": str(int(instant.timestamp() * 1000)),
            "payload": {"headers": [{"name": "Subject", "value": "Example Operations Analyst"}],
                        "mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(
                            b"Example Operations Analyst: Thank you for applying. Your application has been received.").decode()}}}
    gmail_sync._record_message(mail)
    with get_db() as conn:
        assert conn.execute("SELECT reason_code FROM gmail_review_items WHERE message_id = 'synthetic-old-mail'").fetchone()[0] == "older_message"


@pytest.mark.parametrize("legacy_schema", [False, True])
def test_database_defaults_are_explicit_utc_without_rewriting_legacy_rows(tmp_path, monkeypatch, legacy_schema):
    from app.database import SCHEMA_PATH

    db_path = tmp_path / "default.db"
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(db_path))
    if legacy_schema:
        schema = SCHEMA_PATH.read_text().replace("strftime('%Y-%m-%dT%H:%M:%fZ', 'now')", "datetime('now')")
        with get_db() as conn:
            conn.executescript(schema)
            conn.execute("INSERT INTO jobs (id, title, company, created_at) VALUES ('old-default', 'Role', 'Example', '2026-09-30 02:00:00')")
            conn.commit()
    init_db()
    with get_db() as conn:
        conn.execute("INSERT INTO jobs (id, title, company, created_at) VALUES ('legacy', 'Role', 'Example', '2026-09-29T21:00:00')")
        conn.execute("INSERT INTO jobs (id, title, company) VALUES ('new', 'Role', 'Example')")
        conn.commit()
    init_db()
    with get_db() as conn:
        new = conn.execute("SELECT created_at FROM jobs WHERE id = 'new'").fetchone()[0]
        assert datetime.fromisoformat(new).tzinfo is not None
        assert conn.execute("SELECT created_at FROM jobs WHERE id = 'legacy'").fetchone()[0] == "2026-09-29T21:00:00"
        if legacy_schema:
            assert conn.execute("SELECT created_at FROM jobs WHERE id = 'old-default'").fetchone()[0] == "2026-09-30 02:00:00"


def test_stale_comparison_uses_instants_instead_of_iso_string_order(tmp_path, monkeypatch):
    from app import clock, crud

    monkeypatch.setattr(clock, "SETTINGS_PATH", tmp_path / "time-settings.json")
    freeze_clock(monkeypatch, datetime(2026, 9, 30, 2, tzinfo=timezone.utc))
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(tmp_path / "stale.db"))
    init_db()
    with get_db() as conn:
        for key, value in [("stale", "2026-09-16T00:30:00+00:00"),
                           ("fresh", "2026-09-15T22:00:00-05:00")]:
            conn.execute("INSERT INTO jobs (id, title, company) VALUES (?, 'Analyst', 'Example')", (key,))
            conn.execute("INSERT INTO applications (id, job_id, current_stage, updated_at) VALUES (?, ?, 'applied', ?)",
                         (key, key, value))
        conn.commit()
    assert [row["id"] for row in crud.get_stale_applications(14)] == ["stale"]
