import json
import hashlib
import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from ..config import (
    WORKSPACE_DIR,
    APPLICATIONS_DIR,
)
from ..ai.provider import AIClient, get_ai_client
from .compiler import compile_document
from .settings import get_resume_settings
from .validation import validate_resume_evidence
from .naming import (
    sanitize_slug,
    generate_document_filename,
    generate_application_workspace_dirname,
    get_candidate_display_name,
)

logger = logging.getLogger("doorknock.tailor.engine")


def _resume_skills_without_coursework_labels(skills):
    """Keep supported skill names while leaving provenance in the evidence record."""
    cleaned = []
    for skill in skills:
        entry = dict(skill)
        field = "items" if "items" in entry else "skills"
        value = entry.get(field)
        if isinstance(value, str):
            entry[field] = re.sub(r"\s*\(coursework\)", "", value, flags=re.IGNORECASE)
        cleaned.append(entry)
    return cleaned

def _application_key(job_data: Dict[str, Any]) -> str:
    if job_data.get("id"):
        return str(job_data["id"])
    source = "\0".join(str(job_data.get(key, "")) for key in ("company", "title", "raw_text"))
    return "jd:" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]

def _application_dir(job_data: Dict[str, Any], company: str, title: str, date_stamp: str) -> Path:
    key = _application_key(job_data)
    if APPLICATIONS_DIR.is_dir():
        matching = []
        for directory in APPLICATIONS_DIR.iterdir():
            metadata_path = directory / "workspace-metadata.json"
            if not directory.is_dir() or not metadata_path.is_file():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if metadata.get("application_key") == key or (job_data.get("id") and metadata.get("job_id") == job_data["id"]):
                matching.append(directory)
        if matching:
            return max(matching, key=lambda directory: directory.stat().st_mtime)
    directory_name = generate_application_workspace_dirname(company, title, date_str=date_stamp)
    return APPLICATIONS_DIR / f"{directory_name}-{sanitize_slug(key, max_len=16)}"

def _next_version_number(app_dir: Path, doc_type: str) -> int:
    from ..documents import scan_document_versions
    highest = 0
    for entry in scan_document_versions(app_dir, doc_type)["versions"]:
        match = re.fullmatch(r"v(\d+)", entry["version"])
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1

def _job_posting_text(job_data: Dict[str, Any]) -> str:
    """Use the full stored posting before short import summaries."""
    return (job_data.get("raw_text") or job_data.get("job_description")
            or job_data.get("description") or job_data.get("job_brief") or "")


def _match_analysis_context(job_data: Dict[str, Any], posting: str) -> str:
    """Use saved analysis only when it describes the current posting."""
    raw = job_data.get("analysis_json")
    if not raw:
        return "Not available. Select evidence directly from the posting."
    try:
        analysis = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return "Unavailable (invalid saved analysis). Select evidence directly from the posting."
    if not isinstance(analysis, dict):
        return "Unavailable (invalid saved analysis). Select evidence directly from the posting."
    analyzed_posting = analysis.get("raw_text")
    if not isinstance(analyzed_posting, str) or not analyzed_posting.strip():
        return "Unavailable (posting identity unknown). Select evidence directly from the posting."
    if analyzed_posting.strip() != posting.strip():
        raise ValueError("Saved match analysis is out of date for this job posting. Re-run Match Analysis before generating documents.")
    relevant = {
        "job_brief": analysis.get("job_brief"),
        "technical_skills_required": analysis.get("technical_skills_required"),
        "gaps_and_mitigation": analysis.get("gaps_and_mitigation"),
    }
    return json.dumps({key: value for key, value in relevant.items() if value}, ensure_ascii=False)

