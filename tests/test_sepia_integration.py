from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_sepia_skills_vendored_and_accessible():
    sepia_dir = REPO_ROOT / ".agents" / "skills" / "sepia"
    assert sepia_dir.is_dir(), ".agents/skills/sepia directory must exist"
    
    canonical_skill = sepia_dir / "SKILL.md"
    assert canonical_skill.is_file(), "Canonical Sepia SKILL.md must be present"
    assert canonical_skill.stat().st_size > 1000

    refs_dir = sepia_dir / "references"
    assert refs_dir.is_dir()
    assert (refs_dir / "professional-pass.md").is_file()
    assert (refs_dir / "style-pass.md").is_file()
    assert (refs_dir / "rubric.md").is_file()

def test_sepia_subskills_sibling_resolution():
    subskills = ["sepia-review", "sepia-refactor", "sepia-write", "sepia-recreate"]
    skills_root = REPO_ROOT / ".agents" / "skills"
    
    for sub in subskills:
        sub_dir = skills_root / sub
        assert sub_dir.is_dir(), f"{sub} skill directory must exist"
        skill_file = sub_dir / "SKILL.md"
        assert skill_file.is_file(), f"{sub}/SKILL.md must exist"
        
        # Test sibling resolution contract (../sepia/SKILL.md)
        resolved_canonical = (sub_dir / ".." / "sepia" / "SKILL.md").resolve()
        assert resolved_canonical.is_file(), f"{sub} failed to resolve sibling ../sepia/SKILL.md"
