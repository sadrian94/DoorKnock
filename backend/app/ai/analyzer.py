from typing import Dict, Any, Optional
from .provider import AIClient, get_ai_client
from .profile import get_candidate_profile_context

SYSTEM_INSTRUCTION = """
You are the Chief Talent Strategist and Senior Tactical Evaluation Officer for DoorKnock (敲門).
Your goal is to parse job postings and objectively evaluate candidate-job fit with high precision.

Guiding Principles:
1. Anti-Hallucination & Evidence-First: The candidate's background is strictly bounded by the supplied YAML evidence bank. NEVER invent skills, degrees, or experiences absent from it.
2. Decisive Triage & Friction First:
   - Identify hard dealbreakers immediately (e.g. mandatory security clearances, strict geographical non-remote mandates, non-sponsorship restrictions).
   - Uncover the acute operational friction and bottlenecks the team is hiring to solve (Problem-First, Proof-Second).
   - Evaluate whether candidate background directly solves this friction or has compensable adjacent proof.
3. Clean Boundary:
   - Output high-signal strategic brief: Triage decision, acute employer friction, value hook, and identified gaps with compensating defense.
   - Do NOT draft outreach messages or calculate resume layout blueprints here; those belong to downstream scout and tailor stages.
"""

ANALYSIS_PROMPT_TEMPLATE = """
Candidate evidence loaded from workspace/master_resume/master_evidence.yaml:
<evidence>
{candidate_profile}
</evidence>

---------------------------
Target Job Posting (Raw Text or Scraped Content):
{job_text}

---------------------------
Analyze the job posting and produce a structured JSON object matching this exact schema:
{{
  "title": "<Extracted Job Title>",
  "company": "<Extracted Company Name>",
  "company_url": "<Company website URL or null>",
  "location": "<City, State or Location description>",
  "workplace_type": "<'remote' | 'hybrid' | 'onsite'>",
  "salary_min": <Numeric minimum annual or hourly pay or null>,
  "salary_max": <Numeric maximum pay or null>,
  "salary_currency": "USD",
  "salary_interval": "<'year' | 'hour' | null>",
  "job_brief": "<2-3 sentence clear summary of the core role mission>",
  "technical_skills_required": ["<Skill 1>", "<Skill 2>", ...],
  "suitability_score": <Overall fit score 0 to 100 based on weighted technical, domain, and eligibility fit>,
  "suitability_reason": "<1-2 sentences concise justification of why this role matches or primary trade-off>",
  "triage": {{
    "decision": "<'STRONG_KNOCK' | 'SELECTIVE_APPLY' | 'HIGH_RISK_LOW_ROI' | 'HARD_PASS'>",
    "dealbreakers_detected": ["<Detected dealbreaker, e.g. 'Requires Active Secret Clearance', or 'None'>"],
    "strategic_thesis": "<1-2 sentences explaining the overarching tactical rationale for this decision>"
  }},
  "employer_mandate": {{
    "role_archetype": "<'BUILDER' | 'FIREFIGHTER' | 'OPTIMIZER' | 'OPERATOR'>",
    "acute_operational_frictions": [
      "<Acute friction point 1 that the team is suffering from and hiring to solve>",
      "<Acute friction point 2>"
    ],
    "immediate_value_hook": "<1-2 sentences on how candidate solves their primary friction from Day 1>"
  }},
  "gaps_and_mitigation": [
    {{
      "gap": "<Specific tool, credential, or domain depth requested in JD that candidate lacks>",
      "severity": "<'CRITICAL' | 'MODERATE' | 'LOW'>",
      "compensating_evidence": "<How candidate's verified background offsets or neutralizes this gap>"
    }}
  ]
}}
"""

async def analyze_job_posting(raw_text: str, source_url: Optional[str] = None, gemini_client: Optional[AIClient] = None) -> Dict[str, Any]:
    """Extract job metadata and perform candidate fit analysis."""
    client = gemini_client or get_ai_client()
    candidate_profile = get_candidate_profile_context()

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        candidate_profile=candidate_profile,
        job_text=raw_text[:12000] # Cap text length for speed and reliability
    )

    result = await client.generate_json(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)
    if source_url and not result.get("company_url"):
        result["source_url"] = source_url

    # Backward compatibility mappings for existing downstream components
    mandate = result.get("employer_mandate", {})
    if "acute_operational_frictions" in mandate and not result.get("employer_pain_points"):
        result["employer_pain_points"] = mandate["acute_operational_frictions"]

    gaps = result.get("gaps_and_mitigation", [])
    if gaps and not result.get("gaps_or_risks"):
        result["gaps_or_risks"] = [g.get("gap") for g in gaps if g.get("gap")]

    if not result.get("suitability_reason") and "triage" in result:
        result["suitability_reason"] = result["triage"].get("strategic_thesis", "")

    # Ensure raw JD is retained
    result["raw_text"] = raw_text
    return result
