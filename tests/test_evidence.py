import sys
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.evidence import (
    load_master_evidence,
    format_evidence_for_prompt,
    get_candidate_master_context,
)


SYNTHETIC_EVIDENCE = {
    "schema_version": 1,
    "headline": "Sample Systems Analyst",
    "summary_pool": [
        {"id": "summary-1", "focus": "operations", "text": "Improved sample reporting."}
    ],
    "experiences": [
        {
            "id": "experience-1",
            "company": "Apex Logistics",
            "role": "Operations Analyst",
            "location": "Sample City",
            "dates": "2024-2025",
            "tenure_context": "Synthetic test record",
            "bullets": [
                {
                    "id": "experience-bullet-1",
                    "category": "reporting",
                    "tags": ["sample-tag"],
                    "metrics": ["12% synthetic change"],
                    "text": "Built a synthetic reporting workflow.",
                }
            ],
        }
    ],
    "projects": [
        {
            "id": "project-1",
            "name": "Route Study",
            "role_type": "portfolio",
            "tech_stack": ["Python", "SQLite"],
            "github_url": "https://example.com/route-study",
            "bullets": [
                {
                    "id": "project-bullet-1",
                    "label": "Validation",
                    "tags": ["synthetic-project-tag"],
                    "metrics": ["3 synthetic checks"],
                    "text": "Validated synthetic route data.",
                }
            ],
        }
    ],
    "technical_skills": {"analytics_and_bi": ["SQL", "Power BI"]},
    "education": [
        {
            "institution": "Global Tech University",
            "degree": "Sample Bachelor Degree",
            "year": "2024",
            "location": "Sample City",
            "focus": "Analytics",
        }
    ],
    "certifications": {
        "primary": ["Sample Primary Certification"],
        "secondary": ["Sample Secondary Certification"],
    },
}


@pytest.fixture
def synthetic_evidence_file(tmp_path, monkeypatch):
    path = tmp_path / "workspace" / "master_resume" / "master_evidence.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(SYNTHETIC_EVIDENCE, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr("app.evidence.DOORKNOCK_MASTER_EVIDENCE_YAML_PATH", path)
    return path


def test_load_master_evidence(synthetic_evidence_file):
    data = load_master_evidence()
    assert data["experiences"][0]["company"] == "Apex Logistics"
    assert data["projects"][0]["name"] == "Route Study"


def test_prompt_context_preserves_the_complete_yaml_evidence(synthetic_evidence_file):
    formatted = format_evidence_for_prompt(load_master_evidence())
    assert "experience-bullet-1" in formatted
    assert "sample-tag" in formatted
    assert "project-bullet-1" in formatted
    assert "synthetic-project-tag" in formatted
    assert "3 synthetic checks" in formatted
    assert "Sample Secondary Certification" in formatted


def test_get_candidate_master_context_uses_synthetic_yaml(synthetic_evidence_file):
    context = get_candidate_master_context()
    assert "Apex Logistics" in context
    assert "Sample Secondary Certification" in context


def test_missing_yaml_does_not_fall_back_to_plaintext(tmp_path, monkeypatch):
    evidence_path = tmp_path / "workspace" / "master_resume" / "master_evidence.yaml"
    evidence_path.parent.mkdir(parents=True)
    (evidence_path.parent / "master_resume.txt").write_text(
        "Synthetic legacy fallback content that must be ignored.", encoding="utf-8"
    )
    monkeypatch.setattr("app.evidence.DOORKNOCK_MASTER_EVIDENCE_YAML_PATH", evidence_path)
    assert load_master_evidence() is None
    assert get_candidate_master_context() == ""


def test_profile_context_requires_valid_yaml(tmp_path, monkeypatch):
    evidence_path = tmp_path / "workspace" / "master_resume" / "master_evidence.yaml"
    evidence_path.parent.mkdir(parents=True)
    (evidence_path.parent / "master_resume.txt").write_text(
        "Synthetic legacy fallback content that must not be returned.", encoding="utf-8"
    )
    monkeypatch.setattr("app.evidence.DOORKNOCK_MASTER_EVIDENCE_YAML_PATH", evidence_path)
    from app.ai.profile import get_candidate_profile_context

    with pytest.raises(ValueError, match="master_evidence.yaml"):
        get_candidate_profile_context()
