from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from app.database import get_db, init_db
from app.main import app


def test_dashboard_counts_full_population_and_deduplicates_attention(tmp_path, monkeypatch):
    db_path = tmp_path / "dashboard.db"
    monkeypatch.setenv("DOORKNOCK_DB_PATH", str(db_path))
    init_db(db_path)
    today = date.today()
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
                ("applied-app", "applied-job", "applied", today.isoformat(), today.isoformat(), old_update),
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
    assert data["followups_due"] == 1
    assert data["stage_counts"]["applied"] == 1
    assert data["stage_counts"]["recruiter_screen"] == 1
    assert len(data["weekly_applications"]) == 12
    assert sum(week["count"] for week in data["weekly_applications"]) == 1
    assert [(item["application_id"], item["kind"]) for item in data["attention_items"]] == [
        ("applied-app", "followup"),
        ("screen-app", "stale"),
    ]
