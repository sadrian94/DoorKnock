---
name: doorknock-refine
description: Use for post-submission application retrospectives and proposal-first improvement of the private master evidence bank, or an explicitly requested scoped audit.
metadata:
  tags: [doorknock, master-resume, evidence, refine, audit, de-ai, socratic]
  related_skills: [doorknock-flow, doorknock-tailor, sepia-refactor]
---

# DoorKnock Refine Skill (淬金 / 事實定錨)

Use this skill to strengthen `workspace/master_resume/master_evidence.yaml`. It is the sole maintained master evidence file; tailored resumes are outputs built from it.

## Primary timing: post-submission retrospective

The normal recurring opportunity for Refine is AFTER the user confirms a real application submission. During preparation, prioritize the requested materials; do not make a broad evidence interview or full bank audit a routine prerequisite. A material unknown that changes the current document can still receive a targeted clarification. Explicit standalone audits/refinements remain supported.

Submission confirmation makes a retrospective timely; it is not automatic authorization to edit the bank, change application stage, create an event, run a background schedule, or rewrite submitted files. Do not treat generated/uploaded materials, elapsed time or a draft message as submission. If the user has already updated the application, inspect rather than duplicate the event. Apply existing Cadence gates for separately authorized record changes.

### Retrospective sequence

1. Resolve the exact job/application and inspect its current record read-only. Establish the user-confirmed submission and actual submitted document versions from the available conversation and artifact records. Preserve originals. Keep generated, submitted and latest versions distinct; do not assume the newest generated PDF was sent, or that a generated cover letter was submitted. Label unknown submitted-file identity rather than inventing it.
2. Revisit only the relevant application conversation, JD, submitted resume/cover letter and useful intermediate drafts or review findings. Use existing history/retrieval tools when available; if a transcript is inaccessible, disclose coverage and work from accessible artifacts rather than asking the user to repeat their work history. Keep private source excerpts and reports in authorized private workspace storage, never tracked system documentation.
3. Produce the analysis report and complete update proposals BEFORE any bank write. Distinguish:
   - Newly confirmed candidate facts: reusable actions, tools, decisions, outputs, context and results with exact confirmation/source pointers.
   - Existing facts poorly organized: reconstruct a richer reusable record without changing source meaning.
   - Better phrasing without new facts: retain as document/writing reference, not another accomplishment.
   - JD-specific positioning/keywords: retain with that application, not as universal candidate identity.
   - Production/review lessons: route to the appropriate skill or process, not the evidence bank.
   - Unresolved assumptions: leave pending or omit from proposed confirmed additions; a reviewer rewrite or submitted sentence is not a confirmation.
4. Return a compact report: application and submission/artifact identity; source coverage/limitations; what was learned; original-to-proposed bank changes with source basis and reuse value; writing/process lessons; and any genuinely consequential validation point. No work-history questionnaire. Do not claim an ATS pass, employer approval or effective wording from submission alone; assess preparation quality separately from later employer outcomes.
5. Present the concrete diff/proposal for approval. Only after explicit evidence-write authorization, back up and apply the supported or specifically confirmed changes using the existing schema, preserve IDs/source statements, and verify parsing and claim fidelity. A user may authorize report plus bank writes together, but never infer new facts or duplicate previously retained evidence. Report proposed, applied and unresolved items separately.

This is a retrospective of one application, not a comprehensive verification of the entire candidate record. Do not regenerate submitted documents or start a new resume version as an incidental part of the retrospective.

## Core Philosophy

1. Preserve the distinction between paid work, coursework, portfolio work, personal use, certification, and aspiration. A listed skill is not proof of production use.
2. Keep confirmed context, contribution, method, validation, outcome, and limitations. Do not invent metrics or imply a project was deployed or adopted without evidence.
3. Use categories and tags as search aids, not a fixed taxonomy. Natural wording and useful specificity matter more than a prescribed bullet formula.
4. Treat the bank as factual authority, not a complete inventory of the candidate's ability or a library of finished resume sentences. Missing detail is unknown, not absence. Discover useful work before polishing language.

## Contribution discovery and review feedback

### Open-world evidence and competitive framing

**Unrecorded does not mean unperformed.** The bank is a maintained factual record, not a ceiling on capability, responsibility or permissible professional vocabulary. Treat an absent detail as unrecorded, not disproven; reserve "did not do" for an actual contradiction or explicit candidate denial. Do not force the candidate to prove ordinary professional descriptions already supported by their actions.

When an external review offers a stronger rewrite, **decompose each rewrite into clauses** before accepting or rejecting it. Distinguish (1) professional terminology or synthesis of established actions, (2) plausible but unrecorded methods, scope or deliverables worth understanding, and (3) genuinely new quantities, authority, adoption or outcomes. A problematic clause does not invalidate the whole rewrite. Retain its useful framing, explain the exact unresolved addition, and provide a complete stronger proposal rather than retreating to the weakest recorded sentence.

Competitive strengthening is part of the task: make analytical judgment, initiative, ownership, useful outputs and decision support legible. A comparison of options, costs and constraints may support cost-benefit or trade-off analysis without that exact term appearing in the bank; determine whether the substance fits instead of requiring a formal model by name. Conversely, a spreadsheet comparison does not alone prove a financial model or an approval outcome. Distinguish a purpose ("to support authorization") from an observed result ("secured authorization"). Personal workflow improvements can be business-process contributions without team-wide rollout; describe their real use confidently without inventing adoption or expanding measured scope.

Offer the strongest coherent draft and a compact set of precise correction points first. For a consequential unrecorded detail, use a targeted interpretation check about the proposed work, not repeated "did you really do this?" questions or a work-history questionnaire. Once specifically confirmed, use it in the authorized document and retain a private confirmation pointer; updating the canonical bank still requires separate write authorization and backup. A hypothetical enhancement remains a proposal until established, but it is not a rejected direction merely because it is absent from the bank.

