---
name: doorknock-refine
description: Use when the candidate wants to audit, expand, or correct the private master evidence bank, with or without a target role.
metadata:
  tags: [doorknock, master-resume, evidence, refine, audit, de-ai, socratic]
  related_skills: [doorknock-flow, doorknock-tailor, sepia-refactor]
---

# DoorKnock Refine Skill (淬金 / 事實定錨)

Use this skill to strengthen `workspace/master_resume/master_evidence.yaml`. It is the sole maintained master evidence file; tailored resumes are outputs built from it.

## Core Philosophy

1. Preserve the distinction between paid work, coursework, portfolio work, personal use, certification, and aspiration. A listed skill is not proof of production use.
2. Keep confirmed context, contribution, method, validation, outcome, and limitations. Do not invent metrics or imply a project was deployed or adopted without evidence.
3. Use categories and tags as search aids, not a fixed taxonomy. Natural wording and useful specificity matter more than a prescribed bullet formula.

---

## Operating Workflow

### Step 1: Audit the evidence
- Read `workspace/master_resume/master_evidence.yaml` and `workspace/profile.yaml`. Do not read, create, or synchronize a plaintext master-resume copy.
- For a comprehensive audit without a target role, inventory every experience, project, skill group, education item, and certification. Find contradictions, unsupported outcomes, ambiguous ownership, missing validation, and evidence-class confusion. Prioritize gaps that could change future Data/BI, Business Systems, or Operations applications.
- For a target role, map its few material requirements to specific evidence IDs or explicit gaps. A job posting states employer needs, never candidate history.
- Inspect sparse entries for purpose, personal contribution, method, checks, result, and limits. A project can need more than one bullet.

### Step 2: Resolve material gaps
- Ask a small number of focused questions at a time, starting with gaps most likely to change how the candidate is presented. Request an example or artifact before asking for metrics; do not suggest numerical answers. Continue in rounds rather than treating unanswered questions as confirmation.
- If the user provides an accessible repository, inspect code, README files, tests, or commits. Separate what those artifacts establish from what still needs user confirmation. Reading a repository does not authorize external publication or transfer of private candidate data.
- Leave an unsupported qualification as a gap. Do not turn transferable work into direct professional experience.

### Step 3: Persist and verify
- Back up `master_evidence.yaml` before changing it. Add only confirmed, reusable evidence in the existing schema. Record the source or user-confirmation context and scope of each material new claim when available; mark unresolved claims in the audit, not as verified accomplishments.
- Update only the YAML master. Check that it parses, review the changed claims against their sources, and run the repository quality gate.
- Hand off to Tailor with evidence IDs labeled direct, transferable, portfolio, or gap. Keep limitations attached to modeled results and unadopted tools.
- A comprehensive pass ends only after every experience bullet, project bullet, skill group, education item, and certification has a disposition: confirmed and revised, retained pending confirmation, or removed. Report the YAML changes and the remaining questions; pending claims are not completed verification.

Read [the detailed evidence rubric](references/refine-rubric.md) for a deeper audit. A strong entry can be brief; a project may need several lines when method and result would otherwise disappear.
