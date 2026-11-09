"""Keep resume authoring instructions consistent about experience ordering."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_resume_skills_share_chronological_default():
    skills = ROOT / ".agents" / "skills"
    tailor = (skills / "doorknock-tailor" / "SKILL.md").read_text(encoding="utf-8")
    assert "reverse chronological order" in tailor
    assert "ongoing" in tailor
    assert "user approv" in tailor
    assert "bullet selection and depth" in tailor

    assert "place them at the **end of the Experience section**" not in tailor
    assert "active continuity anchor at the end" not in tailor
    assert "Always place the candidate's most relevant" not in tailor
    assert "explicitly authorized selective omission" in tailor
    assert "potential employment gaps" in tailor


def test_active_review_route_replaces_retired_pipeline():
    skills = ROOT / ".agents" / "skills"
    retired = "doorknock-resume-3stage"
    assert not (skills / retired / "SKILL.md").exists()
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert retired not in agents
    assert "doorknock-resume-roast-scorer" in agents
    for name in ("doorknock-tailor", "doorknock-resume-roast-scorer"):
        content = (skills / name / "SKILL.md").read_text(encoding="utf-8")
        assert retired not in content
    review = (skills / "doorknock-resume-roast-scorer" / "SKILL.md").read_text(encoding="utf-8")
    assert "evidence bank" in review
    assert "Propose the answer before asking questions" in review
