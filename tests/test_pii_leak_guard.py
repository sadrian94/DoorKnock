import re
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "workspace",
    "data",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".pytest-tmp",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".png",
    ".jpg",
    ".pdf",
    ".ico",
    ".db",
    ".lock",
}

def get_candidate_pii_tokens() -> list[str]:
    """Read candidate-private tokens only for the source-leakage guard."""
    tokens = []

    def add_token(value, minimum_length=4):
        if isinstance(value, str) and len(value.strip()) >= minimum_length:
            tokens.append(value.strip())

    profile_path = REPO_ROOT / "workspace" / "profile.yaml"
    if profile_path.is_file():
        try:
            data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
            for key in ["full_name", "preferred_name", "email", "phone", "linkedin_url", "github_url"]:
                val = data.get(key)
                add_token(val)
                if isinstance(val, str) and "@" in val:
                    add_token(val.split("@")[0])
                if isinstance(val, str):
                    digits_only = re.sub(r"\D", "", val)
                    if len(digits_only) >= 7:
                        add_token(digits_only, minimum_length=7)
        except Exception:
            pass

    evidence_path = REPO_ROOT / "workspace" / "master_resume" / "master_evidence.yaml"
    if evidence_path.is_file():
        try:
            evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8")) or {}
            for experience in evidence.get("experiences", []):
                for key in ("company", "role", "dates", "location"):
                    add_token(experience.get(key), minimum_length=8)
                for bullet in experience.get("bullets", []):
                    add_token(bullet.get("text"), minimum_length=32)
                    for metric in bullet.get("metrics", []):
                        add_token(metric, minimum_length=8)
            for project in evidence.get("projects", []):
                for key in ("name", "github_url"):
                    add_token(project.get(key), minimum_length=8)
                for bullet in project.get("bullets", []):
                    add_token(bullet.get("text"), minimum_length=32)
                    for metric in bullet.get("metrics", []):
                        add_token(metric, minimum_length=8)
            for education in evidence.get("education", []):
                for key in ("institution", "degree", "year", "location"):
                    add_token(education.get(key), minimum_length=8)
            for cert_type in ("primary", "secondary"):
                for certification in evidence.get("certifications", {}).get(cert_type, []):
                    add_token(certification, minimum_length=8)
        except Exception:
            pass
    return list(set(tokens))

def test_zero_candidate_pii_leak_in_tracked_code():
    """Ensure no personal PII from workspace is hardcoded in frontend, backend, docs, or tests."""
    pii_tokens = get_candidate_pii_tokens()
    if not pii_tokens:
        return

    leaks = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_dir():
            continue
        # Check exclusion directories
        parts = p.relative_to(REPO_ROOT).parts
        if any(part in EXCLUDE_DIRS or part.startswith(".uv-cache") for part in parts):
            continue
        if p.suffix.lower() in EXCLUDE_EXTENSIONS:
            continue
        # Avoid printing or matching the source code of this guard against the live tokens it holds.
        if p.name == "test_pii_leak_guard.py":
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for token in pii_tokens:
            if len(token) < 4:
                continue
            # Check for literal token appearance
            if token.lower() in text.lower():
                # Allow docs discussing how to isolate PII if it does not literally include raw phone/email
                leaks.append(str(p.relative_to(REPO_ROOT)))

    assert not leaks, "Candidate-private facts detected in repository source files:\n" + "\n".join(sorted(set(leaks)))
