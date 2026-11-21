from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from app.database import get_db, init_db
from app.main import app
from app.clock import local_today


def test_dashboard_counts_full_population_and_deduplicates_attention(tmp_path, monkeypatch):
    db_path = tmp_path / "dashboard.db"
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(db_path))
    init_db(db_path)
    today = local_today()
    old_update = (datetime.now() - timedelta(days=20)).isoformat()

    with get_db(db_path) as conn:
        conn.executemany(
            "INSERT INTO jobs (id, title, company, status) VALUES (?, ?, ?, ?)",
            [(f"saved-{index}", "Synthetic role", "Example", "saved") for index in range(101)]
            + [("applied-job", "Analyst", "Example", "applied"),
               ("screen-job", "Coordinator", "Sample", "in_progress")],
        )
        conn.executemany(
            """INSERT INTO applications
               (id, job_id, current_stage, applied_date, next_followup_date, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                ("applied-app", "applied-job", "applied", (today-timedelta(days=20)).isoformat(), today.isoformat(), old_update),
                ("screen-app", "screen-job", "recruiter_screen", None, None, old_update),
            ],
        )
        conn.commit()

    response = TestClient(app).get("/api/pipeline/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["saved_jobs"] == 101  # Saved Jobs API is limited to 100 by default.
    assert data["submitted"] == 1
    assert data["active"] == 2
    assert data["followups_due"] == 0
    assert data['status_checks_due'] == 1
    assert data["stage_counts"]["applied"] == 1
    assert data["stage_counts"]["recruiter_screen"] == 1
    assert len(data["weekly_applications"]) == 12
    assert sum(week["count"] for week in data["weekly_applications"]) == 1
    assert [(item["application_id"], item["kind"]) for item in data["attention_items"]] == [
        ("applied-app", "status_check"),
        ("screen-app", "record_review"),
    ]
    assert data["analytics"]["cohorts"]["30d"]["applications"] == 1
    assert data["analytics"]["records_without_valid_applied_date"] == 1


def test_dashboard_conversions_use_dated_cohorts_and_visible_history(tmp_path, monkeypatch):
    db_path = tmp_path / "analytics.db"
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(db_path))
    monkeypatch.setattr("app.crud.local_today", lambda: date(2026, 4, 30))
    monkeypatch.setattr("app.clock.get_time_settings", lambda: {"timezone": "America/Chicago"})
    init_db(db_path)

    records = [
        ("screened", "closed", "rejected", "2026-04-01"),
        ("interview", "technical_interview", None, "2026-04-05"),
        ("offer", "closed", "offer_accepted", "2026-02-15"),
        ("older", "closed", "rejected", "2025-12-01"),
        ("recent", "applied", None, "2026-04-28"),
        ("snapshot", "recruiter_screen", None, "2026-04-08"),
        ("no-date", "recruiter_screen", None, None),
        ("pre-application", "applied", None, "2026-04-10"),
        ("saved", "saved", None, None),
        ("invalid", "applied", None, "not a date"),
    ]
    events = [
        ("screened", "interview_scheduled", "recruiter_screen", "2026-04-04T02:00:00+00:00", '{"due_date":"2026-04-09"}'),
        ("screened", "interview_scheduled", "technical_interview", "2026-04-08", None),
        ("screened", "interview_completed", None, "2026-04-09", None),
        ("screened", "interview_completed", "recruiter_screen", "2026-04-09", None),
        ("screened", "stage_updated", "closed", "2026-04-22", '{"outcome":"rejected"}'),
        ("interview", "stage_change", "technical_interview", "2026-04-10", None),
        ("interview", "interview_completed", None, "2026-04-14", '{"_deleted_at":"2026-04-16"}'),
        ("offer", "stage_updated", "closed", "2026-03-01", '{"outcome":"offer_accepted"}'),
        ("no-date", "interview_completed", "recruiter_screen", "2026-04-14", None),
        ("pre-application", "interview_scheduled", "recruiter_screen", "2026-04-08", None),
        ("pre-application", "stage_change", "offer", "2026-05-04", None),
        ("recent", "assessment_assigned", "assessment", "2026-04-29", None),
    ]
    with get_db(db_path) as conn:
        conn.executemany(
            "INSERT INTO jobs (id, title, company) VALUES (?, 'Synthetic role', 'Example')",
            [(f"job-{key}",) for key, *_ in records],
        )
        conn.executemany(
            "INSERT INTO applications (id, job_id, current_stage, outcome, applied_date) VALUES (?, ?, ?, ?, ?)",
            [(key, f"job-{key}", *rest) for key, *rest in records],
        )
        conn.executemany(
            """INSERT INTO timeline_events (id, application_id, event_type, to_stage, occurred_at, metadata, title)
               VALUES (?, ?, ?, ?, ?, ?, 'Synthetic event')""",
            [(str(index), *event) for index, event in enumerate(events)],
        )
        conn.commit()

    response = TestClient(app).get("/api/pipeline/dashboard")
    assert response.status_code == 200
    analytics = response.json()["analytics"]
    assert analytics["through_date"] == "2026-04-30"
    assert analytics["records_without_valid_applied_date"] == 2
    assert analytics["dated_records_with_unverified_milestones"] == 1
    assert analytics["cohorts"]["30d"] == {
        "start_date": "2026-04-01", "applications": 5, "with_interview": 2,
        "with_completed_interview": 1, "with_offer": 0, "median_days_to_interview": 3.5,
    }
    assert analytics["cohorts"]["90d"] == {
        "start_date": "2026-01-31", "applications": 6, "with_interview": 2,
        "with_completed_interview": 1, "with_offer": 1, "median_days_to_interview": 3.5,
    }
    assert analytics["cohorts"]["all"]["applications"] == 7


def test_dashboard_empty_cohort_has_no_time_to_interview(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(db_path))
    init_db(db_path)
    result = TestClient(app).get("/api/pipeline/dashboard")
    assert result.status_code == 200
    for cohort in result.json()["analytics"]["cohorts"].values():
        assert cohort["applications"] == cohort["with_interview"] == 0
        assert cohort["median_days_to_interview"] is None
