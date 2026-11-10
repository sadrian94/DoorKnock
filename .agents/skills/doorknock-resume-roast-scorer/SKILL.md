---
name: doorknock-resume-roast-scorer
description: Use when scoring or roasting a resume for hiring appeal, ATS keyword alignment, and concrete high-impact rewrite recommendations.
metadata:
  tags: [doorknock, resume, review, roast, scoring, ats, hiring, recommendations]
  related_skills: [doorknock-tailor, doorknock-refine]
---

# DoorKnock Resume Roast Scorer

Adapted from the user-supplied `resume-roast-scorer` skill. Preserve its direct hiring-manager perspective, four weighted dimensions, keyword analysis, and complete rewrite recommendations. This is a diagnostic and proposal skill, not a candidate evidence audit or document publication workflow.

## When to Use

- Score, audit, or roast a supplied resume against a target role or JD.
- Identify weak hiring signals, ATS-oriented keyword gaps, and attention/structure problems.
- Propose stronger analytical, business-value, ownership, or senior/enterprise framing where appropriate to the target.
- Produce a Markdown report or structured JSON for an explicitly requested review workflow.

A review does not authorize editing the resume, updating evidence or application state, uploading, applying, or sending. Use `doorknock-tailor` for authorized implementation and `doorknock-refine` for confirmed evidence maintenance. Review and revision are driven by material findings, not a fixed sequence of published versions.

## Reviewer Inputs and Separation

Use only the supplied resume, target role, optional JD and target level. Do not read `workspace/master_resume/master_evidence.yaml`, `workspace/profile.yaml`, application records, prior scores, candidate memories or author defenses to perform this review. The point is what a hiring reader can see in the document, not what the author can explain privately.

For explicitly blind review, the coordinator launches a fresh reviewer context/process with those inputs and this skill only. The reviewer is already the dispatched worker and must not try to spawn another reviewer. The coordinator verifies launch separation; the reviewer discloses any received candidate-background contamination. A role switch in a conversation already containing candidate history is not independently blind. Procedural separation is not an OS access sandbox.

Extract text and inspect actual PDF pages when supplied. Text-only input permits content critique, not verified layout or PDF parser claims. Do not upload private documents to third-party services. If a review report is requested as a file, save it only in the authorized private workspace, never in tracked system files.

## Operating Workflow

### Step 1: Establish target and hiring proposition

1. Resolve the target role from the request; if inferred from the resume, state the assumption.
2. Use a supplied JD as primary criteria, separating required from preferred and duties from tool lists. With no JD, state the role archetype and provisional expectations; do not claim live market requirements without research. Research only when authorized and cite it.
3. Calibrate to the target level. Evaluate senior ownership when the target calls for it, not automatically for every entry-level analyst. Identify the first-scan hiring proposition, strongest visible evidence, and biggest obstacle.

### Step 2: Score using the source's four dimensions

Avoid politeness inflation. Use the source's task-focused 55/100 anchor as a calibration reference, not a forced score or a deduction independent of target context. Justify deductions with visible weaknesses. Personal time savings and academic work deserve scrutiny of relevance and depth, not automatic dismissal.

- **Enterprise Impact & Quantification /35**: business contribution, useful outputs, cost/cycle-time/reliability outcomes, scale and meaningful quantification rather than task completion alone. Qualitative decisions and operational improvements can be valuable; do not demand invented ROI.
- **ATS & Technical Stack Alignment /25**: target/JD tools and methods, technical depth, visible actions versus skills merely listed, and relevant keyword placement. Modern production tools matter when the role needs them, not as an arbitrary fashion checklist.
- **Seniority & Ownership Framing /25**: initiative, personal contribution, analytical choices, end-to-end responsibility and stakeholder use at the target level. Do not reward unsupported senior-sounding prose.
- **Clarity, Signal-to-Noise & Formatting /15**: immediate relevance, specific terminology, natural English, prioritization, density and readable structure; inspect the actual PDF where available.

Calculate the sum with a tool. If a required dimension cannot be assessed, disclose provisional scope or withhold a definitive total instead of treating it as passed.

Source tiers: **0–49 Critical | 50–69 Weak | 70–84 Competitive | 85–100 Strong**. The source's top tier was labelled “Top 5% / Hire-Ready”; use “Strong” because this review cannot establish applicant percentiles or hiring readiness. Scores are document-review judgments, not actual ATS results, hiring probabilities or guarantees.

### Step 3: Deliver the roast

Write 2–3 direct sentences about how the resume comes across on a first scan. Call out concrete issues such as task-list writing, personal automation obscuring business purpose, academic methods without an analytical question, low-relevance recent work dominating the page, or core credentials unsupported by visible work. Do not use contract/gig status as a personal insult. Name strong evidence worth retaining too.

### Step 4: Perform hiring and ATS keyword analysis

- **Already Present**: normally 6–8 important terms where warranted, with exact visible placements. Distinguish listed tools from demonstrated actions.
- **Missing / Recommended**: normally 5–7 useful terms where warranted, tied to the JD or explicitly provisional role expectations. Separate supported-but-obscured wording, new content needing user validation, and optional stack items. Do not manufacture gaps to meet a quota.
- Recommend natural placement in experience/projects, not just keyword stuffing into Skills. Do not automatically prescribe dbt, Snowflake, ELT, dimensional modeling or governance without target relevance.
- Distinguish extraction/format risks from semantic keyword fit. Do not claim that a keyword score proves an employer's ATS will pass the resume.

