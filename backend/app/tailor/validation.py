"""Conservative, mechanical checks before publishing a tailored resume."""

import re
from typing import Any

import yaml
from ..evidence_schema import eligible_evidence, is_eligible
from .alignment import evidence_index


# A scale suffix must be a whole unit, not the first letter of MAE, mean, or budget.
_NUMBER = re.compile(r"(?<![\w])\$?\d[\d,.]*(?:\s?[KMB](?!\w))?%?", re.IGNORECASE)


def _normal(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _numbers(value: Any) -> set[str]:
    return {re.sub(r"[\s,$]", "", match.group()).casefold()
            for match in _NUMBER.finditer(str(value or ""))}


def _eligible_numbers(record: Any) -> set[str]:
    """Use claim content, never source dates, notes, IDs or tailoring guidance."""
    if isinstance(record, list):
        return set().union(*(_eligible_numbers(item) for item in record))
    if not isinstance(record, dict):
        return set()
    if "bullets" in record:
        return _eligible_numbers(record["bullets"]) | _numbers(record.get("dates")) | _numbers(record.get("name"))
    if "degree" in record:
        return _numbers(record["degree"]) | _numbers(record.get("year")) | _numbers(record.get("focus"))
    allowed = _numbers(record.get("text", record.get("name", "")))
    denied = set()
    for metric in record.get("metrics", []):
        tokens = _numbers(metric.get("text")) | _numbers(metric.get("value"))
        if is_eligible(metric):
            allowed |= tokens
        else:
            denied |= tokens
    return allowed - denied


def _check_numbers(values: list[Any], allowed: set[str]) -> None:
    unsupported = set().union(*(_numbers(value) for value in values)) - allowed
    if unsupported:
        raise ValueError("Resume contains numbers absent from master evidence: " + ", ".join(sorted(unsupported)))


def _bank_numbers(evidence: dict[str, Any]) -> set[str]:
    return _eligible_numbers(evidence.get("experiences", []) + evidence.get("projects", []) + evidence.get("education", [])) | set().union(
        *(_eligible_numbers(values) for values in evidence.get("technical_skills", {}).values()),
        *(_eligible_numbers(values) for values in evidence.get("certifications", {}).values()))


def _numeric_references(payload, evidence_context, paths, scopes=None):
    """Bind numeric claims to eligible IDs; semantic fidelity still needs review."""
    index = evidence_index(evidence_context)
    bindings = payload.get("claim_evidence", {})
    if not isinstance(bindings, dict):
        raise ValueError("claim_evidence must be an object mapping claim paths to evidence IDs")

    def reference_numbers(ref):
        record = index[ref].get("bullet", index[ref])
        # An engagement/project ID supports identity dates/name, never all its metrics.
        if "bullets" in record:
            return _numbers(record.get("dates")) | _numbers(record.get("name"))
        allowed = _eligible_numbers(record)
        refs = record.get("evidence_refs", [])
        if refs:
            allowed &= set().union(*(reference_numbers(source) for source in refs))
        return allowed

    for path, value in paths.items():
        if not _numbers(value):
            continue
        refs = bindings.get(path)
        if not isinstance(refs, list) or not refs or any(
                not isinstance(ref, str) or ref not in index
                or (scopes and path in scopes and ref not in scopes[path]) for ref in refs):
            raise ValueError(f"claim_evidence.{path}: numeric claim requires eligible, specific source IDs in its original context")
        allowed = set().union(*(reference_numbers(ref) for ref in refs))
        _check_numbers([value], allowed)


def validate_resume_evidence(resume: dict[str, Any], evidence_context: str) -> None:
    """Reject unsupported exact facts; prose still needs a human claim review."""
    evidence = yaml.safe_load(evidence_context)
    if not isinstance(evidence, dict):
        raise ValueError("Structured candidate evidence is required for resume validation")
    evidence = eligible_evidence(evidence)
    v2 = evidence.get("schema_version") == 2
    paths = {"summary": resume.get("summary", ""), "certifications": resume.get("certifications", "")}
    scopes = {}

    experiences = evidence.get("experiences") or []
    if not isinstance(experiences, list):
        raise ValueError("Candidate experiences must be a list")
    for position, entry in enumerate(resume.get("experiences", [])):
        if not isinstance(entry, dict):
            raise ValueError("Resume experience must be an object")
        match = next((source for source in experiences if isinstance(source, dict)
                      and _normal(source.get("company")) == _normal(entry.get("company"))), None)
        if match is None:
            raise ValueError("Resume employer is absent from master evidence")
        for output_key, evidence_key in (("title", "role"), ("dates", "dates"), ("location", "location")):
            if _normal(entry.get(output_key)) != _normal(match.get(evidence_key)):
                raise ValueError(f"Resume experience {output_key} differs from master evidence")
        if v2:
            _check_numbers(entry.get("bullets", []), _eligible_numbers(match))
            for offset, text in enumerate(entry.get("bullets", [])):
                path = f"experiences/{position}/bullets/{offset}"
                paths[path] = text
                scopes[path] = {match["id"], *(b["id"] for b in match["bullets"])}

    education = evidence.get("education") or []
    if not isinstance(education, list):
        raise ValueError("Candidate education must be a list")
    for position, entry in enumerate(resume.get("education", [])):
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
        if v2:
            path = f"education/{position}/focus"
            paths[path] = entry.get("focus", "")
            scopes[path] = {match["id"]}

    projects = evidence.get("projects") or []
    if not isinstance(projects, list):
        raise ValueError("Candidate projects must be a list")
    known_projects = {_normal(source.get("name")) for source in projects if isinstance(source, dict)}
    for position, entry in enumerate(resume.get("projects", [])):
        if not isinstance(entry, dict) or _normal(entry.get("name")) not in known_projects:
            raise ValueError("Resume project is absent from master evidence")
        if v2:
            match = next(p for p in projects if _normal(p.get("name")) == _normal(entry.get("name")))
            _check_numbers(entry.get("bullets", []), _eligible_numbers(match))
            for offset, text in enumerate(entry.get("bullets", [])):
                path = f"projects/{position}/bullets/{offset}"
                paths[path] = text
                scopes[path] = {match["id"], *(b["id"] for b in match["bullets"])}

    if v2:
        _check_numbers([resume.get("summary", ""), resume.get("certifications", "")], _bank_numbers(evidence))
        for position, skill in enumerate(resume.get("skills", [])):
            paths[f"skills/{position}/items"] = skill.get("items", skill.get("skills", ""))
        _numeric_references(resume, evidence_context, paths, scopes)
        return

    source_numbers = _numbers(evidence_context)
    claim_text = [resume.get("summary", "")]
    for section in ("experiences", "projects"):
        for entry in resume.get(section, []):
            claim_text.extend(entry.get("bullets", []))
    claim_text.append(resume.get("certifications", ""))
    unsupported = set().union(*(_numbers(value) for value in claim_text)) - source_numbers
    if unsupported:
        raise ValueError("Resume contains numbers absent from master evidence: " + ", ".join(sorted(unsupported)))


def validate_letter_evidence(letter: dict[str, Any], evidence_context: str) -> None:
    """Apply the same pending-metric guard to letters, including authored letters."""
    evidence = eligible_evidence(yaml.safe_load(evidence_context))
    if evidence.get("schema_version") == 2:
        _check_numbers(letter.get("paragraphs", []), _bank_numbers(evidence))
        _numeric_references(letter, evidence_context,
                            {f"paragraphs/{i}": text for i, text in enumerate(letter.get("paragraphs", []))})
