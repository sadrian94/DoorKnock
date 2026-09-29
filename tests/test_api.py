import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.main import app
from app.database import get_db, init_db
from app import crud

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

@pytest.fixture
def client():
    return TestClient(app)


def _create_synthetic_job(client, title="Operations Analyst", company="Sample Analytics"):
    response = client.post("/api/jobs/import", json={
        "title": title,
        "company": company,
        "job_description": "A synthetic role used to verify application workflow behavior.",
        "source": "test",
    })
    assert response.status_code == 200
    return response.json()

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "DoorKnock"}

def test_get_saved_jobs(client):
    res = client.get("/api/jobs/saved")
    assert res.status_code == 200
    data = res.json()
    assert "jobs" in data
    assert "count" in data
    assert isinstance(data["jobs"], list)

def test_get_pipeline_kanban(client):
    res = client.get("/api/pipeline/kanban")
    assert res.status_code == 200
    data = res.json()
    assert "stages" in data
    assert "total_applications" in data
    assert "saved" in data["stages"]
    assert "applied" in data["stages"]
    assert "knocked" in data["stages"]

def test_stage_transition(client):
    job = _create_synthetic_job(client)
    app_id = job["application_id"]
    with get_db() as conn:
        conn.execute("UPDATE applications SET current_stage = 'applied' WHERE id = ?", (app_id,))
        conn.commit()

    patch_res = client.patch(f"/api/pipeline/applications/{app_id}/stage", json={"to_stage": "recruiter_screen"})
    assert patch_res.status_code == 200
    assert patch_res.json()["current_stage"] == "recruiter_screen"

    rej_res = client.patch(f"/api/pipeline/applications/{app_id}/stage", json={"to_stage": "rejected"})
    assert rej_res.status_code == 200
    assert rej_res.json()["current_stage"] == "closed"

    invalid_res = client.patch(f"/api/pipeline/applications/{app_id}/stage", json={"to_stage": "non_existent_stage"})
    assert invalid_res.status_code == 400

    back_res = client.patch(f"/api/pipeline/applications/{app_id}/stage", json={"to_stage": "applied"})
    assert back_res.status_code == 200
    assert back_res.json()["current_stage"] == "applied"
    assert back_res.json()["outcome"] is None

def test_delete_job(client):
    # First create a temporary job to delete
    create_res = client.post("/api/jobs/import", json={
        "title": "Temporary Job for Deletion",
        "company": "DeleteCorp",
        "job_description": "To be deleted.",
        "source": "test"
    })
    assert create_res.status_code == 200
    job_id = create_res.json()["job"]["id"]

    # Now delete it
    del_res = client.delete(f"/api/jobs/{job_id}")
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # Verify 404 on get
    get_res = client.get(f"/api/jobs/{job_id}")
    assert get_res.status_code == 404

def test_documents_api(client, tmp_path, monkeypatch):
    from app.api import documents
    from app import documents as document_service

    job = _create_synthetic_job(client, company="Sample Constructors")
    job_id = job["job"]["id"]
    applications_dir = tmp_path / "applications"
    app_dir = applications_dir / job_id
    resume_pdf = app_dir / "resume" / "v001" / "final.pdf"
    cover_pdf = app_dir / "cover-letter" / "v001" / "letter.pdf"
    resume_pdf.parent.mkdir(parents=True)
    cover_pdf.parent.mkdir(parents=True)
    resume_pdf.write_bytes(b"%PDF synthetic resume fixture")
    cover_pdf.write_bytes(b"%PDF synthetic cover letter fixture")
    monkeypatch.setattr(document_service, "APPLICATIONS_DIR", applications_dir)
    monkeypatch.setattr(document_service, "WORKSPACE_DIR", tmp_path)

    res = client.get(f"/api/jobs/{job_id}/documents")
    assert res.status_code == 200
    data = res.json()
    assert data["has_documents"] is True
    assert data["resume"]["available"] is True
    assert data["cover_letter"]["available"] is True

    # Test PDF stream inline
    pdf_res = client.get(f"/api/jobs/{job_id}/documents/resume")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers.get("content-type", "")
    assert "inline" in pdf_res.headers.get("content-disposition", "")

    # Test download mode
    dl_res = client.get(f"/api/jobs/{job_id}/documents/resume?download=true")
    assert dl_res.status_code == 200
    cd = dl_res.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "final.pdf" not in cd
    assert "Resume" in cd
    assert "Sample_Constructors" in cd

    # Test cover letter
    cl_res = client.get(f"/api/jobs/{job_id}/documents/cover-letter")
    assert cl_res.status_code == 200
    assert "application/pdf" in cl_res.headers.get("content-type", "")

    # Test non-existent document
    fake_res = client.get("/api/jobs/non-existent-id/documents/resume")
    assert fake_res.status_code == 404

