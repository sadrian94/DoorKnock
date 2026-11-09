"""Versioned private evidence contracts and a lossless, conservative v1 upgrade."""
from copy import deepcopy
from datetime import date
import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


Status = Literal["recorded", "confirmed", "pending_confirmation", "excluded"]


class Record(BaseModel):
    # Natural-language evidence and candidate-specific metadata remain extensible.
    model_config = ConfigDict(extra="allow", strict=True)


class Source(Record):
    id: str = Field(min_length=1)
    kind: Literal["legacy_snapshot", "user_confirmation", "artifact"]
    description: str = Field(min_length=1)
    confirmed_at: str | None = None
    observed_at: str | None = None
    recorded_at: str | None = None
    revision: str | None = None

    @field_validator("confirmed_at", "observed_at", "recorded_at")
    @classmethod
    def iso_date(cls, value):
        if value is not None:
            try:
                valid = len(value) == 10 and date.fromisoformat(value).isoformat() == value
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("Use an ISO YYYY-MM-DD date")
        return value


class Provenance(Record):
    status: Status
    source_refs: list[str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class Metric(Provenance):
    text: str = Field(min_length=1)
    value: str | int | float | None = None
    unit: str | None = None
    scope: str | None = None
    basis: Literal["measured", "candidate_estimate", "modeled", "context", "unclassified"]
    observed_at: str | None = None
    revision: str | None = None

    _date = field_validator("observed_at")(Source.iso_date.__func__)


class Node(Provenance):
    id: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class Claim(Node):
    text: str = Field(min_length=1)
    metrics: list[Metric] = Field(default_factory=list)


class Experience(Node):
    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    dates: str = Field(min_length=1)
    location: str
    evidence_class: str = Field(min_length=1)
    bullets: list[Claim]


class Project(Node):
    name: str = Field(min_length=1)
    evidence_class: str = Field(min_length=1)
    bullets: list[Claim]


class Skill(Node):
    text: str = Field(min_length=1)


class Education(Node):
    institution: str = Field(min_length=1)
    degree: str = Field(min_length=1)
    year: str
    location: str


class Certification(Node):
    name: str = Field(min_length=1)


class PresentationGroup(Record):
    id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    member_ids: list[str] = Field(min_length=1)
    bullets: list[Claim] = Field(default_factory=list)


class EvidenceV2(Record):
    schema_version: Literal[2]
    sources: list[Source]
    experiences: list[Experience]
    projects: list[Project]
    technical_skills: dict[str, list[Skill]]
    education: list[Education]
    certifications: dict[str, list[Certification]]
    presentation_groups: list[PresentationGroup] = Field(default_factory=list)


def validate_evidence_bank(data: Any) -> dict[str, Any]:
    """Validate without replacing or silently dropping original metadata."""
    if not isinstance(data, dict):
        raise ValueError("Evidence bank must be a mapping")
    version = data.get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("schema_version: expected 1 or 2")
    if version == 1:
        # Existing installations keep their original, flexible v1 records.
        for key in ("experiences", "projects", "education"):
            if key in data and (not isinstance(data[key], list) or
                                any(not isinstance(item, dict) for item in data[key])):
                raise ValueError(f"{key}: expected a list of records")
        return data
    try:
        bank = EvidenceV2.model_validate(data)
    except ValidationError as exc:
        # Report useful paths without echoing private input values in logs/errors.
        details = [".".join(map(str, e["loc"])) + ": " + e["msg"]
                   for e in exc.errors(include_input=False, include_url=False)]
        raise ValueError("Invalid evidence schema: " + "; ".join(details)) from None

    ids = set()
    sources = {s.id for s in bank.sources}
    nodes: dict[str, Node] = {}

    def unique(identity):
        if identity in ids:
            raise ValueError(f"Duplicate evidence ID: {identity}")
        ids.add(identity)

    for source in bank.sources:
        unique(source.id)
    for entry in [*bank.experiences, *bank.projects, *bank.education,
                  *(s for group in bank.technical_skills.values() for s in group),
                  *(c for group in bank.certifications.values() for c in group)]:
        unique(entry.id)
        nodes[entry.id] = entry
        for bullet in getattr(entry, "bullets", []):
            unique(bullet.id)
            nodes[bullet.id] = bullet
    raw_ids = set(nodes)
    experience_claims = {e.id: {b.id for b in e.bullets} for e in bank.experiences}
    for group in bank.presentation_groups:
        unique(group.id)
        if len(set(group.member_ids)) != len(group.member_ids) or any(
                key not in experience_claims for key in group.member_ids):
            raise ValueError(f"presentation_groups.{group.id}.member_ids: unknown or duplicate engagement")
        allowed = set().union(*(experience_claims[key] for key in group.member_ids))
        for bullet in group.bullets:
            unique(bullet.id)
            nodes[bullet.id] = bullet
            if not bullet.evidence_refs or any(ref not in allowed for ref in bullet.evidence_refs):
                raise ValueError(f"{bullet.id}.evidence_refs: group claims must reference member claims")
    for identity, node in nodes.items():
        for item in [node, *getattr(node, "metrics", [])]:
            if any(ref not in sources for ref in item.source_refs):
                raise ValueError(f"{identity}.source_refs: unknown source")
        if any(ref not in raw_ids for ref in node.evidence_refs):
            raise ValueError(f"{identity}.evidence_refs: unknown original evidence")
    # References may enrich provenance; they must never form a circular proof.
    def visit(identity, trail):
        if identity in trail:
            raise ValueError(f"{identity}.evidence_refs: circular reference")
        for ref in nodes[identity].evidence_refs:
            visit(ref, trail | {identity})
    for identity in nodes:
        visit(identity, set())
    return data


def is_eligible(record: dict[str, Any]) -> bool:
    return record.get("status") in {"recorded", "confirmed"}


def eligible_evidence(data: dict[str, Any]) -> dict[str, Any]:
    """A selection view; never feed notes/source dates into numeric claim support."""
    validate_evidence_bank(data)
    if data.get("schema_version", 1) == 1:
        return deepcopy(data)
    result = deepcopy(data)
    available = set()
    for section in ("experiences", "projects"):
        result[section] = [e for e in result[section] if is_eligible(e)]
        for entry in result[section]:
            available.add(entry["id"])
            entry["bullets"] = [b for b in entry["bullets"] if is_eligible(b)]
            available.update(b["id"] for b in entry["bullets"])
    for section in ("technical_skills", "certifications"):
        result[section] = {key: [item for item in values if is_eligible(item)]
                           for key, values in result[section].items()}
        available.update(item["id"] for values in result[section].values() for item in values)
    result["education"] = [item for item in result["education"] if is_eligible(item)]
    available.update(item["id"] for item in result["education"])
    # A recorded derived claim cannot launder a pending/excluded underlying claim.
    all_nodes = [e for section in ("experiences", "projects") for e in result[section]]
    all_nodes += [b for e in all_nodes for b in e["bullets"]]
    all_nodes += [s for section in ("technical_skills", "certifications")
                  for values in result[section].values() for s in values] + result["education"]
    while True:
        rejected = {n["id"] for n in all_nodes if n["id"] in available
                    and any(ref not in available for ref in n.get("evidence_refs", []))}
        rejected.update(b["id"] for e in result["experiences"] + result["projects"]
                        if e["id"] not in available for b in e["bullets"])
        if not rejected & available:
            break
        available -= rejected
    for section in ("experiences", "projects"):
        result[section] = [e for e in result[section] if e["id"] in available]
        for entry in result[section]:
            entry["bullets"] = [b for b in entry["bullets"] if b["id"] in available]
    for section in ("technical_skills", "certifications"):
        result[section] = {k: [n for n in values if n["id"] in available]
                           for k, values in result[section].items()}
    result["education"] = [n for n in result["education"] if n["id"] in available]
    for group in result.get("presentation_groups", []):
        group["bullets"] = [b for b in group.get("bullets", []) if is_eligible(b) and
                            all(ref in available for ref in b.get("evidence_refs", []))]
    return result


def migrate_evidence_v1(data: dict[str, Any], *, recorded_at: str) -> dict[str, Any]:
    """Explicit in-memory migration. Persistence/backup belongs to the caller."""
    validate_evidence_bank(data)
    if data.get("schema_version") == 2:
        return deepcopy(data)
    result = deepcopy(data)
    result.update(schema_version=2, sources=[], presentation_groups=[])

    def identity(prefix, value):
        return prefix + "-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]

    def attach(node, description):
        ref = "src-" + node["id"]
        result["sources"].append({"id": ref, "kind": "legacy_snapshot",
            "description": description or "Preserved v1 record; not newly verified.",
            "recorded_at": recorded_at})
        node.update(status="recorded", source_refs=[ref])

    for section in ("experiences", "projects"):
        for entry in result.setdefault(section, []):
            entry.setdefault("evidence_class", "unclassified_legacy")
            attach(entry, "\n".join(str(entry[k]) for k in ("evidence_source", "evidence_status") if entry.get(k)))
            for bullet in entry.setdefault("bullets", []):
                bullet.update(status="recorded", source_refs=entry["source_refs"][:])
                if bullet.get("evidence_status"):
                    attach(bullet, bullet["evidence_status"])
                bullet["metrics"] = [{"text": text, "status": "recorded", "basis": "unclassified",
                                      "source_refs": bullet["source_refs"][:]} for text in bullet.get("metrics", [])]
    for category, values in result.setdefault("technical_skills", {}).items():
        records = []
        for raw in values:
            text = raw
            if isinstance(raw, dict) and len(raw) == 1 and all(
                    isinstance(k, str) and isinstance(v, str) for k, v in raw.items()):
                # YAML parses unquoted "skill: explanation" as a one-key mapping.
                text = next(k + ": " + v for k, v in raw.items())
            if not isinstance(text, str):
                raise ValueError(f"technical_skills.{category}: unsupported legacy skill shape")
            node = {"id": identity("skill", category + "/" + text), "text": text}
            if raw != text:
                node["legacy_value"] = raw
            attach(node, text)
            records.append(node)
        result["technical_skills"][category] = records
    for node in result.setdefault("education", []):
        node.setdefault("id", identity("edu", str(node)))
        attach(node, "Preserved education record; credential not newly checked.")
        node["year"] = str(node.get("year", ""))
    for category, values in result.setdefault("certifications", {}).items():
        records = []
        for name in values:
            node = {"id": identity("cert", name), "name": name}
            attach(node, "Preserved credential record; current validity not newly checked.")
            records.append(node)
        result["certifications"][category] = records
    validate_evidence_bank(result)
    return result
