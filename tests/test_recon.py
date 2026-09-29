import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.ai.recon import recon_company_and_department, RECON_PROMPT_TEMPLATE
from app.ai.gemini import GeminiClient
from app import crud

def test_recon_prompt_template_formatting():
    prompt = RECON_PROMPT_TEMPLATE.format(
        company="ElevenLabs",
        company_url="https://elevenlabs.io",
        role_title="Full-Stack Engineer",
        job_description="Build real-time audio creative tools with WebAudio and Canvas."
    )
    assert "ElevenLabs" in prompt
    assert "Full-Stack Engineer" in prompt
    assert "revenue_engine" in prompt
    assert "manager_core_pressure" in prompt

@pytest.mark.anyio
async def test_recon_company_and_department_mocked():
    mock_gemini = MagicMock(spec=GeminiClient)
    mock_gemini.is_configured.return_value = True
    mock_response = {
        "company_name": "TestCorp",
        "business_model": {
            "revenue_engine": "B2B SaaS",
            "target_customers": "Enterprise Logistics",
            "value_proposition": "Real-time dispatch optimization",
            "macro_challenges": "Legacy database sync delays"
        },
        "company_stage": {
            "scale_and_momentum": "Series B, 200 employees",
            "funding_or_tier": "Growth / Series B-D",
            "market_standing": "Challenger"
        },
        "department_intel": {
            "team_name": "Dispatch Infrastructure",
            "team_charter": "Core Infrastructure",
            "role_archetype": "FIREFIGHTER",
            "hiring_manager_profile": "Director of Engineering",
            "manager_core_pressure": "Driver app disconnections during peak hours"
        },
        "strategic_positioning_for_candidate": {
            "tailor_summary_angle": "Highlight zero-data-loss pipeline experience",
            "cover_letter_hook_angle": "Open with high-concurrency dispatch latency"
        }
    }
    mock_gemini.generate_json = AsyncMock(return_value=mock_response)

    res = await recon_company_and_department(
        company="TestCorp",
        role_title="Senior Backend Engineer",
        job_description="Maintain dispatch pipelines and optimize latency.",
        company_url="https://testcorp.example",
        gemini_client=mock_gemini
    )

    assert res["company_name"] == "TestCorp"
    assert res["business_model"]["revenue_engine"] == "B2B SaaS"
    assert res["department_intel"]["role_archetype"] == "FIREFIGHTER"
    assert "researched_at" in res

def test_crud_update_company_recon():
    # Fetch a job or create a test job
    saved = crud.get_saved_jobs(limit=1)
    if not saved:
        pytest.skip("No saved jobs to test crud update")
    job_id = saved[0]["id"]

    sample_recon = {
        "company_name": saved[0]["company"],
        "business_model": {"revenue_engine": "Test Revenue Engine"}
    }
    updated = crud.update_job_company_recon(job_id, sample_recon)
    assert updated is not None
    assert updated["company_recon_json"] is not None
    loaded = json.loads(updated["company_recon_json"])
    assert loaded["company_name"] == saved[0]["company"]