def test_trigger_tailor_api_not_found(client):
    res = client.post("/api/jobs/non-existent-job-id/tailor/resume")
    assert res.status_code == 404

def test_trigger_tailor_api_success(client, monkeypatch):
    job_id = _create_synthetic_job(client)["job"]["id"]
    
    requested_types = []

    async def mock_tailor(job, document_type):
        requested_types.append(document_type)
        return {
            "success": True,
            "manifest": {
                "tailor_strategy": {
                    "target_role_header": "DATA ANALYST",
                    "primary_angle": "Test Angle",
                }
            }
        }

    from app.api import documents
    monkeypatch.setattr(documents, "tailor_application_documents", mock_tailor)

    res = client.post(f"/api/jobs/{job_id}/tailor/resume")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Typst" in data["message"]
    assert "documents_info" in data
    assert data["document_type"] == "resume"
    letter_res = client.post(f"/api/jobs/{job_id}/tailor/cover-letter")
    assert letter_res.status_code == 200
    assert letter_res.json()["document_type"] == "cover_letter"
    assert requested_types == ["resume", "cover_letter"]
    assert client.post(f"/api/jobs/{job_id}/tailor/invalid").status_code == 400
    assert client.post(f"/api/jobs/{job_id}/tailor").status_code in (404, 405)
    assert requested_types == ["resume", "cover_letter"]


def test_trigger_tailor_api_reports_page_limit(client, monkeypatch):
    from app.api import documents
    job_id = _create_synthetic_job(client)["job"]["id"]

    async def mock_tailor(job, document_type):
        return {"success": False, "compilation": {
            "page_count": 2, "text_complete": True, "page_limit_required": True,
        }}

    monkeypatch.setattr(documents, "tailor_application_documents", mock_tailor)
    res = client.post(f"/api/jobs/{job_id}/tailor/resume")
    assert res.status_code == 500
    assert res.json()["detail"] == "Document exceeds one page (2 pages)"