def load_candidate_base_context() -> Dict[str, Any]:
    """Load candidate profile details and evidence context from workspace YAML files."""
    profile_path = WORKSPACE_DIR / "profile.yaml"
    data: Dict[str, Any] = {}
    if profile_path.exists():
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Error parsing profile.yaml: {e}")

    full_name = data.get("full_name", "").strip() or "Candidate"
    pref_name = data.get("preferred_name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    location = data.get("location", "").strip()
    headline = data.get("headline", "").strip() or "Professional"
    work_auth = data.get("work_authorization", "").strip() or "Authorized to work in the U.S."

    # Format URLs for clean resume display (strip https:// and trailing slashes)
    linkedin = data.get("linkedin_url", "").strip()
    linkedin = re.sub(r'^https?://(www\.)?', '', linkedin).rstrip('/')
    github = data.get("github_url", "").strip()
    github = re.sub(r'^https?://(www\.)?', '', github).rstrip('/')

    projects_meta = data.get("projects", [])

    from ..evidence import get_candidate_master_context
    candidate_evidence_context = get_candidate_master_context()
    if not candidate_evidence_context:
        raise ValueError("Candidate master evidence is missing or invalid: workspace/master_resume/master_evidence.yaml")


    display_name = get_candidate_display_name(pref_name or full_name)

    return {
        "candidate": {
            "name": f"{full_name} ({pref_name.split()[0]})" if pref_name and pref_name != full_name else full_name,
            "display_name": display_name,
            "headline": headline,
            "location": location,
            "phone": phone,
            "email": email,
            "linkedin": linkedin,
            "github": github,
            "work_authorization": work_auth,
            "projects_meta": projects_meta,
        },
        "candidate_evidence_context": candidate_evidence_context,
    }

SYSTEM_PROMPT = """
Candidate facts come only from the supplied evidence. Preserve verified employers, titles, dates, degrees, certifications, tools, and metrics. The posting describes employer needs, not candidate experience. Treat recon as uncertain context, never as a candidate fact or a known internal problem. Use job terms only when the evidence supports them. Write confidently about work the candidate actually performed, without inflating ownership, domain, or results. Avoid vague corporate language and unsupported business effects. Return JSON only; use empty values for unsupported optional content.
"""

TAILOR_PROMPT_TEMPLATE = """
Candidate evidence:
<evidence>
{candidate_evidence}
</evidence>

Job: {job_title} at {company}
Location: {location}
Posting:
<posting>
{raw_job_text}
</posting>
Saved match analysis (selection guide only; verify every requirement against the posting and every candidate claim against evidence):
<match_analysis>
{match_analysis_context}
</match_analysis>
Company context (may contain inference):
<recon>
{company_recon_summary}
</recon>
"""


async def _generate_part(client: AIClient, context: str, instruction: str,
                         required_fields: tuple[str, ...]) -> Dict[str, Any]:
    result = await client.generate_json(prompt=f"{context}\n\nTask:\n{instruction}", system_instruction=SYSTEM_PROMPT)
    if not isinstance(result, dict):
        raise ValueError("Tailor generation returned a non-object JSON value")
    missing = [field for field in required_fields if field not in result]
    if missing:
        raise ValueError(f"Tailor generation missing fields: {', '.join(missing)}")
    return result

async def tailor_application_documents(
    job_data: Dict[str, Any],
    document_type: str = "resume",
    custom_output_dir: Optional[Path] = None,
    gemini_client: Optional[AIClient] = None,
    authored_documents: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate and publish one independently versioned document.
    """
    if document_type not in ("resume", "cover_letter"):
        raise ValueError("document_type must be resume or cover_letter")
    resume_preferences = get_resume_settings()
    require_single_page = resume_preferences["require_single_page"] if document_type == "resume" else True
    base_info = load_candidate_base_context()
    candidate = base_info["candidate"]
    candidate_evidence = base_info["candidate_evidence_context"]

    company = job_data.get("company", "Company").strip()
    title = job_data.get("title", "Job").strip()
    location = job_data.get("location", "Remote/Hybrid").strip()
    raw_text = _job_posting_text(job_data)
    match_analysis_context = _match_analysis_context(job_data, raw_text) if authored_documents is None else ""

    now_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    today_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Determine target workspace directory
    if custom_output_dir:
        app_dir = custom_output_dir
    else:
        app_dir = _application_dir(job_data, company, title, today_stamp)
    app_dir.mkdir(parents=True, exist_ok=True)

    recon_json = job_data.get("company_recon_json") or job_data.get("company_recon")
    recon_summary = "Not available."
    if recon_json:
        try:
            recon_dict = json.loads(recon_json) if isinstance(recon_json, str) else recon_json
            bm = recon_dict.get("business_model", {})
            dept = recon_dict.get("department_intel", {})
            strat = recon_dict.get("strategic_positioning_for_candidate", {})
            recon_summary = (
                f"Revenue Engine: {bm.get('revenue_engine', '')}; "
                f"Target Customers: {bm.get('target_customers', '')}; "
                f"Department: {dept.get('team_name', '')} ({dept.get('team_charter', '')}); "
                f"Role Archetype: {dept.get('role_archetype', '')}; "
                f"Manager Anxiety: {dept.get('manager_core_pressure', '')}; "
                f"Resume Summary Angle: {strat.get('tailor_summary_angle', '')}; "
                f"Cover Letter Hook Angle: {strat.get('cover_letter_hook_angle', '')}"
            )
        except Exception:
            pass

    strategy = None
    resume_payload = None
    letter_payload = None
    if authored_documents is not None:
        if not isinstance(authored_documents, dict):
            raise ValueError("Agent-authored document package must be a JSON object")
        strategy = authored_documents.get("tailor_strategy")
        resume_payload = authored_documents.get("resume")
        letter_payload = authored_documents.get("cover_letter")
        if document_type == "resume":
            if not isinstance(strategy, dict) or not isinstance(resume_payload, dict):
                raise ValueError("Agent-authored resume requires tailor_strategy and resume objects")
            required_resume = ("summary", "experiences", "projects", "skills", "education", "certifications")
            if any(field not in resume_payload for field in required_resume):
                raise ValueError("Agent-authored resume is missing required fields")
            if not isinstance(resume_payload["summary"], str) or not resume_payload["summary"].strip():
                raise ValueError("Agent-authored resume summary must be nonempty")
        else:
            if not isinstance(letter_payload, dict) or not isinstance(letter_payload.get("paragraphs"), list) or not letter_payload["paragraphs"]:
                raise ValueError("Agent-authored cover letter needs paragraphs")
    else:
        # Agent-authored packages bypass provider generation.
        client = gemini_client or get_ai_client()
        context = TAILOR_PROMPT_TEMPLATE.format(
            candidate_evidence=candidate_evidence,
            job_title=title,
            company=company,
            location=location,
            company_recon_summary=recon_summary,
            match_analysis_context=match_analysis_context,
            raw_job_text=raw_text[:10000],
        )

        page_guidance = (
            "Keep the resume to one page."
            if require_single_page
            else "Do not omit relevant verified evidence solely to fit one page; two pages are acceptable when the content needs the space."
        )
        resume_sections_instruction = (
            "Write only the resume Experience and Projects sections. "
            + page_guidance
            + ' Select the strongest relevant evidence and preserve exact employers, titles and dates. Each bullet should name a concrete action and its object, then the useful method, scale, check, or verified result. Use direct verbs for work the candidate performed; use a supporting verb only when the evidence shows a supporting role. Keep the original work domain visible. Do not add inferred outcomes such as prevented losses or improved decisions unless the evidence supports them. Give useful projects enough detail to show method, checks and result. Avoid invented metrics, vague corporate phrases, keyword stuffing and fixed bullet counts. Return {"experiences": [{"company": "", "location": "", "title": "", "dates": "", "bullets": [""]}], "projects": [{"name": "", "tech_stack": "", "bullets": [""]}]}. Use empty arrays when unsupported; never include blank example entries.'
        )

        if document_type == "resume":
            strategy = await _generate_part(client, context,
        'Select the strongest evidence-based fit for this role. Return {"target_role_header": "<concise role heading, not an employment claim>", "primary_angle": "<one-sentence evidence-based fit>"}.', ("target_role_header", "primary_angle"))
            body = await _generate_part(client, context + "\nSelected positioning:\n" + json.dumps(strategy, ensure_ascii=False),
        resume_sections_instruction, ("experiences", "projects"))
            credentials = await _generate_part(client, context + "\nSelected resume content:\n" + json.dumps(body, ensure_ascii=False),
        'Write only resume Skills, Education and Certifications. Include supported, role-relevant skill names without parenthetical provenance labels such as (coursework); retain the evidence boundary and do not imply paid use of a skill supported only by study. Preserve exact degree and certification facts. Avoid repeating a tool in several categories. Return {"skills": [{"category": "", "items": "<comma-separated supported skills>"}], "education": [{"institution": "", "degree": "", "year": "", "location": "", "focus": ""}], "certifications": ""}. Use empty values when unsupported.', ("skills", "education", "certifications"))
            resume_payload = {**body, **credentials}
            summary = await _generate_part(client, context + "\nSelected resume:\n" + json.dumps(resume_payload, ensure_ascii=False),
        'Write only the resume Summary for a human reader: a brief, natural overview of relevant work the candidate has done and one or two strengths that match the role. Lead with concrete work rather than a target-title label, aspiration, or list of abstract capabilities. Mention a career transition only if it clarifies the fit, and only once. Base every phrase on candidate evidence and the selected resume; do not imply the candidate already holds the target title. Do not repeat bullet metrics, claim inferred business effects, or list keywords. Return {"summary": "<brief specific summary>"}.', ("summary",))
            resume_payload["summary"] = summary.get("summary", "")
        else:
            cover_letter_prompt = (
                "Write an authentic, highly compelling single-page cover letter in 3-4 concise paragraphs following the Sepia professional standard.\n"
                "Architecture:\n"
                "1. Hook: Start from the employer's acute operational reality, technical friction, or domain challenge (draw from company recon and posting). Do not open with 'I am writing to apply...' or generic introductions. State the candidate's core operating ethos.\n"
                "2. Grounded Proof / War Story: Highlight a concrete technical accomplishment from candidate evidence showing how the candidate structured work, enforced constraints/contracts, tested rigorously, or recovered from failures. Show actual methods and boundaries, not bare buzzwords.\n"
                "3. Domain & Operational Context: Connect the candidate's verified background to the company's real business risk and operational environment (e.g. data integrity, transaction risk, system reliability).\n"
                "4. Conviction & Boundaries: Confident close emphasizing disciplined verification, respecting review/rollback procedures, and readiness to take ownership under technical guidance.\n"
                "Negative Constraints (Sepia De-AI):\n"
                "- Never parrot the job posting verbatim or echo requirements back as hollow claims.\n"
                "- Ban generative boilerplate: 'directly aligns with', 'testament to', 'I welcome the opportunity to discuss', 'Holding a degree...', 'foster', 'elevate', 'harness', 'seamless', 'delve'.\n"
                "- Keep syntax active, direct, and speech-shaped. Never invent unverified candidate facts or metrics.\n"
                'Return {"paragraphs": ["<p1>", "<p2>", "<p3>", "<p4>"], "recipient_title": "<targeted title e.g. Engineering Hiring Team>", "salutation": "<clean name without Dear, e.g. TRG Engineering Team>"}.'
            )
            letter_payload = await _generate_part(client, context, cover_letter_prompt, ("paragraphs",))

    # Step 2: Prepare Contexts
    target_role_header = (strategy or {}).get("target_role_header") or title.upper()

    projects = (resume_payload or {}).get("projects", [])
    projects_meta = candidate.get("projects_meta", [])
    for p in projects:
        p_name = p.get("name", "").lower()
        if not p.get("url") and projects_meta:
            for pm in projects_meta:
                pm_name = pm.get("name", "").lower()
                pm_keywords = [k.lower() for k in pm.get("keywords", []) if k]
                if pm_name and pm_name in p_name:
                    p["url"] = pm.get("url")
                    break
                if any(k in p_name for k in pm_keywords):
                    p["url"] = pm.get("url")
                    break

    education = (resume_payload or {}).get("education", [])

    resume_context = {
        "candidate": candidate,
        "resume": {
            "target_role": target_role_header,
            "summary": (resume_payload or {}).get("summary", ""),
            "experiences": (resume_payload or {}).get("experiences", []),
            "projects": projects,
            "skills": _resume_skills_without_coursework_labels((resume_payload or {}).get("skills", [])),
            "education": education,
            "certifications": (resume_payload or {}).get("certifications", ""),
        },
    }

    letter_context = {
        "candidate": candidate,
        "letter": {
            "recipient_title": (letter_payload or {}).get("recipient_title", "Hiring Team"),
            "company_name": (letter_payload or {}).get("company_name", company),
            "company_location": (letter_payload or {}).get("company_location", location),
            "date": (letter_payload or {}).get("date", now_date),
            "subject_role": (letter_payload or {}).get("subject_role", title),
            "salutation": re.sub(r"^Dear\s+", "", str((letter_payload or {}).get("salutation") or f"{company} Hiring Team").strip(), flags=re.IGNORECASE).rstrip(",").strip(),
            "paragraphs": (letter_payload or {}).get("paragraphs", []),
        },
    }

    if document_type == "resume":
        validate_resume_evidence(resume_payload, candidate_evidence)

    # Compile only the requested document; publish after its PDF passes QA.
    stage_dir = app_dir / f".tailor-staging-{uuid.uuid4().hex}"
    stage_dir.mkdir()
    try:
        folder = "resume" if document_type == "resume" else "cover-letter"
        template = "resume.typ.j2" if document_type == "resume" else "cover_letter.typ.j2"
        context = resume_context if document_type == "resume" else letter_context
        base_name = generate_document_filename(document_type, company, candidate_name=candidate["display_name"])
        compiled = compile_document(
            template, context, stage_dir, base_name,
            require_single_page=require_single_page,
        )
        if not compiled.get("success"):
            return {"success": False, "application_dir": str(app_dir), "document_type": document_type,
                    "pdf": None, "manifest": None, "compilation": compiled}

        versions_dir = app_dir / folder
        versions_dir.mkdir(exist_ok=True)
        version_number = _next_version_number(app_dir, document_type)
        while True:
            version = f"v{version_number:03d}"
            target_dir = versions_dir / version
            if target_dir.exists():
                version_number += 1
                continue
            try:
                stage_dir.rename(target_dir)
                break
            except FileExistsError:
                version_number += 1

        pdf = target_dir / f"{base_name}.pdf"
        typ = target_dir / f"{base_name}.typ"
        manifest = {
            "application_key": _application_key(job_data),
            "job_id": job_data.get("id"),
            "company": company,
            "title": title,
            "document_type": document_type,
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pdf": str(pdf),
            "typ": str(typ),
            "single_page": compiled.get("is_single_page", False),
            "page_limit_required": require_single_page if document_type == "resume" else True,
            "success": True,
            "page_count": compiled.get("page_count"),
            "text_chars": compiled.get("text_chars"),
        }
        if document_type == "resume":
            manifest["tailor_strategy"] = strategy
        version_manifest = target_dir / "workspace-metadata.json"
        version_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        latest_path = app_dir / "workspace-metadata.json"
        if latest_path.is_file():
            try:
                latest = json.loads(latest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                latest = {}
        else:
            latest = {}
        documents = latest.get("documents")
        if not isinstance(documents, dict):
            documents = {}
        legacy_version = latest.get("version")
        if isinstance(legacy_version, str) and re.fullmatch(r"v\d+", legacy_version):
            for legacy_type in ("resume", "cover_letter"):
                if isinstance(latest.get(legacy_type), dict) and legacy_type not in documents:
                    documents[legacy_type] = {
                        "version": legacy_version,
                        "manifest": str(app_dir / "versions" / legacy_version / "workspace-metadata.json"),
                    }
        for old_key in ("version", "created_at", "tailor_strategy", "resume", "cover_letter"):
            latest.pop(old_key, None)
        latest.update({key: manifest[key] for key in ("application_key", "job_id", "company", "title")})
        documents[document_type] = {"version": version, "manifest": str(version_manifest)}
        latest["documents"] = documents
        latest_temp = app_dir / f".workspace-metadata-{uuid.uuid4().hex}.json"
        latest_temp.write_text(json.dumps(latest, indent=2, ensure_ascii=False), encoding="utf-8")
        latest_temp.replace(latest_path)
        return {"success": True, "application_dir": str(app_dir), "document_type": document_type,
                "pdf": str(pdf), "manifest": manifest}
    finally:
        if stage_dir.exists():
            # This path was created in this call and must stay inside the selected application directory.
            stage_dir.resolve().relative_to(app_dir.resolve())
            shutil.rmtree(stage_dir)
