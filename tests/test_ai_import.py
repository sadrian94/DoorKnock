import sys
from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.main import app
from app.ai.profile import get_candidate_profile_context
from app.ai.gemini import GeminiClient


@pytest.fixture
def synthetic_evidence_file(tmp_path, monkeypatch):
    path = tmp_path / "workspace" / "master_resume" / "master_evidence.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump({
            "schema_version": 1,
            "headline": "Sample Analyst",
            "experiences": [{
                "id": "synthetic-experience-1",
                "company": "Apex Logistics",
                "role": "Operations Analyst",
                "location": "Sample City",
                "dates": "2024-2025",
                "bullets": [{
                    "id": "synthetic-bullet-1",
                    "category": "reporting",
                    "tags": ["sample"],
                    "metrics": ["12% synthetic change"],
                    "text": "Built a synthetic reporting workflow.",
                }],
            }],
            "projects": [],
            "technical_skills": {"analytics_and_bi": ["SQL"]},
            "education": [],
            "certifications": {"primary": [], "secondary": []},
        }, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.evidence.DOORKNOCK_MASTER_EVIDENCE_YAML_PATH", path)
    return path

@pytest.fixture
def client():
    return TestClient(app)

def test_candidate_profile_loader_uses_synthetic_yaml(synthetic_evidence_file):
    profile = get_candidate_profile_context()
    assert len(profile.strip()) > 50
    assert "Apex Logistics" in profile
    assert "synthetic-bullet-1" in profile

def test_analyze_endpoint_validation(client):
    # Test with empty text/url
    res = client.post("/api/jobs/analyze", json={})
    # If GEMINI_API_KEY is not set, it returns 400 (configured check) or validation
    assert res.status_code == 400

def test_import_job_endpoint(client):
    payload = {
        "title": "Senior Systems & Data Analyst",
        "company": "Enterprise Horizon Inc",
        "location": "Sample City",
        "workplace_type": "hybrid",
        "salary_min": 95000,
        "salary_max": 120000,
        "job_url": "https://example.com/jobs/123",
        "job_description": "Looking for a Business Systems Analyst with Python and SQL experience.",
        "job_brief": "Core analyst role governing operational data flows and reporting.",
        "suitability_score": 92.0,
        "suitability_reason": "The sample analysis identified relevant operational reporting experience.",
        "source": "direct_import"
    }

    job_id = None
    try:
        res = client.post("/api/jobs/import", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert "job" in data
        assert data["job"]["title"] == "Senior Systems & Data Analyst"
        assert data["job"]["company"] == "Enterprise Horizon Inc"
        assert "application_id" in data
        job_id = data["job"]["id"]

        # Verify job appears in saved jobs
        saved_res = client.get("/api/jobs/saved?search=Enterprise+Horizon")
        assert saved_res.status_code == 200
        saved_jobs = saved_res.json()["jobs"]
        assert any(j["company"] == "Enterprise Horizon Inc" for j in saved_jobs)
    finally:
        if job_id:
            client.delete(f"/api/jobs/{job_id}")

@pytest.mark.anyio
async def test_v2_tactical_brief_schema_mappings(synthetic_evidence_file):
    from unittest.mock import AsyncMock
    from app.ai.analyzer import analyze_job_posting

    mock_client = AsyncMock()
    mock_client.generate_json.return_value = {
        "title": "Lead Operations Analyst",
        "company": "Apex Freight Logistics",
        "triage": {
            "decision": "STRONG_KNOCK",
            "dealbreakers_detected": ["None"],
            "strategic_thesis": "Strong alignment with logistics reconciliation pipelines."
        },
        "employer_mandate": {
            "role_archetype": "OPTIMIZER",
            "acute_operational_frictions": [
                "Manual route schedule reconciliation latency",
                "Vendor SLA audit discrepancy tracking"
            ],
            "immediate_value_hook": "Deploys automated Python models to slash reconciliation cycle times."
        },
        "gaps_and_mitigation": [
            {
                "gap": "Lack of specialized TMS vendor platform exposure",
                "severity": "LOW",
                "compensating_evidence": "Extensive relational SQL data validation experience"
            }
        ]
    }

    result = await analyze_job_posting("Sample raw job text", gemini_client=mock_client)
    assert "Apex Logistics" in mock_client.generate_json.call_args.kwargs["prompt"]
    assert result["triage"]["decision"] == "STRONG_KNOCK"
    assert result["employer_mandate"]["role_archetype"] == "OPTIMIZER"
    # Verify backward compatibility mappings
    assert result["employer_pain_points"] == result["employer_mandate"]["acute_operational_frictions"]
    assert result["gaps_or_risks"] == ["Lack of specialized TMS vendor platform exposure"]
    assert result["suitability_reason"] == "Strong alignment with logistics reconciliation pipelines."

