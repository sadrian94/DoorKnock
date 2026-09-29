import json
from typing import Dict, Any, List, Optional
from .provider import AIClient, get_ai_client
from .profile import get_candidate_profile_context
from .. import crud

KNOCK_SYSTEM_INSTRUCTION = """
You are the Chief Cold Outreach & Strategic Communication Officer for DoorKnock (敲門).
Your role is to craft authentic, razor-sharp, low-friction outreach messages for target gatekeepers.

Sepia De-AI Protocol & Guardrails:
1. STRICT BAN on AI Tell Words & Clichés:
   - FORBIDDEN: delve, foster, elevate, harness, empower, resonate, testament to, tapestry, multifaceted, seamless, vibrant, bespoke, pleased to, passionate about, I hope this message finds you well.
   - NO trailing participial phrases or rule-of-three platitudes.
2. Structure & Length Constraints:
   - For 'linkedin_connect': STRICTLY <= 300 characters (including spaces). Do not exceed 300 characters under any circumstance.
   - For 'inmail' / 'cold_email': STRICTLY 80 to 120 words. Problem-First opening -> 1-2 verified operational proof points -> low-friction 15-minute Micro-Ask.
3. Problem-First, Proof-Second:
   - Start directly with the employer's acute operational friction or product challenge.
   - Frame the candidate as an insider practitioner who has tackled and solved this exact problem.
   - Never beg for a job or referral; ask for a brief, peer-to-peer technical exchange or confirm qualifications.
"""

KNOCK_PROMPT_TEMPLATE = """
Candidate evidence loaded from the local YAML evidence bank:
<evidence>
{candidate_profile}
</evidence>

---------------------------
Target Employer & Role:
Company: {company}
Role Title: {role_title}

Company & Department Recon Intel:
{company_recon_summary}

Target Friction & Acute Bottlenecks:
{frictions_summary}

---------------------------
Target Gatekeeper to Contact:
Name: {contact_name}
Role Title: {contact_title}
Contact Type: {contact_type}

---------------------------
Generate exactly 2 outreach draft messages for this gatekeeper:
1. 'linkedin_connect': Short connection note (STRICTLY <= 300 characters).
2. 'linkedin_inmail' (or 'email'): Concise message (STRICTLY 80 to 120 words).

Return a structured JSON object matching this exact schema:
{{
  "messages": [
    {{
      "channel": "linkedin_connect",
      "archetype": "{default_archetype}",
      "subject": null,
      "body": "<LinkedIn connection note text strictly <= 300 characters>",
      "character_count": <character count integer>
    }},
    {{
      "channel": "linkedin_inmail",
      "archetype": "{default_archetype}",
      "subject": "<Concise, lower-case subject line under 7 words>",
      "body": "<80-120 word body text. Problem-first -> proof -> 15-min ask>",
      "word_count": <word count integer>
    }}
  ]
}}
"""

async def generate_outreach_for_contact(
    job_id: str,
    contact_id: str,
    gemini_client: Optional[AIClient] = None,
) -> List[Dict[str, Any]]:
    """Generate high-conversion, Sepia-compliant outreach messages for a target contact."""
    job = crud.get_job_by_id(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")

    # Find target contact
    target_contact = None
    for c in job.get("contacts", []):
        if c["id"] == contact_id:
            target_contact = c
            break

    if not target_contact:
        raise ValueError(f"Contact not found: {contact_id}")

    client = gemini_client or get_ai_client()
    candidate_profile = get_candidate_profile_context()

    # Summarize recon intel
    recon_json = job.get("company_recon_json")
    recon_summary = "No detailed recon available."
    if recon_json:
        try:
            recon_data = json.loads(recon_json) if isinstance(recon_json, str) else recon_json
            bm = recon_data.get("business_model", {})
            dept = recon_data.get("department_intel", {})
            recon_summary = (
                f"Revenue Engine: {bm.get('revenue_engine')}\n"
                f"Macro Challenges: {bm.get('macro_challenges')}\n"
                f"Department: {dept.get('team_name')} ({dept.get('team_charter')})\n"
                f"Manager Anxiety: {dept.get('manager_core_pressure')}"
            )
        except Exception:
            pass

    # Summarize analysis frictions
    analysis_json = job.get("analysis_json")
    frictions_summary = job.get("job_brief") or "General technical role requirements."
    if analysis_json:
        try:
            analysis_data = json.loads(analysis_json) if isinstance(analysis_json, str) else analysis_json
            mandate = analysis_data.get("employer_mandate", {})
            frictions = mandate.get("acute_operational_frictions", [])
            hook = mandate.get("immediate_value_hook", "")
            frictions_summary = f"Frictions: {'; '.join(frictions)}\nValue Hook: {hook}"
        except Exception:
            pass

    contact_type = target_contact.get("contact_type", "hiring_manager")
    archetype_map = {
        "hiring_manager": "pain_point_solution",
        "recruiter": "recruiter_qualification",
        "peer": "peer_coffee_chat",
        "alumni": "peer_coffee_chat",
        "other": "pain_point_solution"
    }
    default_archetype = archetype_map.get(contact_type, "pain_point_solution")

    prompt = KNOCK_PROMPT_TEMPLATE.format(
        candidate_profile=candidate_profile,
        company=job.get("company", "Target Employer"),
        role_title=job.get("title", "Target Position"),
        company_recon_summary=recon_summary,
        frictions_summary=frictions_summary,
        contact_name=target_contact.get("name", "Hiring Team"),
        contact_title=target_contact.get("role_title", "Leader"),
        contact_type=contact_type,
        default_archetype=default_archetype,
    )

    result = await client.generate_json(prompt=prompt, system_instruction=KNOCK_SYSTEM_INSTRUCTION)
    generated_msgs = result.get("messages", [])

    # Clean up prior un-sent drafts for this contact so we rewrite the DB cleanly
    crud.delete_draft_outreach_messages(contact_id=contact_id)

    created_records = []
    for msg in generated_msgs:
        body = msg.get("body", "").strip()
        if not body:
            continue
        channel = msg.get("channel", "linkedin_connect")
        subject = msg.get("subject")
        archetype = msg.get("archetype", default_archetype)

        rec = crud.add_outreach_message(
            contact_id=contact_id,
            channel=channel,
            archetype=archetype,
            body=body,
            subject=subject,
            status="draft",
        )
        created_records.append(rec)

    return created_records
