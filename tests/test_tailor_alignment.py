"""Synthetic alignment cases: keyword placement must not strengthen claims."""
import json
from pathlib import Path

import pytest

from app.tailor import engine


EVIDENCE = """experiences:
  - id: exp-operations
    company: Sample Distribution
    role: Operations Analyst
    dates: 2024-2025
    location: Sample City
    bullets:
      - id: payment-checks
        text: Investigated payment discrepancies by tracing transaction records.
projects: []
education: []
technical_skills:
  analytics: [Excel, SQL (coursework)]
"""
POSTING = "Investigate discrepancies and improve data quality. Product catalog and ERP experience preferred."


def package():
    return {
        "tailor_strategy": {"target_role_header": "ANALYST", "primary_angle": "Record investigation"},
        "resume": {"summary": "Investigated transaction discrepancies.",
                   "experiences": [], "projects": [], "skills": [],
                   "education": [], "certifications": ""},
        "keyword_alignment": [{
            "keyword": "discrepancies", "requirement": "Investigate discrepancies",
            "support": "direct", "evidence_ids": ["payment-checks"],
            "placements": ["summary", "experiences"],
            "boundary": "Transaction records, not product catalogs or ERP administration.",
        }, {
            "keyword": "data quality", "requirement": "improve data quality",
            "support": "transferable", "evidence_ids": ["payment-checks"],
            "placements": ["experiences"], "boundary": "Operational payment records only.",
        }, {
            "keyword": "ERP", "requirement": "ERP experience preferred",
            "support": "unsupported", "evidence_ids": [], "placements": [],
            "boundary": "No verified ERP experience.",
        }],
        "claim_review": {"status": "ready", "findings": []},
    }


@pytest.fixture
def candidate(monkeypatch):
    monkeypatch.setattr(engine, "load_candidate_base_context", lambda: {
        "candidate": {"name": "Alex Taylor", "display_name": "Alex_Taylor", "location": "Sample City",
                      "email": "alex@example.com", "phone": "555-0100", "linkedin": "", "github": "",
                      "work_authorization": "Authorized", "projects_meta": []},
        "candidate_evidence_context": EVIDENCE,
    })
    # PDF compilation has its own real-PDF tests; exercise publication here.
    def compile_fixture(_template, _context, output_dir, base_filename, **_kwargs):
        (output_dir / f"{base_filename}.pdf").write_bytes(b"synthetic pdf")
        (output_dir / f"{base_filename}.typ").write_text("synthetic document", encoding="utf-8")
        return {"success": True, "page_count": 1, "text_chars": 200}
    monkeypatch.setattr(engine, "compile_document", compile_fixture)


async def publish(tmp_path, document, **kwargs):
    return await engine.tailor_application_documents(
        {"id": "synthetic-alignment", "company": "Sample Employer", "title": "Analyst", "raw_text": POSTING},
        custom_output_dir=tmp_path, authored_documents=document, **kwargs,
    )


@pytest.mark.anyio
async def test_version_saves_coverage_and_distinguishes_missing_from_unsupported(tmp_path, candidate):
    result = await publish(tmp_path, package())
    assert result["success"]
    report_path = tmp_path / "resume" / "v001" / "keyword-review.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["coverage"][0]["status"] == "covered"
    assert report["coverage"][0]["found_in"] == ["summary"]
    assert report["coverage"][0]["missing_placements"] == ["experiences"]
    assert report["coverage"][1]["status"] == "could_improve"
    assert report["coverage"][2]["status"] == "evidence_gap"
    assert report["claim_review"]["status"] == "ready"
    assert result["manifest"]["keyword_review"] == str(report_path)


@pytest.mark.anyio
@pytest.mark.parametrize("problem", ["unknown_id", "not_in_posting", "unsupported_placement", "missing_review"])
async def test_invalid_mapping_never_publishes(tmp_path, candidate, problem):
    data = package()
    if problem == "unknown_id":
        data["keyword_alignment"][0]["evidence_ids"] = ["invented-id"]
    elif problem == "not_in_posting":
        data["keyword_alignment"][0]["requirement"] = "Lead enterprise governance"
    elif problem == "unsupported_placement":
        data["keyword_alignment"][2]["placements"] = ["skills"]
    else:
        del data["claim_review"]
    with pytest.raises(ValueError):
        await publish(tmp_path, data)
    assert not (tmp_path / "resume" / "v001").exists()


