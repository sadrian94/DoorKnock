"""Evidence-linked keyword planning and advisory literal coverage.

ID validity and word presence cannot establish semantic support. Claim reviews
are agent/provider judgments, not an ATS score or an independent truth proof.
"""
import hashlib
import json
import re
from typing import Any

import yaml


def evidence_index(evidence_context: str) -> dict[str, Any]:
    evidence = yaml.safe_load(evidence_context)
    if not isinstance(evidence, dict):
        raise ValueError("Structured evidence is required for keyword alignment")
    index = {}

    def add(key, value):
        if key in index:
            raise ValueError("Duplicate keyword evidence ID")
        index[key] = value

    for section in ("experiences", "projects"):
        for entry in evidence.get(section, []) or []:
            if entry.get("id"):
                add(entry["id"], entry)
            for bullet in entry.get("bullets", []) or []:
                if bullet.get("id"):
                    # Keep provenance and confirmation limits beside each bullet.
                    add(bullet["id"], {"section": section, "parent_id": entry.get("id"),
                                      "evidence_class": entry.get("evidence_class"),
                                      "evidence_status": entry.get("evidence_status"), "bullet": bullet})
    for category, skills in (evidence.get("technical_skills") or {}).items():
        for position, skill in enumerate(skills):
            add(f"technical_skills/{category}/{position}", skill)
    return index


def _normal(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _contains(text: str, phrase: str) -> bool:
    # Word boundaries prevent SQL matching NoSQL; Typst bold is not content.
    return bool(re.search(r"(?<!\w)" + re.escape(_normal(phrase)) + r"(?!\w)",
                          _normal(text.replace("*", ""))))


def validate_alignment(rows, posting: str, index: dict, document_type: str) -> None:
    if not isinstance(rows, list) or (posting.strip() and not rows):
        raise ValueError("Keyword alignment requires a nonempty list for a posting")
    sections = {"summary", "experiences", "projects", "skills"} if document_type == "resume" else {"paragraphs"}
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Keyword alignment entries must be objects")
        for key in ("keyword", "requirement", "boundary"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Keyword alignment requires {key}")
        if not _contains(posting, row["requirement"]) or not _contains(row["requirement"], row["keyword"]):
            raise ValueError("Keyword requirement must quote the posting and contain its keyword")
        identity = (_normal(row["keyword"]), _normal(row["requirement"]))
        if identity in seen:
            raise ValueError("Duplicate keyword alignment entry")
        seen.add(identity)
        support = row.get("support")
        if support not in {"direct", "transferable", "unsupported"}:
            raise ValueError("Invalid keyword support level")
        refs, placements = row.get("evidence_ids"), row.get("placements")
        if not isinstance(refs, list) or not all(isinstance(ref, str) and ref in index for ref in refs):
            raise ValueError("Keyword alignment contains unknown evidence IDs")
        if not isinstance(placements, list) or not all(isinstance(s, str) and s in sections for s in placements):
            raise ValueError("Invalid keyword placement for document type")
        if support == "unsupported":
            if refs or placements:
                raise ValueError("Unsupported keywords cannot have evidence or planned placements")
        elif not refs or not placements:
            raise ValueError("Supported keywords require evidence and planned placements")


def validate_claim_review(review, payload: dict, document_type: str) -> None:
    if not isinstance(review, dict) or review.get("status") not in {"ready", "needs_revision"}:
        raise ValueError("Claim review requires ready or needs_revision status")
    findings = review.get("findings")
    if not isinstance(findings, list) or (review["status"] == "ready") != (not findings):
        raise ValueError("Claim review status must agree with findings")
    sections = document_sections(payload, document_type)
    for finding in findings:
        if not isinstance(finding, dict) or any(not isinstance(finding.get(key), str) or not finding[key].strip()
                                              for key in ("section", "quote", "issue", "suggestion")):
            raise ValueError("Claim findings require section, quote, issue and suggestion")
        section = finding["section"]
        if section not in sections or not _contains(sections[section], finding["quote"]):
            raise ValueError("Claim finding must quote the reviewed document section")


def document_sections(payload: dict, document_type: str) -> dict[str, str]:
    if document_type == "cover_letter":
        return {"paragraphs": "\n".join(payload.get("paragraphs", []))}
    return {
        "summary": payload.get("summary", ""),
        "experiences": "\n".join(b for e in payload.get("experiences", []) for b in e.get("bullets", [])),
        "projects": "\n".join(b for p in payload.get("projects", []) for b in p.get("bullets", [])),
        "skills": "\n".join(s.get("items", s.get("skills", "")) for s in payload.get("skills", [])),
    }


def keyword_report(rows, review, payload: dict, document_type: str, posting: str, evidence: str, source: str) -> dict:
    sections = document_sections(payload, document_type)
    coverage = []
    for row in rows or []:
        found = [section for section, text in sections.items() if _contains(text, row["keyword"])]
        status = "evidence_gap" if row["support"] == "unsupported" else ("covered" if found else "could_improve")
        coverage.append({"keyword": row["keyword"], "status": status, "found_in": found,
                         "missing_placements": [s for s in row["placements"] if s not in found]})
    return {
        "schema_version": 1, "document_type": document_type,
        "status": review["status"] if review else "not_reviewed", "review_source": source,
        "posting_sha256": hashlib.sha256(posting.encode("utf-8")).hexdigest(),
        "evidence_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
        "document_sha256": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        "keyword_alignment": rows or [], "coverage": coverage,
        "claim_review": review or {"status": "not_reviewed", "findings": []},
        "limitations": "Literal coverage is advisory, not an ATS score. Evidence IDs do not prove semantic support. "
                        "Provider or agent claim review still requires human verification.",
    }

ALIGNMENT_INSTRUCTION = '''Build keyword_alignment from the main requirements of the supplied posting, including important unsupported requirements. No keyword quotas. Each entry has {"keyword": "<exact JD term>", "requirement": "<verbatim JD excerpt containing that term>", "support": "direct|transferable|unsupported", "evidence_ids": ["<ID from evidence index>"], "placements": ["<allowed section>"], "boundary": "<original domain, tools, ownership, results and provenance limits>"}. Use specific bullet IDs when possible. Direct means evidence supports the requirement in its stated context, not merely a matching word. Transferable preserves the original work domain. Coursework or portfolio tools do not establish paid or production use. Unsupported entries have empty evidence_ids and placements. Never infer achievements from tags, JD text or company recon. Return at least one entry for a nonempty posting.'''

REVIEW_INSTRUCTION = '''Review the completed document against evidence, posting and keyword boundaries. Check every claim, not just mapped keywords. Flag inflated domain, ownership, tools, seniority or results; coursework/portfolio recast as paid work; and speculative employer problems asserted as facts. A valid evidence ID alone is not proof. Supported JD terms and transferable examples are allowed when their original scope remains clear. Missing keywords alone are advisory, not a claim violation. Return {"claim_review": {"status": "ready|needs_revision", "findings": [{"section": "<document section>", "quote": "<exact document excerpt>", "issue": "<unsupported implication>", "suggestion": "<evidence-safe correction>"}]}}. Ready requires no findings; needs_revision requires concrete findings. Do not rewrite the document or invent a score.'''
