"""Keep authoring and review rules open to unrecorded work, not invented facts.

These are instruction-contract regressions, not tests of model compliance.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"


def test_strengthening_contract_spans_discovery_authoring_and_review():
    for name in (
        "doorknock-refine",
        "doorknock-tailor",
        "doorknock-resume-roast-scorer",
    ):
        content = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        assert "Unrecorded does not mean unperformed" in content
        assert "decompose each rewrite into clauses" in content.lower()
        assert "purpose" in content
        assert "financial model" in content
        assert "complete" in content
        assert "confirmation" in content or "confirmations" in content


def test_discovery_and_blind_review_keep_distinct_authority():
    refine = (SKILLS / "doorknock-refine" / "SKILL.md").read_text(encoding="utf-8")
    rubric = (SKILLS / "doorknock-refine" / "references" / "refine-rubric.md").read_text(
        encoding="utf-8"
    )
    review = (SKILLS / "doorknock-resume-roast-scorer" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "separate write authorization and backup" in refine
    assert "at most one material clarification" in refine
    assert "successive discovery rounds" in refine
    assert "Decompose each rewrite into clauses" in rubric
    assert "do not ask again or silently write the bank" in rubric
    assert "not demonstrated here" in review
    assert "coordinator, not this reviewer" in review
    assert "Stay within the blind-input boundary" in review
    assert "conditional proposal is not yet a publication-ready fact" in review