@pytest.mark.anyio
async def test_claim_escalation_blocks_new_version_and_preserves_previous(tmp_path, candidate):
    first = await publish(tmp_path, package())
    previous = (tmp_path / "workspace-metadata.json").read_bytes()
    data = package()
    data["resume"]["summary"] = "Managed enterprise product catalog governance."
    data["claim_review"] = {"status": "needs_revision", "findings": [{
        "section": "summary", "quote": "Managed enterprise product catalog governance.",
        "issue": "Payment reconciliation does not establish product catalog ownership.",
        "suggestion": "Describe transaction discrepancy investigation.",
    }]}
    result = await publish(tmp_path, data)
    assert not result["success"]
    assert result["keyword_review"]["claim_review"]["status"] == "needs_revision"
    assert not (tmp_path / "resume" / "v002").exists()
    assert (tmp_path / "workspace-metadata.json").read_bytes() == previous
    assert first["success"]


@pytest.mark.anyio
async def test_legacy_package_explicitly_requires_manual_review(tmp_path, candidate):
    data = package()
    del data["keyword_alignment"], data["claim_review"]
    result = await publish(tmp_path, data)
    assert result["success"]
    assert result["manifest"]["alignment_status"] == "not_reviewed"


@pytest.mark.anyio
async def test_letter_checks_paragraphs_without_regenerating_resume(tmp_path, candidate):
    data = package()
    del data["resume"], data["tailor_strategy"]
    data["cover_letter"] = {"paragraphs": ["I investigated transaction discrepancies and reported findings."]}
    for row in data["keyword_alignment"]:
        if row["support"] != "unsupported":
            row["placements"] = ["paragraphs"]
    result = await publish(tmp_path, data, document_type="cover_letter")
    assert result["success"]
    report = json.loads((tmp_path / "cover-letter" / "v001" / "keyword-review.json").read_text(encoding="utf-8"))
    assert report["coverage"][0]["found_in"] == ["paragraphs"]
    assert not (tmp_path / "resume").exists()


@pytest.mark.anyio
@pytest.mark.parametrize("document_type", ["resume", "cover_letter"])
async def test_provider_plan_reaches_drafting_and_review(tmp_path, candidate, document_type):
    class Client:
        def __init__(self):
            self.calls = []

        async def generate_json(self, **kwargs):
            prompt = kwargs["prompt"]
            self.calls.append(prompt)
            data = package()
            rows = data["keyword_alignment"]
            if document_type == "cover_letter":
                for row in rows:
                    if row["support"] != "unsupported":
                        row["placements"] = ["paragraphs"]
            if "Review the completed document" in prompt:
                assert "Completed document:" in prompt and "Transaction records, not product catalogs" in prompt
                return {"claim_review": data["claim_review"]}
            if "Build keyword_alignment" in prompt:
                return {**data["tailor_strategy"], "keyword_alignment": rows}
            assert "Keyword alignment plan:" in prompt
            if "Write only the resume Experience" in prompt:
                return {"experiences": [], "projects": []}
            if "Write only resume Skills" in prompt:
                return {"skills": [], "education": [], "certifications": ""}
            if "Write only the resume Summary" in prompt:
                return {"summary": data["resume"]["summary"]}
            return {"paragraphs": ["Investigated transaction discrepancies."]}

    client = Client()
    result = await engine.tailor_application_documents(
        {"company": "Sample Employer", "title": "Analyst", "raw_text": POSTING},
        custom_output_dir=tmp_path, gemini_client=client, document_type=document_type,
    )
    assert result["success"]
    report = json.loads(Path(result["manifest"]["keyword_review"]).read_text(encoding="utf-8"))
    assert report["review_source"] == "provider"
    assert report["keyword_alignment"][2]["support"] == "unsupported"
    assert len(client.calls) == (5 if document_type == "resume" else 3)


def test_skill_refs_and_literal_coverage_do_not_confuse_sql_with_nosql():
    from app.tailor.alignment import evidence_index, validate_alignment, keyword_report

    index = evidence_index(EVIDENCE)
    assert index["technical_skills/analytics/1"] == "SQL (coursework)"
    rows = [{"keyword": "SQL", "requirement": "SQL", "support": "direct",
             "evidence_ids": ["technical_skills/analytics/1"], "placements": ["skills"],
             "boundary": "Coursework only, no paid-use claim."}]
    validate_alignment(rows, "SQL preferred", index, "resume")
    report = keyword_report(rows, {"status": "ready", "findings": []},
        {"summary": "Used NoSQL", "skills": [{"items": "NoSQL"}]}, "resume", "SQL preferred", EVIDENCE, "agent")
    assert report["coverage"][0]["status"] == "could_improve"


@pytest.mark.parametrize("review", [
    {"status": "ready", "findings": [{"issue": "hidden problem"}]},
    {"status": "needs_revision", "findings": []},
    {"status": "needs_revision", "findings": [{"section": "summary", "quote": "Absent text",
                                              "issue": "unsupported", "suggestion": "Remove"}]},
])
def test_malformed_or_unbound_reviews_cannot_pass(review):
    from app.tailor.alignment import validate_claim_review
    with pytest.raises(ValueError):
        validate_claim_review(review, {"summary": "Investigated discrepancies."}, "resume")
