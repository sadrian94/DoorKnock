import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.recon import recon_company_and_department
from app.ai.gemini import GeminiClient


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

    prompt = mock_gemini.generate_json.call_args.kwargs["prompt"]
    assert "TestCorp" in prompt
    assert "Senior Backend Engineer" in prompt
    assert "Maintain dispatch pipelines and optimize latency." in prompt
    assert "https://testcorp.example" in prompt
    assert res["company_name"] == "TestCorp"
    assert res["business_model"]["revenue_engine"] == "B2B SaaS"
    assert res["department_intel"]["role_archetype"] == "FIREFIGHTER"
    assert "researched_at" in res
