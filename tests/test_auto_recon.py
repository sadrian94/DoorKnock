import asyncio
import json

import pytest
from fastapi import BackgroundTasks, HTTPException
from fastapi.testclient import TestClient

from app import crud
from app.api import jobs
from app.api.import_job import ImportConfirmedJobRequest, import_job
from app.main import app


def save_job():
    tasks = BackgroundTasks()
    result = import_job(ImportConfirmedJobRequest(
        title="Operations Analyst", company="Example Employer",
        job_description="Analyze operational reports and coordinate process improvements.",
    ), tasks)
    return result, tasks


@pytest.mark.anyio
async def test_save_returns_before_recon_then_persists_result(monkeypatch):
    async def research(**kwargs):
        assert kwargs["company"] == "Example Employer"
        assert kwargs["role_title"] == "Operations Analyst"
        return {"company_name": "Example Employer", "business_model": {"revenue_engine": "Services"}}

    monkeypatch.setattr(jobs, "require_ai_client", lambda: object())
    monkeypatch.setattr(jobs, "recon_company_and_department", research)
    result, tasks = save_job()
    job_id = result["job"]["id"]
    assert result["job"]["company_recon_status"] == "pending"
    assert crud.get_job_by_id(job_id)["company_recon_json"] is None
    await tasks()
    saved = crud.get_job_by_id(job_id)
    assert saved["company_recon_status"] == "completed"
    assert json.loads(saved["company_recon_json"])["business_model"]["revenue_engine"] == "Services"
    assert saved["application"]["current_stage"] == "saved"


@pytest.mark.anyio
async def test_failed_background_recon_keeps_job_and_allows_retry(monkeypatch):
    def unavailable():
        raise ValueError("AI is not configured")

    monkeypatch.setattr(jobs, "require_ai_client", unavailable)
    result, tasks = save_job()
    job_id = result["job"]["id"]
    await tasks()
    saved = crud.get_job_by_id(job_id)
    assert saved["company_recon_status"] == "failed"
    assert saved["application"]["current_stage"] == "saved"
    assert saved["company_recon_json"] is None

    async def research(**kwargs):
        return {"company_name": "Example Employer"}

    monkeypatch.setattr(jobs, "require_ai_client", lambda: object())
    monkeypatch.setattr(jobs, "recon_company_and_department", research)
    retried = await jobs.run_company_recon(job_id)
    assert retried["job"]["company_recon_status"] == "completed"


@pytest.mark.anyio
async def test_running_recon_rejects_duplicate_and_deleted_jobs_are_safe(monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()

    async def research(**kwargs):
        entered.set()
        await release.wait()
        return {"company_name": "Example Employer"}

    monkeypatch.setattr(jobs, "require_ai_client", lambda: object())
    monkeypatch.setattr(jobs, "recon_company_and_department", research)
    result, tasks = save_job()
    job_id = result["job"]["id"]
    worker = asyncio.create_task(tasks())
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        assert crud.get_job_by_id(job_id)["company_recon_status"] == "running"
        with pytest.raises(HTTPException) as error:
            await jobs.run_company_recon(job_id)
        assert error.value.status_code == 409
        crud.delete_job(job_id)
    finally:
        release.set()
        await worker
    assert crud.get_job_by_id(job_id) is None


def test_import_api_saves_despite_provider_failure(monkeypatch):
    async def research(**kwargs):
        raise RuntimeError("Provider failed")

    monkeypatch.setattr(jobs, "require_ai_client", lambda: object())
    monkeypatch.setattr(jobs, "recon_company_and_department", research)
    client = TestClient(app)
    response = client.post("/api/jobs/import", json={
        "title": "Analyst", "company": "Example Employer", "job_description": "Prepare reports",
    })
    assert response.status_code == 200
    job_id = response.json()["job"]["id"]
    assert client.get(f"/api/jobs/{job_id}").json()["company_recon_status"] == "failed"


def test_restart_marks_interrupted_recon_retryable():
    from app.main import recover_interrupted_recon

    result, _ = save_job()
    job_id = result["job"]["id"]
    recover_interrupted_recon()
    assert crud.get_job_by_id(job_id)["company_recon_status"] == "failed"


@pytest.mark.anyio
async def test_completed_background_task_is_not_repeated(monkeypatch):
    async def research(**kwargs):
        return {"company_name": "Example Employer"}

    monkeypatch.setattr(jobs, "require_ai_client", lambda: object())
    monkeypatch.setattr(jobs, "recon_company_and_department", research)
    result, tasks = save_job()
    job_id = result["job"]["id"]
    with pytest.raises(HTTPException) as error:
        await jobs.run_company_recon(job_id)
    assert error.value.status_code == 409
    await tasks()

    async def unexpected(**kwargs):
        raise RuntimeError("Must not repeat completed research")

    monkeypatch.setattr(jobs, "recon_company_and_department", unexpected)
    await tasks()
    assert crud.get_job_by_id(job_id)["company_recon_status"] == "completed"


@pytest.mark.anyio
async def test_timeout_preserves_previous_recon_and_marks_failure(monkeypatch):
    async def timeout(**kwargs):
        raise TimeoutError("Provider timed out")

    result, _ = save_job()
    job_id = result["job"]["id"]
    crud.update_job_company_recon(job_id, {"company_name": "Previous research"})
    monkeypatch.setattr(jobs, "require_ai_client", lambda: object())
    monkeypatch.setattr(jobs, "recon_company_and_department", timeout)
    with pytest.raises(HTTPException):
        await jobs.run_company_recon(job_id)
    saved = crud.get_job_by_id(job_id)
    assert saved["company_recon_status"] == "failed"
    assert json.loads(saved["company_recon_json"])["company_name"] == "Previous research"


def test_legacy_migration_preserves_existing_research(tmp_path):
    from app.database import init_db, get_db

    path = tmp_path / "legacy.db"
    init_db(path)
    with get_db(path) as conn:
        conn.execute("ALTER TABLE jobs DROP COLUMN company_recon_status")
        conn.execute("INSERT INTO jobs (id, title, company, company_recon_json) VALUES (?, ?, ?, ?)",
                     ("legacy", "Analyst", "Example Employer", '{"company_name":"Existing research"}'))
        conn.commit()
    init_db(path)
    init_db(path)
    with get_db(path) as conn:
        saved = dict(conn.execute("SELECT * FROM jobs WHERE id = 'legacy'").fetchone())
    assert saved["company_recon_status"] is None
    assert json.loads(saved["company_recon_json"])["company_name"] == "Existing research"
