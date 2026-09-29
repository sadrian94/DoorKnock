"""Conservative, mechanical checks before publishing a tailored resume."""

import re
from typing import Any

import yaml


_NUMBER = re.compile(r"(?<![\w])\$?\d[\d,.]*(?:\s?[KMB])?%?", re.IGNORECASE)


def _normal(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _numbers(value: Any) -> set[str]:
    return {re.sub(r"[\s,$]", "", match.group()).casefold()
            for match in _NUMBER.finditer(str(value or ""))}


def validate_resume_evidence(resume: dict[str, Any], evidence_context: str) -> None:
    """Reject unsupported exact facts; prose still needs a human claim review."""
    evidence = yaml.safe_load(evidence_context)
    if not isinstance(evidence, dict):
        raise ValueError("Structured candidate evidence is required for resume validation")

    experiences = evidence.get("experiences") or []
    if not isinstance(experiences, list):
        raise ValueError("Candidate experiences must be a list")
    for entry in resume.get("experiences", []):
        if not isinstance(entry, dict):
            raise ValueError("Resume experience must be an object")
        match = next((source for source in experiences if isinstance(source, dict)
                      and _normal(source.get("company")) == _normal(entry.get("company"))), None)
        if match is None:
            raise ValueError("Resume employer is absent from master evidence")
        for output_key, evidence_key in (("title", "role"), ("dates", "dates"), ("location", "location")):
            if _normal(entry.get(output_key)) != _normal(match.get(evidence_key)):
                raise ValueError(f"Resume experience {output_key} differs from master evidence")

    education = evidence.get("education") or []
    if not isinstance(education, list):
        raise ValueError("Candidate education must be a list")
    for entry in resume.get("education", []):
        if not isinstance(entry, dict):
            raise ValueError("Resume education must be an object")
        institution_matches = [source for source in education if isinstance(source, dict)
                               and _normal(source.get("institution")) == _normal(entry.get("institution"))]
        if not institution_matches:
            raise ValueError("Resume institution is absent from master evidence")
        match = next((source for source in institution_matches
                      if _normal(source.get("degree")) == _normal(entry.get("degree"))), None)
        if match is None:
            raise ValueError("Resume education degree differs from master evidence")
        for key in ("year", "location"):
            if _normal(entry.get(key)) != _normal(match.get(key)):
                raise ValueError(f"Resume education {key} differs from master evidence")

    projects = evidence.get("projects") or []
    if not isinstance(projects, list):
        raise ValueError("Candidate projects must be a list")
    known_projects = {_normal(source.get("name")) for source in projects if isinstance(source, dict)}
    for entry in resume.get("projects", []):
        if not isinstance(entry, dict) or _normal(entry.get("name")) not in known_projects:
            raise ValueError("Resume project is absent from master evidence")

    source_numbers = _numbers(evidence_context)
    claim_text = [resume.get("summary", "")]
    for section in ("experiences", "projects"):
        for entry in resume.get(section, []):
            claim_text.extend(entry.get("bullets", []))
    claim_text.append(resume.get("certifications", ""))
    unsupported = set().union(*(_numbers(value) for value in claim_text)) - source_numbers
    if unsupported:
        raise ValueError("Resume contains numbers absent from master evidence: " + ", ".join(sorted(unsupported)))
