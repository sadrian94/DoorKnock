# Master evidence schema

`workspace/master_resume/master_evidence.yaml` is the private evidence bank. Identity and contact metadata remain in `workspace/profile.yaml`. Neither file belongs in Git. The executable v2 contract is in `backend/app/evidence_schema.py` (`EvidenceV2`); `EvidenceV2.model_json_schema()` exposes its JSON Schema without candidate data.

## Versions and migration

Version 1 remains readable for existing installations. Unknown versions and malformed v2 records fail with field locations. Version 2 requires `sources`, `experiences`, `projects`, `technical_skills`, `education`, and `certifications`; `presentation_groups` defaults to an empty list. Additional natural-language fields are preserved.

`migrate_evidence_v1(data, recorded_at="YYYY-MM-DD")` returns an upgraded copy without writing files. The caller must back up the exact original bytes, validate the result, and replace the file atomically. It preserves experience/project/bullet IDs, original wording, tags and evidence notes, converts skill and credential strings into records with persistent IDs, and wraps old metric strings. Unquoted legacy `skill: explanation` mappings become text with the original mapping retained in `legacy_value`. Calling the migration on v2 returns an unchanged copy.

Migration assigns `recorded`, not `confirmed`. Its `recorded_at` date records the migration; it does not establish when a fact was verified. Review existing pending qualifications individually before using the upgraded bank. Migration cannot infer grouping, official titles, metric units, adoption, current certification validity, or a missing confirmation.

## Records, sources and status

Every engagement, project, bullet, skill, education item, and certification has an immutable `id`, `status`, and nonempty `source_refs`. IDs are unique across the bank, including sources and presentation views. Skills remain grouped by category; certifications retain their grouping keys, with objects rather than strings as items.

| Status | Meaning | Selection |
| --- | --- | --- |
| `recorded` | Preserved evidence; not independently reverified during migration | Available with its original limitations; claim review required |
| `confirmed` | Explicitly supported by the cited source for its stated scope | Available; claim review still required |
| `pending_confirmation` | Material part of the claim remains unresolved | Excluded from the usable index |
| `excluded` | Retained for history but unavailable for use | Excluded from the usable index |

Sources have `id`, `kind` (`legacy_snapshot`, `user_confirmation`, or `artifact`), and a description. Optional `confirmed_at`, `observed_at`, and `recorded_at` dates use `YYYY-MM-DD`; `revision` can identify an inspected commit or artifact version. Keep the original source or confirmation context verbatim in the description or existing evidence fields. Never manufacture a date, artifact, or confirmation. A source supports only the scope actually described.

Metrics have their own `status`, `source_refs`, `text`, and `basis`: `measured`, `candidate_estimate`, `modeled`, `context`, or `unclassified`. Optional `value`, `unit`, `scope`, `observed_at`, `revision`, and `limitations` retain detail when known. Unclassified legacy data must not be silently promoted to measurement. Personal estimates remain personal; modeled portfolio outcomes remain modeled. A pending metric cannot be made usable by repeating its number in the same bullet's text.

## Presentation views

`experiences` contains real engagements. A `presentation_groups` record has an ID, a `heading`, `member_ids` referencing those engagements, and optional derived bullets. Each derived bullet cites original member bullet IDs through `evidence_refs`. It is excluded if any cited evidence is unavailable. References cannot be circular.

The group is a selection/presentation view, not another employer or a new source of accomplishments. Current resume output retains the original employer/title/date/location rows; introducing a shared visual heading would require template support. Do not attribute one platform's duties to another. A group can retain `legacy_presentation` metadata without making that metadata employment evidence.

## Tailoring and publication

- The complete YAML, including notes and limits, remains in prompt context. The usable evidence index excludes pending/excluded records and derived references to them. It includes stable IDs for skills, education and certifications. V1 positional skill references remain available only for v1 banks.
- V2 authored documents require `keyword_alignment` and `claim_review`; a `needs_revision` review stops publication. Older v1 packages keep the existing explicit `not_reviewed` compatibility path.
- V2 numeric claims require a `claim_evidence` object **inside the resume or cover-letter payload**. Keys identify output paths; values cite specific eligible bullet, skill or credential IDs. Work/project bullet references must belong to that same engagement/project. Parent entry IDs support their identity dates/name only, never all child metrics. Derived claims are constrained by the numeric evidence available along their reference chain.
- Numeric support uses eligible claim/metric content, not source dates, internal IDs, evidence-status notes, or tailoring guidance. Exact employers, titles, dates, locations and degrees still undergo identity checks.
- References and numeric checks do not prove faithful paraphrasing. Claim review must still check units, scope, personal estimates, deployment/adoption, domain and authority. Preserve original limitations even when a number passes.

Example fragment for a synthetic resume:

```json
{
  "summary": "Prepared reports for 7 teams.",
  "claim_evidence": {
    "summary": ["claim-team-reporting"],
    "experiences/0/bullets/0": ["claim-team-reporting"]
  }
}
```

Supported numeric paths are `summary`, `experiences/<entry>/bullets/<bullet>`, `projects/<entry>/bullets/<bullet>`, `skills/<entry>/items`, `education/<entry>/focus`, `certifications`, and `paragraphs/<paragraph>` (all indices zero-based). Non-numeric prose still needs semantic claim review. Education identity fields are checked directly against their source records; optional focus claims must remain within the matching education record. Resume alignment/review sections include `summary`, `experiences`, `projects`, `skills`, `education`, and `certifications`; letters use `paragraphs`. Existing published documents and their evidence fingerprints are not rewritten by migration.