def test_contacts_and_outreach_api_flow(client):
    job_id = _create_synthetic_job(client)["job"]["id"]

    # 1. Create a gatekeeper contact
    contact_payload = {
        "name": "Jane Fictional",
        "role_title": "Lead Analytics Manager",
        "contact_type": "hiring_manager",
        "linkedin_url": "https://linkedin.com/in/fictional-jane",
        "email": "jane.fictional@example.com",
        "notes": "Spoke at local data summit regarding ETL bottlenecks."
    }
    res = client.post(f"/api/jobs/{job_id}/contacts", json=contact_payload)
    assert res.status_code == 200
    contact = res.json()
    assert contact["name"] == "Jane Fictional"
    assert contact["role_title"] == "Lead Analytics Manager"
    contact_id = contact["id"]

    # 2. Add an outreach message draft
    msg_payload = {
        "channel": "linkedin_connect",
        "archetype": "pain_point_solution",
        "body": "Reviewed a sample reconciliation report built from fictional routing records.",
        "status": "draft"
    }
    msg_res = client.post(f"/api/jobs/contacts/{contact_id}/messages", json=msg_payload)
    assert msg_res.status_code == 200
    msg = msg_res.json()
    assert msg["status"] == "draft"
    assert "fictional routing records" in msg["body"]
    msg_id = msg["id"]

    # 3. Update outreach message status
    patch_res = client.patch(f"/api/jobs/messages/{msg_id}/status", json={"status": "ready_to_send"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "ready_to_send"

def test_stale_and_followup_queries(client):
    res_stale = client.get("/api/pipeline/stale?days=0")
    assert res_stale.status_code == 200
    assert "stale_applications" in res_stale.json()

    res_fu = client.get("/api/pipeline/followups?days=30")
    assert res_fu.status_code == 200
    assert "upcoming_followups" in res_fu.json()

def test_database_is_isolated():
    """Verify that test suite operates strictly on an isolated database."""
    from app.config import get_db_path, DATA_DIR
    active_path = get_db_path().resolve()
    prod_path = (DATA_DIR / "jobs.db").resolve()
    assert active_path != prod_path, "Tests must never run directly against production jobs.db"

def test_rematch_endpoint(client, monkeypatch):
    # Create temporary job with JD
    create_res = client.post("/api/jobs/import", json={
        "title": "Data Pipeline Engineer",
        "company": "TestPipeline Corp",
        "job_description": "We are seeking a senior data engineer to optimize high-throughput SQL and Python ETL pipelines with rigorous automated testing.",
        "source": "test"
    })
    assert create_res.status_code == 200
    job_id = create_res.json()["job"]["id"]

    try:
        from unittest.mock import AsyncMock
        mock_analysis = {
            "title": "Data Pipeline Engineer",
            "company": "TestPipeline Corp",
            "suitability_score": 88.0,
            "suitability_reason": "Direct match for Python and SQL automation.",
            "triage": {
                "decision": "STRONG_KNOCK",
                "dealbreakers_detected": ["None"],
                "strategic_thesis": "Direct match for Python and SQL automation."
            },
            "employer_mandate": {
                "role_archetype": "OPTIMIZER",
                "acute_operational_frictions": ["Pipeline latency", "ETL failure recovery"],
                "immediate_value_hook": "Deploys automated Python testing loops."
            },
            "gaps_and_mitigation": []
        }

        # Mock analyze_job_posting
        async def mock_analyze(*args, **kwargs):
            return mock_analysis

        monkeypatch.setattr("app.api.jobs.analyze_job_posting", mock_analyze)

        res = client.post(f"/api/jobs/{job_id}/rematch")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["job"]["suitability_score"] == 88.0
        assert "STRONG_KNOCK" in data["job"]["analysis_json"]
    finally:
        client.delete(f"/api/jobs/{job_id}")

def test_recon_and_outreach_api(client, monkeypatch):
    create_res = client.post("/api/jobs/import", json={
        "title": "Full-Stack Engineer",
        "company": "AudioGen Corp",
        "job_description": "Build low latency audio streaming and web editor.",
        "source": "test"
    })
    assert create_res.status_code == 200
    job_id = create_res.json()["job"]["id"]

    try:
        # Mock recon
        mock_recon = {
            "company_name": "AudioGen Corp",
            "business_model": {
                "revenue_engine": "B2B SaaS API",
                "target_customers": "Media studios",
                "value_proposition": "Low-latency voice",
                "macro_challenges": "GPU scale"
            },
            "company_stage": {
                "scale_and_momentum": "Series B",
                "funding_or_tier": "Growth / Series B-D",
                "market_standing": "Challenger"
            },
            "department_intel": {
                "team_name": "Studio Experience",
                "team_charter": "Frontline Profit Center",
                "role_archetype": "BUILDER",
                "hiring_manager_profile": "Head of Engineering",
                "manager_core_pressure": "Editor stability"
            },
            "strategic_positioning_for_candidate": {
                "tailor_summary_angle": "Highlight streaming",
                "cover_letter_hook_angle": "Open with latency"
            }
        }
        async def mock_recon_fn(*args, **kwargs):
            return mock_recon

        monkeypatch.setattr("app.api.jobs.recon_company_and_department", mock_recon_fn)

        recon_res = client.post(f"/api/jobs/{job_id}/recon")
        assert recon_res.status_code == 200
        recon_data = recon_res.json()
        assert recon_data["ok"] is True
        assert recon_data["recon"]["company_name"] == "AudioGen Corp"

        # Check GET /recon
        get_recon_res = client.get(f"/api/jobs/{job_id}/recon")
        assert get_recon_res.status_code == 200
        assert get_recon_res.json()["recon"]["department_intel"]["team_name"] == "Studio Experience"

        # Add a contact
        contact_res = client.post(f"/api/jobs/{job_id}/contacts", json={
            "name": "Alex Tech Lead",
            "role_title": "Director of Engineering",
            "contact_type": "hiring_manager"
        })
        assert contact_res.status_code == 200
        contact_id = contact_res.json()["id"]

        # Mock outreach generation
        mock_messages = [
            {
                "id": "msg-001",
                "contact_id": contact_id,
                "channel": "linkedin_connect",
                "archetype": "pain_point_solution",
                "subject": None,
                "body": "Hi Alex, saw AudioGen's Studio expansion. Handled low-latency streaming in past systems.",
                "status": "draft"
            }
        ]
        async def mock_outreach_fn(*args, **kwargs):
            return mock_messages

        monkeypatch.setattr("app.api.jobs.generate_outreach_for_contact", mock_outreach_fn)

        outreach_res = client.post(f"/api/jobs/{job_id}/contacts/{contact_id}/generate-outreach")
        assert outreach_res.status_code == 200
        assert len(outreach_res.json()["messages"]) == 1

        # Test PATCH contact (updating contact details in DB)
        patch_res = client.patch(f"/api/jobs/contacts/{contact_id}", json={
            "role_title": "VP of Engineering",
            "notes": "Verified via LinkedIn MCP"
        })
        assert patch_res.status_code == 200
        assert patch_res.json()["role_title"] == "VP of Engineering"
        assert patch_res.json()["notes"] == "Verified via LinkedIn MCP"

        # Test DELETE contact (deleting contact and its messages from DB)
        del_contact_res = client.delete(f"/api/jobs/contacts/{contact_id}")
        assert del_contact_res.status_code == 200
        assert del_contact_res.json()["ok"] is True

        # Verify contact is gone from job detail
        get_job_res = client.get(f"/api/jobs/{job_id}")
        assert len(get_job_res.json()["contacts"]) == 0

    finally:
        client.delete(f"/api/jobs/{job_id}")





