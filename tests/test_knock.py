import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.knock import generate_outreach_for_contact, KNOCK_PROMPT_TEMPLATE
from app.ai.gemini import GeminiClient
from app import crud

FORBIDDEN_WORDS = [
    "delve", "foster", "elevate", "harness", "empower", "resonate",
    "testament to", "tapestry", "multifaceted", "seamless", "vibrant",
    "I hope this message finds you well"
]

def test_knock_prompt_template_formatting():
    prompt = KNOCK_PROMPT_TEMPLATE.format(
        candidate_profile="Candidate Profile Sample",
        company="Apex Audio Systems",
        role_title="Full-Stack Engineer",
        company_recon_summary="Revenue Engine: B2B SaaS",
        frictions_summary="Frictions: WebAudio memory leaks",
        contact_name="Alex Taylor",
        contact_title="Head of Engineering",
        contact_type="hiring_manager",
        default_archetype="pain_point_solution",
    )
    assert "Alex Taylor" in prompt
    assert "Apex Audio Systems" in prompt
    assert "linkedin_connect" in prompt
    assert "<= 300 characters" in prompt

@pytest.mark.anyio
async def test_generate_outreach_for_contact_mocked(monkeypatch):
    monkeypatch.setattr(
        "app.ai.knock.get_candidate_profile_context",
        lambda: "Synthetic candidate evidence for this isolated test.",
    )
    # 1. Create temporary job
    with crud.get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO jobs (id, title, company, job_description, status)
            VALUES (?, ?, ?, ?, ?)
        """, ("test-job-knock-01", "Audio Systems Analyst", "Apex Audio Systems", "Build sample audio web editors.", "saved"))
        conn.commit()
    import_res = crud.create_application_for_job("test-job-knock-01")

    # 2. Add contact
    contact = crud.add_contact(
        job_id="test-job-knock-01",
        name="Alex Taylor",
        role_title="Head of Product Eng",
        contact_type="hiring_manager"
    )

    # 3. Setup mock gemini client
    mock_gemini = MagicMock(spec=GeminiClient)
    mock_gemini.is_configured.return_value = True

    connect_body = "Hi Alex, saw Apex Audio Systems' studio expansion. I work on synthetic timeline rendering and source validation. Would a short technical exchange help?"
    inmail_body = (
        "Subject: Studio audio timeline & rendering\n\n"
        "Hi Alex,\n\n"
        "I saw the audio systems opening. As multi-track timelines move to web editors, frame drops and audio memory leaks can become a bottleneck before teams support larger projects.\n\n"
        "In a synthetic portfolio project, I checked timeline rendering behavior and documented data validation issues. That gave me a concrete way to discuss the trade-offs without assuming your team's implementation.\n\n"
        "If your team is tackling these rendering and streaming trade-offs this quarter, I'd welcome a brief 15-minute conversation to share notes.\n\n"
        "Best,\nCandidate"
    )

    mock_response = {
        "messages": [
            {
                "channel": "linkedin_connect",
                "archetype": "pain_point_solution",
                "subject": None,
                "body": connect_body,
                "character_count": len(connect_body)
            },
            {
                "channel": "linkedin_inmail",
                "archetype": "pain_point_solution",
                "subject": "Studio audio timeline & rendering latency",
                "body": inmail_body,
                "word_count": len(inmail_body.split())
            }
        ]
    }
    mock_gemini.generate_json = AsyncMock(return_value=mock_response)

    # 4. Generate outreach
    msgs = await generate_outreach_for_contact(
        job_id="test-job-knock-01",
        contact_id=contact["id"],
        gemini_client=mock_gemini
    )

    assert len(msgs) == 2
    connect_msg = next(m for m in msgs if m["channel"] == "linkedin_connect")
    assert len(connect_msg["body"]) <= 300

    inmail_msg = next(m for m in msgs if m["channel"] == "linkedin_inmail")
    assert 50 <= len(inmail_msg["body"].split()) <= 150

    # Ensure no forbidden AI tell words
    for m in msgs:
        for forbidden in FORBIDDEN_WORDS:
            assert forbidden.lower() not in m["body"].lower()

    # 5. Cleanup
    crud.delete_job("test-job-knock-01")
