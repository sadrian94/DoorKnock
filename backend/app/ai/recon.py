from ..clock import utc_now
from typing import Dict, Any, Optional
from .provider import AIClient, get_ai_client

RECON_SYSTEM_INSTRUCTION = """
You are the Chief Corporate Intelligence Officer and Senior Organizational Analyst for DoorKnock (敲門).
Your mission is to perform tactical reconnaissance on a target employer and deduce the specific operational context of the hiring department.

Guiding Principles:
1. Commercial Reality & Revenue Engine:
   - Identify how this business actually makes money (B2B subscription, API consumption, transaction cut, enterprise consulting, etc.).
   - Identify who the paying customer is and what macro friction or unit-economic pressures the company is experiencing right now.
2. Department Charter & Organizational Power:
   - Deduce where this role sits in the company's org chart (Frontline profit center, core infrastructure, internal cost center, or compliance defense).
   - Identify the hiring manager's core anxiety: What keeps them awake at night? What risk or bottleneck are they hiring this person to eliminate?
3. Strategic Positioning Angle:
   - Pinpoint the exact high-leverage technical/operational angle that will make a candidate stand out as an insider problem-solver rather than an external generic applicant.
   - Do NOT invent fictitious candidate experience; focus on how verified engineering/analytical fundamentals should be framed against this employer's frictions.
"""

RECON_PROMPT_TEMPLATE = """
Target Company: {company}
Company Website: {company_url}
Target Role Title: {role_title}

Target Job Description (Excerpt):
{job_description}

---------------------------
Analyze the target employer and the hiring team. Produce a structured JSON object matching this exact schema:
{{
  "company_name": "{company}",
  "business_model": {{
    "revenue_engine": "<How the company monetizes, e.g. 'B2B SaaS subscription + consumption billing' or 'Fixed-fee commercial construction contracts'>",
    "target_customers": "<Primary customer profile, e.g. 'Enterprise media studios and content creators' or 'Commercial real estate developers'>",
    "value_proposition": "<Core customer promise and defensible moat>",
    "macro_challenges": "<Current macro headwind, cost pressure, or operational bottleneck they are battling>"
  }},
  "company_stage": {{
    "scale_and_momentum": "<Estimated stage, headcount scale, or recent momentum>",
    "funding_or_tier": "<'Early-Stage' | 'Growth / Series B-D' | 'Unicorn' | 'Public Enterprise' | 'Established Private'>",
    "market_standing": "<'Category Leader' | 'Challenger' | 'Niche Specialist' | 'Legacy Incumbent'>"
  }},
  "department_intel": {{
    "team_name": "<Deduced functional department or pod name>",
    "team_charter": "<Mission of this team and whether it is a profit center, core infra, or support>",
    "role_archetype": "<'BUILDER' | 'FIREFIGHTER' | 'OPTIMIZER' | 'OPERATOR'>",
    "hiring_manager_profile": "<Deduced direct supervisor title, e.g. 'Engineering Manager / Director of Product Engineering'>",
    "manager_core_pressure": "<The direct supervisor's biggest quarter anxiety, operational friction, or delivery risk>"
  }},
  "strategic_positioning_for_candidate": {{
    "tailor_summary_angle": "<1-2 sentences on how resume summary should anchor itself to solve their specific department friction>",
    "cover_letter_hook_angle": "<1-2 sentences on the exact opening hook focusing on their real business/product problem>"
  }}
}}
"""

async def recon_company_and_department(
    company: str,
    role_title: str,
    job_description: str,
    company_url: Optional[str] = None,
    gemini_client: Optional[AIClient] = None,
) -> Dict[str, Any]:
    """Execute tactical reconnaissance on employer business model and department charter."""
    client = gemini_client or get_ai_client()

    prompt = RECON_PROMPT_TEMPLATE.format(
        company=company.strip() or "Target Employer",
        company_url=company_url or "Not provided",
        role_title=role_title.strip() or "Target Role",
        job_description=(job_description or "")[:10000]
    )

    result = await client.generate_json(prompt=prompt, system_instruction=RECON_SYSTEM_INSTRUCTION)
    result["researched_at"] = utc_now().isoformat()
    return result