When a resume review exposes weak task descriptions, distinguish five causes: wording, selection/order, missing displayed evidence, missing underlying facts, and actual target mismatch. Do not send every criticism back to the candidate as a question, and do not repair factual gaps with senior-sounding language.

For each priority example, reconstruct the problem/data, personal actions and choices, methods/tools, validation or exception handling, deliverable, audience/use, and observed result/limits. Inspect already-authorized artifacts first. Present the reconstruction before any consequential clarification, following Step 2's default limit rather than conducting successive discovery rounds. A qualitative output or useful decision can establish contribution without a fabricated metric or company-wide ROI.

Keep three layers separate: confirmed facts; reviewer interpretations/recommendations; questions awaiting confirmation. A reviewer rewrite, score, or approval of document wording does not establish new candidate history. Do not persist presentation preferences or speculative outcomes as accomplishments. Use existing schema fields and preserve source context; no incidental schema expansion.

For reporting/BI targets, proactively look for an actual query-to-output workflow: data sources, SQL transformations, metric definitions, model/measures or report, validation, and intended users. Coursework and personal examples count in their real setting. A skills entry is not an artifact, but missing artifact details do not disprove capability. Where the example remains unknown, list the exact discovery question instead of repeatedly treating the same omission as a new defect.

Hand off a contribution brief, not just copied bullets: strongest supported hiring contribution, concrete action/output evidence, natural role terminology that preserves meaning, unresolved facts, and the appropriate evidence IDs. Keep reusable work detail in the bank; compose tailored wording in the document. A short fact can support a substantive sentence, and a long fact can support a concise one; sentence length is not the quality objective.

---

## Operating Workflow

### Step 1: Audit the evidence
- Read `workspace/master_resume/master_evidence.yaml` and `workspace/profile.yaml`. Do not read, create, or synchronize a plaintext master-resume copy.
- For a comprehensive audit without a target role, inventory every experience, project, skill group, education item, and certification. Find contradictions, unsupported outcomes, ambiguous ownership, missing validation, and evidence-class confusion. Prioritize gaps that could change future Data/BI, Business Systems, or Operations applications.
- For a target role, map its few material requirements to specific evidence IDs or explicit gaps. A job posting states employer needs, never candidate history.
- Inspect sparse entries for purpose, personal contribution, method, checks, result, and limits. A project can need more than one bullet.

### Step 2: Propose the reconstruction before eliciting facts
- First deliver a complete proposed reconstruction from existing authorized material. For each priority entry, show the original, proposed replacement or richer reusable record, why the old wording undersells the contribution, and which existing sources support the change. Make analytical judgment, deliverables and use legible rather than merely upgrading verbs or shortening sentences.
- Do not conduct a questionnaire about what the candidate did at work. Do not require the candidate to retell their history, populate a form, supply every method/result, or answer a series of discovery rounds before receiving useful writing. The agent owns synthesis, framing and the initial draft; the candidate corrects or adopts a concrete proposal.
- Separate supported proposed content from optional, fully written enhancements requiring validation. Give a compact assumption list beside the latter, not repeated inline caveats or a long list of placeholders. Never promote a hypothetical example to confirmed history. Do not fabricate metrics, tools, adoption or outcomes to make a proposal sound complete.
- After providing the proposal, ask at most one material clarification by default, only if it cannot be resolved from authorized material and changes the meaning or a permitted write. Prefer a precise correction prompt about the proposed content to an open-ended request for a new story. Do not turn this one-question limit into successive interrogation turns. Leave unresolved optional enhancements aside and complete supported improvements; silence is not confirmation.
- If the user provides an accessible repository, inspect code, README files, tests, or commits. Separate what those artifacts establish from what still needs user confirmation. Reading a repository does not authorize external publication or transfer of private candidate data.
- Leave an unsupported qualification as a gap. Do not turn transferable work into direct professional experience.

### Step 3: Persist and verify
- Back up `master_evidence.yaml` before changing it. Add only confirmed, reusable evidence in the existing schema. Record the source or user-confirmation context and scope of each material new claim when available; mark unresolved claims in the audit, not as verified accomplishments.
- Update only the YAML master. Check that it parses, review the changed claims against their sources, and run the repository quality gate.
- Hand off to Tailor with evidence IDs labeled direct, transferable, portfolio, or gap. Keep limitations attached to modeled results and unadopted tools.
- A comprehensive pass ends only after every experience bullet, project bullet, skill group, education item, and certification has a disposition: confirmed and revised, retained pending confirmation, or removed. Report the YAML changes and the remaining questions; pending claims are not completed verification.

## Required proposal and acceptance output

For a scoped refinement, return a small, prioritized set of complete before/after proposals, not an exhaustive gap inventory. Include the missing contribution dimension, improved reusable record, source basis, and any explicit assumption needing correction. Explain what can improve now without new facts and what remains optional. For a comprehensive audit, keep the full item inventory internally and present the highest-value proposals first rather than overwhelming the candidate with questions.

Reviewing this skill or approving the approach does not itself authorize unconfirmed claims to enter the master bank. Keep proposal drafts in authorized private workspace storage; after content approval, back up and apply only supported or specifically confirmed changes in the existing schema. Do not treat blanket wording approval as confirmation of new tools, quantities or outcomes. Preserve original source statements and IDs so future tailoring can use richer facts without copying one polished sentence for every role.

Read [the detailed evidence rubric](references/refine-rubric.md) for a deeper audit. A strong entry can be brief; a project may need several lines when method and result would otherwise disappear.
