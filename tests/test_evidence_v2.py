"""Synthetic contracts for versioned evidence, traceability and publication."""
from copy import deepcopy

import pytest
import yaml

from app.evidence import load_master_evidence
from app.tailor.alignment import evidence_index, validate_alignment
from app.tailor.validation import validate_resume_evidence


def bank():
    return {
        "schema_version": 2,
        "sources": [{"id": "src-confirmation", "kind": "user_confirmation",
                     "description": "Synthetic confirmation", "confirmed_at": "2026-01-12"}],
        "experiences": [{
            "id": "exp-sample", "company": "Apex Logistics", "role": "Operations Analyst",
            "dates": "2024-2025", "location": "Sample City", "evidence_class": "paid_work",
            "status": "confirmed", "source_refs": ["src-confirmation"],
            "bullets": [
                {"id": "claim-reporting", "text": "Prepared reports for 7 teams.",
                 "status": "confirmed", "source_refs": ["src-confirmation"], "metrics": []},
                {"id": "claim-bids", "text": "Reviewed 23 vendor bids.",
                 "status": "pending_confirmation", "source_refs": ["src-confirmation"],
                 "metrics": [{"text": "23 bids", "value": 23, "unit": "bids", "scope": "individual",
                              "basis": "unclassified", "status": "pending_confirmation",
                              "source_refs": ["src-confirmation"]}]},
            ]}],
        "projects": [],
        "technical_skills": {"analytics": [{"id": "skill-sql", "text": "SQL (coursework)",
            "status": "recorded", "source_refs": ["src-confirmation"], "evidence_class": "coursework"}]},
        "education": [{"id": "edu-sample", "institution": "Sample University", "degree": "BS Analytics",
                       "year": "2023", "location": "Sample City", "status": "recorded",
                       "source_refs": ["src-confirmation"]}],
        "certifications": {"primary": [{"id": "cert-sample", "name": "Sample Credential",
                                        "status": "recorded", "source_refs": ["src-confirmation"]}],
                           "secondary": []},
        "presentation_groups": [],
    }


def context(data):
    return yaml.safe_dump(data, sort_keys=False)


@pytest.mark.parametrize("mutation,location", [
    (lambda d: d.update(schema_version=99), "schema_version"),
    (lambda d: d.update(experiences="invalid"), "experiences"),
    (lambda d: d["experiences"][0]["bullets"][0].pop("status"), "status"),
    (lambda d: d["technical_skills"]["analytics"][0].update(source_refs=["missing"]), "source_refs"),
    (lambda d: d["education"][0].update(id="skill-sql"), "Duplicate"),
    (lambda d: d["sources"][0].update(confirmed_at="not-a-date"), "confirmed_at"),
])
def test_loader_reports_invalid_v2_location(tmp_path, monkeypatch, mutation, location):
    data = bank()
    mutation(data)
    path = tmp_path / "evidence.yaml"
    path.write_text(context(data), encoding="utf-8")
    monkeypatch.setattr("app.evidence.DOORKNOCK_MASTER_EVIDENCE_YAML_PATH", path)
    with pytest.raises(ValueError, match=location):
        load_master_evidence()


def test_v2_index_uses_stable_skill_and_credential_ids_and_excludes_pending():
    data = bank()
    before = evidence_index(context(data))
    data["technical_skills"]["analytics"].insert(0, {
        "id": "skill-python", "text": "Python", "status": "recorded", "source_refs": ["src-confirmation"]})
    after = evidence_index(context(data))
    assert before["skill-sql"] == after["skill-sql"]
    assert after["edu-sample"]["degree"] == "BS Analytics"
    assert after["cert-sample"]["name"] == "Sample Credential"
    assert "claim-bids" not in after
    assert [b["id"] for b in after["exp-sample"]["bullets"]] == ["claim-reporting"]


def test_pending_reference_cannot_be_declared_supported():
    rows = [{"keyword": "bids", "requirement": "Review bids", "support": "direct",
             "evidence_ids": ["claim-bids"], "placements": ["experiences"], "boundary": "Individual work"}]
    with pytest.raises(ValueError, match="unknown evidence"):
        validate_alignment(rows, "Review bids", evidence_index(context(bank())), "resume")


