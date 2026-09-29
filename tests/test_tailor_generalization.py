import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.tailor.engine import load_candidate_base_context, TAILOR_PROMPT_TEMPLATE, _job_posting_text, _match_analysis_context, _resume_skills_without_coursework_labels
from app.tailor.naming import get_candidate_display_name, generate_document_filename
from app.tailor.compiler import render_typst_template


@pytest.fixture
def synthetic_candidate_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "profile.yaml").write_text(
        """full_name: Alex Taylor
preferred_name: Alex
email: alex@example.com
phone: (555) 019-2834
location: Sample City
headline: Sample Analyst
work_authorization: Authorized
projects:
  - name: Route Study
    keywords: [routes]
    url: https://example.com/route-study
""",
        encoding="utf-8",
    )
    evidence_path = workspace / "master_resume" / "master_evidence.yaml"
    evidence_path.parent.mkdir()
    evidence_path.write_text(
        """schema_version: 1
headline: Sample Systems Analyst
experiences:
  - id: experience-1
    company: Apex Logistics
    role: Operations Analyst
    location: Sample City
    dates: 2024-2025
    bullets:
      - id: bullet-1
        category: reporting
        tags: [synthetic]
        metrics: [12% synthetic change]
        text: Built a synthetic reporting workflow.
projects: []
technical_skills:
  analytics_and_bi: [SQL]
education: []
certifications:
  primary: []
  secondary: []
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.tailor.engine.WORKSPACE_DIR", workspace)
    monkeypatch.setattr("app.evidence.DOORKNOCK_MASTER_EVIDENCE_YAML_PATH", evidence_path)
    return workspace


def test_load_candidate_base_context_uses_structured_evidence(synthetic_candidate_workspace):
    context = load_candidate_base_context()
    candidate = context["candidate"]
    candidate_evidence = context["candidate_evidence_context"]

    assert "name" in candidate
    assert "display_name" in candidate
    assert "email" in candidate
    assert "phone" in candidate
    assert isinstance(candidate.get("projects_meta"), list)
    assert "Apex Logistics" in candidate_evidence
    assert "bullet-1" in candidate_evidence


def test_tailor_requires_yaml_evidence(monkeypatch, synthetic_candidate_workspace):
    monkeypatch.setattr("app.evidence.get_candidate_master_context", lambda: "")
    with pytest.raises(ValueError, match="master_evidence.yaml"):
        load_candidate_base_context()


def test_tailor_prompt_uses_candidate_evidence():
    formatted = TAILOR_PROMPT_TEMPLATE.format(
        candidate_evidence="synthetic evidence marker",
        job_title="Test Analyst",
        company="Acme Corp",
        location="Remote",
        company_recon_summary="Not available.",
        match_analysis_context="Not available.",
        raw_job_text="Raw text",
    )
    assert "Acme Corp" in formatted
    assert "Test Analyst" in formatted
    assert "synthetic evidence marker" in formatted
    assert "<evidence>" in formatted


def test_saved_match_analysis_guides_selection_only_for_same_posting():
    import json

    analysis = {
        "raw_text": "Synthetic JD requires SQL and reporting.",
        "job_brief": "Reporting role",
        "technical_skills_required": ["SQL"],
        "gaps_and_mitigation": [{"gap": "Domain experience", "compensating_evidence": "Check verified evidence"}],
        "employer_mandate": {"immediate_value_hook": "Speculative internal claim"},
    }
    job = {"analysis_json": json.dumps(analysis)}
    context = _match_analysis_context(job, analysis["raw_text"])
    assert "SQL" in context
    assert "Domain experience" in context
    assert "Speculative internal claim" not in context
    with pytest.raises(ValueError, match="out of date"):
        _match_analysis_context(job, "Updated synthetic JD requires Python.")


def test_unbound_match_analysis_does_not_enter_prompt():
    assert "identity unknown" in _match_analysis_context({"analysis_json": '{"job_brief": "Old"}'}, "New JD")


def test_full_imported_posting_takes_precedence_over_brief():
    assert _job_posting_text({
        "job_description": "Full synthetic requirements and responsibilities",
        "job_brief": "Short summary",
    }) == "Full synthetic requirements and responsibilities"


def test_resume_skills_remove_coursework_labels_without_changing_source():
    skills = [{"category": "Tools", "items": "Excel, SQL (coursework), Power BI (Coursework)"}]
    cleaned = _resume_skills_without_coursework_labels(skills)
    assert cleaned == [{"category": "Tools", "items": "Excel, SQL, Power BI"}]
    assert skills[0]["items"] == "Excel, SQL (coursework), Power BI (Coursework)"


def test_cover_letter_does_not_repeat_generic_profile_headline():
    rendered = render_typst_template("cover_letter.typ.j2", {
        "candidate": {
            "name": "Alex Taylor", "headline": "Generic Profile Label",
            "location": "Sample City", "phone": "(555) 019-2834",
            "email": "alex@example.com", "linkedin": "example.com/alex",
            "github": "example.com/alex-code", "work_authorization": "Work authorized",
        },
        "letter": {
            "recipient_title": "Hiring Team", "company_name": "Apex Logistics",
            "company_location": "", "date": "September 24, 2026",
            "subject_role": "Systems Engineer", "salutation": "Hiring Team",
            "paragraphs": ["A specific, evidence-based opening."],
        },
    })
    assert "Generic Profile Label" not in rendered
    assert "Systems Engineer" in rendered


def test_naming_generator_defaults():
    assert get_candidate_display_name(None) == "Candidate"
    assert get_candidate_display_name("") == "Candidate"
    assert get_candidate_display_name("John Doe") == "John_Doe"

    fn = generate_document_filename("resume", "Acme Corp", candidate_name="Jane_Doe")
    assert fn == "Jane_Doe_Resume_Acme_Corp"
