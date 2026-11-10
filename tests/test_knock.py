import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.knock import generate_outreach_for_contact
from app.ai.gemini import GeminiClient
from app import crud


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
    crud.create_application_for_job("test-job-knock-01")

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

    # Canned provider prose cannot demonstrate model style or length compliance.
    # Check provider inputs and the drafts actually persisted instead.
    prompt = mock_gemini.generate_json.call_args.kwargs["prompt"]
    assert "Synthetic candidate evidence for this isolated test." in prompt
    assert "Apex Audio Systems" in prompt
    assert "Audio Systems Analyst" in prompt
    assert "Alex Taylor" in prompt
    assert [(m["channel"], m["body"], m["subject"]) for m in msgs] == [
        (m["channel"], m["body"], m["subject"]) for m in mock_response["messages"]
    ]
    assert all(m["status"] == "draft" and m["contact_id"] == contact["id"] for m in msgs)
    saved_contact = next(
        c for c in crud.get_job_by_id("test-job-knock-01")["contacts"]
        if c["id"] == contact["id"]
    )
    assert {m["id"] for m in saved_contact["messages"]} == {m["id"] for m in msgs}

    # 5. Cleanup
    crud.delete_job("test-job-knock-01")