def test_pending_number_does_not_become_eligible_through_notes_or_metadata():
    data = bank()
    data["tailoring_guidance"] = {"note": "23 bids may need confirmation"}
    data["sources"][0]["description"] = "Conversation about 23 bids"
    with pytest.raises(ValueError, match="numbers absent"):
        validate_resume_evidence({"summary": "Reviewed 23 bids."}, context(data))
    validate_resume_evidence({"summary": "Reported for 7 teams.",
        "claim_evidence": {"summary": ["claim-reporting"]}}, context(data))


def test_numeric_evidence_cannot_be_borrowed_from_another_employer():
    data = bank()
    second = deepcopy(data["experiences"][0])
    second.update(id="exp-other", company="Summit Services", bullets=[{
        "id": "claim-other", "text": "Handled 47 requests.", "metrics": [],
        "status": "confirmed", "source_refs": ["src-confirmation"]}])
    data["experiences"].append(second)
    output = {"experiences": [{"company": "Apex Logistics", "title": "Operations Analyst",
        "dates": "2024-2025", "location": "Sample City", "bullets": ["Handled 47 requests."]}]}
    with pytest.raises(ValueError, match="numbers absent"):
        validate_resume_evidence(output, context(data))


def test_pending_metric_is_blocked_even_when_duplicated_in_eligible_bullet_text():
    data = bank()
    claim = data["experiences"][0]["bullets"][1]
    claim["status"] = "confirmed"
    with pytest.raises(ValueError, match="numbers absent"):
        validate_resume_evidence({"summary": "Reviewed 23 bids."}, context(data))


def test_v1_migration_preserves_ids_text_and_qualifiers_without_creating_confirmation():
    from app.evidence_schema import migrate_evidence_v1, validate_evidence_bank
    original = {"schema_version": 1, "experiences": [{
        "id": "exp-one", "company": "Apex Logistics", "role": "Analyst", "dates": "2024",
        "location": "Sample City", "evidence_class": "paid_work",
        "evidence_status": "An old note; exact scope remains unverified.",
        "bullets": [{"id": "claim-one", "text": "Checked records.", "metrics": ["scope not quantified"]}]}],
        "projects": [], "technical_skills": {"analytics": ["SQL (coursework)"]},
        "education": [], "certifications": {"primary": ["Sample Credential"], "secondary": []}}
    untouched = deepcopy(original)
    result = migrate_evidence_v1(original, recorded_at="2026-01-12")
    validate_evidence_bank(result)
    assert original == untouched
    entry = result["experiences"][0]
    assert entry["id"] == "exp-one" and entry["bullets"][0]["id"] == "claim-one"
    assert entry["bullets"][0]["text"] == "Checked records."
    assert entry["evidence_status"] == original["experiences"][0]["evidence_status"]
    assert entry["status"] == "recorded"
    assert entry["bullets"][0]["metrics"][0]["text"] == "scope not quantified"
    assert all(s.get("confirmed_at") is None for s in result["sources"])
    assert migrate_evidence_v1(result, recorded_at="2026-01-13") == result


def test_presentation_group_is_a_reference_view_not_an_additional_employer():
    from app.evidence_schema import validate_evidence_bank
    data = bank()
    data["presentation_groups"] = [{"id": "group-contracts", "heading": "Contract analyst",
        "member_ids": ["exp-sample"], "bullets": [{"id": "claim-combined", "text": "Prepared reports.",
            "evidence_refs": ["claim-reporting"], "status": "recorded",
            "source_refs": ["src-confirmation"], "metrics": []}]}]
    validate_evidence_bank(data)
    index = evidence_index(context(data))
    assert index["claim-combined"]["evidence_refs"] == ["claim-reporting"]
    data["presentation_groups"][0]["bullets"][0]["evidence_refs"] = ["claim-bids"]
    assert "claim-combined" not in evidence_index(context(data))
    data["presentation_groups"][0]["member_ids"] = ["unknown"]
    with pytest.raises(ValueError, match="member_ids"):
        validate_evidence_bank(data)


def test_migration_preserves_legacy_skill_colon_mapping_as_text():
    from app.evidence_schema import migrate_evidence_v1
    legacy = {"schema_version": 1, "technical_skills": {
        "process": [{"Issue tracking": "Exploratory use; no production claim"}]}}
    upgraded = migrate_evidence_v1(legacy, recorded_at="2026-01-12")
    assert upgraded["technical_skills"]["process"][0]["text"] == "Issue tracking: Exploratory use; no production claim"