### Step 5: Propose the answer before asking questions

The deliverable is a complete useful proposal, not a questionnaire. Rank the fixes and supply proposed positioning, section/attention allocation and fully written English replacements before asking the candidate for corrections. Own the writing and selection work; the user decides what to adopt. Do not block all improvement because one SQL/BI artifact is undocumented.

Select 3–5 materially weak bullets when warranted, or all requested bullets for a full audit. For each:

- **Original**: exact quote, never a paraphrase.
- **Senior Rewrite**: strong, role-appropriate analytical/engineering wording that makes contribution, output and business use legible. Do not just swap synonyms in the same weak structure.
- **Feedback**: 1–2 specific sentences explaining the presentation problem and improvement.

Keep the core truth intact in supported rewrites. Do not invent tools, numbers, employer-wide savings, adoption, production scope, approval authority or outcomes. Where stronger content requires unknown facts, still supply a fully written illustrative option in a separate **Proposed enhancement — user to validate** block with a short list of new assumptions. Prefer concrete prose without arbitrary invented metrics. Do not interrupt every line with caveats or require the user to originate a story. Conditional enhancements are review proposals, not verified candidate history or submission-ready copy.

The coordinator subsequently checks adopted wording under Tailor's publication contract. Do not silently write reviewer assumptions into the evidence bank; do not use private background to dismiss a genuine missing on-page signal.

### Evaluate stronger framing clause by clause

**Unrecorded does not mean unperformed.** A resume-only reviewer can say "not demonstrated here", not that the candidate never did the work. Stay within the blind-input boundary; the coordinator, not this reviewer, handles evidence discovery and candidate confirmations.

When comparing external recommendations, **decompose each rewrite into clauses**. Separate useful professional naming or synthesis, plausible unrecorded work, and added factual claims such as numbers, tool use, authority, deployment or realized outcomes. Keep the useful direction even if one clause needs validation; do not dismiss an entire rewrite or default to weaker prose merely because the document does not establish every detail. Supply complete competitive copy, with new assumptions grouped separately for the coordinator/user, not a questionnaire.

Competitive strengthening is expected: make analytical choices, initiative, responsibility, outputs and decision use visible. Judge terms by their substance rather than whether source wording uses the same label; ordinary quality review can warrant quality-assurance framing without establishing rubric ownership. Distinguish purpose from achieved outcome, option/cost comparison from a formal financial model, and individual process improvement from employer-wide adoption. An undocumented stronger framing is a discovery opportunity, not proof of exaggeration; a conditional proposal is not yet a publication-ready fact. Retain a candid finding about the document while leaving the candidate's unrecorded capability open.

### Step 6: Return a decision and handoff

Conclude with accept / revise / substantial repositioning for the stated target, the top changes, and what wording alone cannot fix. Reviewers do not publish resumes or change a general-resume latest pointer. Report visual or evidence limitations without diluting concrete recommendations.

## Output Contract

Default: Traditional Chinese commentary and English resume copy, unless requested otherwise.

```markdown
# AI Resume Review & Audit Report

- **Target Role / Level**: [Role; supplied or assumed level]
- **JD / Artifact / Scope**: [JD present or absent; exact version; PDF/text checks]
- **Overall Score**: **[X] / 100** ([Tier; document judgment, not actual ATS result])
- **Score Breakdown**:
  - Enterprise Impact & Quantification: [X] / 35 — [reason]
  - ATS & Technical Stack Alignment: [X] / 25 — [reason]
  - Seniority & Ownership Framing: [X] / 25 — [reason]
  - Clarity & Signal-to-Noise: [X] / 15 — [reason]

## 1. The Roast
[2–3 direct sentences; strengths worth preserving]

## 2. ATS Keyword Match Analysis
### Already Present (Matched)
[Terms, locations and listed/demonstrated distinction]
### Missing (Recommended to Add)
[Priority, target basis and proposed placement; additions requiring validation separated]

## 3. Bullet Point Diagnostic & Rewrites
### Weak Bullet #1: [Topic]
- **Original**: "[Exact quote]"
- **Senior Rewrite**: "[Complete proposed copy]"
- **Feedback**: [Why this is stronger]

## 4. Recommended Resume Direction & Priority Changes
[Proposed summary/structure/selection; separate conditional enhancements if needed]

## 5. Decision & Handoff
[Decision, remaining limits, narrowly focused validation points]
```

When JSON is requested, return valid JSON with `overall_score`, `rating_tier`, `score_breakdown`, `the_roast`, `ats_keywords`, and `bullet_fixes`. Put target assumptions, recommended direction, conditional enhancements, limitations and handoff into additional explicit fields; do not disguise unknowns as facts.

## Quality Gate

Before returning: verify original quotes, score arithmetic, JD grounding versus assumptions, concrete usable replacements, selection/order advice, and actual PDF observations. Do not request a score-driven rewrite loop. Keep all candidate identifiers and examples out of this tracked skill; use only private runtime inputs.
