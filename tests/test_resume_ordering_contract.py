"""Keep resume authoring instructions consistent about experience ordering."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_resume_skills_share_chronological_default():
    skills = ROOT / ".agents" / "skills"
    tailor = (skills / "doorknock-tailor" / "SKILL.md").read_text(encoding="utf-8")
    three_stage = (skills / "doorknock-resume-3stage" / "SKILL.md").read_text(encoding="utf-8")

    for content in (tailor, three_stage):
        assert "reverse chronological order" in content
        assert "ongoing" in content
        assert "user approv" in content
        assert "bullet selection and depth" in content

    assert "place them at the **end of the Experience section**" not in three_stage
    assert "active continuity anchor at the end" not in three_stage
    assert "Always place the candidate's most relevant" not in three_stage
    assert "explicitly authorized selective omission" in tailor
    assert "potential employment gaps" in tailor
    assert "do not automatically omit a role" in three_stage