def test_numeric_summary_requires_specific_eligible_claim_references():
    data = bank()
    data["experiences"][0]["bullets"][1]["text"] = "Reviewed 7 bids."
    data["experiences"][0]["bullets"][1]["metrics"][0].update(text="7 bids", value=7)
    with pytest.raises(ValueError, match="claim_evidence"):
        validate_resume_evidence({"summary": "Reviewed 7 bids."}, context(data))
    with pytest.raises(ValueError, match="claim_evidence"):
        validate_resume_evidence({"summary": "Reviewed 7 bids.",
            "claim_evidence": {"summary": ["claim-bids"]}}, context(data))
    validate_resume_evidence({"summary": "Prepared reports for 7 teams.",
        "claim_evidence": {"summary": ["claim-reporting"]}}, context(data))


def test_numeric_bullet_reference_must_belong_to_the_matching_engagement():
    data = bank()
    data["projects"].append({"id": "proj-demo", "name": "Sample Study", "evidence_class": "portfolio",
        "status": "recorded", "source_refs": ["src-confirmation"], "bullets": [{
            "id": "claim-study", "text": "Analyzed 7 examples.", "status": "recorded",
            "source_refs": ["src-confirmation"], "metrics": []}]})
    resume = {"experiences": [{"company": "Apex Logistics", "title": "Operations Analyst",
        "dates": "2024-2025", "location": "Sample City", "bullets": ["Prepared reports for 7 teams."]}],
        "claim_evidence": {"experiences/0/bullets/0": ["claim-study"]}}
    with pytest.raises(ValueError, match="claim_evidence"):
        validate_resume_evidence(resume, context(data))
    resume["claim_evidence"]["experiences/0/bullets/0"] = ["claim-reporting"]
    validate_resume_evidence(resume, context(data))


def test_empty_presentation_view_is_valid_without_explicit_bullets():
    data = bank()
    data["presentation_groups"] = [{"id": "group-contracts", "heading": "Contract analyst",
                                    "member_ids": ["exp-sample"]}]
    assert "claim-reporting" in evidence_index(context(data))


def test_derived_claim_cannot_launder_a_pending_underlying_metric():
    data = bank()
    data["experiences"][0]["bullets"][1]["status"] = "confirmed"
    data["experiences"][0]["bullets"].append({
        "id": "claim-derived", "text": "Reviewed 23 vendor bids.", "status": "recorded",
        "source_refs": ["src-confirmation"], "evidence_refs": ["claim-bids"], "metrics": []})
    with pytest.raises(ValueError, match="numbers absent"):
        validate_resume_evidence({"summary": "Reviewed 23 bids.",
            "claim_evidence": {"summary": ["claim-derived"]}}, context(data))


def test_education_focus_is_reviewable_and_cannot_introduce_unsupported_numbers():
    from app.tailor.alignment import validate_claim_review
    data = bank()
    output = {"education": [{"institution": "Sample University", "degree": "BS Analytics",
        "year": "2023", "location": "Sample City", "focus": "GPA 9.99; top 99% of class"}],
        "claim_evidence": {"education/0/focus": ["edu-sample"]}}
    with pytest.raises(ValueError, match="numbers absent"):
        validate_resume_evidence(output, context(data))
    validate_claim_review({"status": "needs_revision", "findings": [{
        "section": "education", "quote": "GPA 9.99", "issue": "Not established", "suggestion": "Omit GPA"}]},
        output, "resume")


def test_employment_years_can_cite_identity_without_borrowing_its_other_claims():
    from app.tailor.validation import validate_letter_evidence
    data = bank()
    letter = {"paragraphs": ["During 2024, I prepared reports for 7 teams."],
              "claim_evidence": {"paragraphs/0": ["exp-sample", "claim-reporting"]}}
    validate_letter_evidence(letter, context(data))
    letter["claim_evidence"]["paragraphs/0"] = ["exp-sample"]
    with pytest.raises(ValueError, match="numbers absent"):
        validate_letter_evidence(letter, context(data))
