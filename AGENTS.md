# DoorKnock agent contract

Read this file before changing this repository or handling a DoorKnock job application. It applies to every agent working here. Follow the user's current request first, then the relevant skill under `.agents/skills/`. Use `README.md` for orientation and `workflow.md` for the longer product manual. If a skill or older manual implies a broader action than the user requested, keep the narrower scope.

## What DoorKnock is

DoorKnock is a candidate-agnostic, local job application and document tailoring system. The tracked repository is reusable **system** code; private candidate facts and application records are **data**. Keep that boundary intact in code, tests, prompts, documentation, and agent output.

## Start each task

1. Identify the requested outcome and whether the user wants a review, a draft, a local edit, or an external action. A request to review or assess does not authorize editing, importing, applying, sending, or changing an application stage.
2. Inspect the relevant files and current Git status. Preserve pre-existing changes and untracked files. Change only what the task needs; do not silently clean or overwrite another agent's work.
3. Select the narrowest relevant DoorKnock skill from the routing table below and read its `SKILL.md`. Use `doorknock-flow` for an explicitly requested end-to-end application workflow, not as a reason to run every phase for a focused request.
4. Establish the source for each material fact. Keep verified candidate evidence, employer requirements, research, and inference separate. Ask for missing facts only when they block the requested work.
5. Complete the authorized work, verify the actual result, and report what changed, what was checked, and any remaining limitation. Do not claim a stage, message, interview, or application happened merely because an artifact was prepared.

## Route by user intent

| Request | Skill | Boundary |
| --- | --- | --- |
| Audit or improve candidate evidence | `doorknock-refine` | Update `workspace/master_resume/master_evidence.yaml` only with confirmed claims; preserve a backup. |
| Research a role, employer, or contact | `doorknock-scout` | Verify current role and source identity. Research alone does not import a job or save contacts. |
| Tailor or review a resume or cover letter | `doorknock-tailor` | A review is diagnostic only. An edit must stay within the requested content or layout scope. |
| Draft outreach or a follow-up message | `doorknock-knock` or `doorknock-cadence` | Produce a reviewable draft; do not send it. |
| Review or update application history | `doorknock-cadence` | Read freely; write only user-confirmed events and outcomes to the existing record. |
| Practice interview answers | `doorknock-interview` | Keep practice in the agent conversation. Practice does not change application state. |
| Run the full application journey | `doorknock-flow` | Check each phase against the user's authorization and the current record before acting. |

Read a relevant skill directly from `.agents/skills/<name>/SKILL.md`. If a named skill is unavailable, say so and continue only with steps whose rules are clear from this contract and the user's request. Do not invent a workflow or claim a tool was used.

## Data and privacy boundaries

- `workspace/profile.yaml` holds candidate identity, contact details, and personal URL metadata. `workspace/master_resume/master_evidence.yaml` is the maintained source for candidate experience, education, skills, projects, and claims. `workspace/applications/` holds private tailored outputs; `workspace/interviews/` holds brief practice progress.
- `data/jobs.db` holds local jobs, contacts, outreach drafts, applications, and timeline events. It is application state, not a second authority for candidate accomplishments. Both `workspace/` and `data/` are Git-ignored private data.
- Never put real candidate names, phone numbers, personal emails, social URLs, specific employment or degree history, or private metrics in tracked code, prompts, skills, configuration, docs, examples, or tests. Use abstract placeholders and synthetic fixtures. Resolve candidate details dynamically at runtime.
- Do not copy raw personal emails, recipient lists, subject lines, message bodies, or source URLs into a new endpoint or database intake design without the user's explicit request for that data flow. Keep private data local and avoid unnecessary retention.
- A job description states employer needs; it does not establish candidate experience. Research and recon may guide emphasis but cannot create candidate facts. Do not turn coursework, portfolio work, or transferable skills into unsupported production or domain experience.

## Action and state gates

- Reading, researching, reviewing, and preparing local drafts are allowed within the requested scope. Import a job or persist research only when the user asks to add or save it. Do not treat a job alert or repost as a verified live opening; check the official employer or requisition when availability matters.
- Never apply for a job, upload a document, send an invitation or message, contact a recruiter, or change an external tracker on the user's behalf unless the user explicitly authorizes that action. A finished draft is not authorization to send.
- Update an existing DoorKnock application only from a user-confirmed real-world event. Before writing, identify the correct record and inspect its present stage and timeline. Preserve confirmed dates and history; do not infer a screen, interview, rejection, ghosting, or offer from elapsed time or a drafted message.
- When a request says “review,” give findings first. If the user asks for layout only, keep verified experience wording intact. When the user requests a correction to a known record, make the authorized local correction without adding invented stages.
- Before replacing a tailored document, follow `doorknock-tailor`'s version and publication contract. Generate and stage only the requested type, check its PDF for one page, selectable text, required sections, and visual readability, then publish under its own `resume/vNNN` or `cover-letter/vNNN` series. Preserve prior published versions.
- Interview practice uses one question at a time unless the user chooses a mock. Store only the concise progress allowed by `doorknock-interview`. Do not claim to assess pronunciation, pace, or tone from text alone.

## Engineering workflow and quality gate

- Keep implementation changes small and candidate-agnostic. Use synthetic test data only. Do not create a new feature, API, table, or external integration as an incidental part of a document or workflow request.
- Before concluding a repository change or committing, run the full test suite from this checkout:

  ```powershell
  uv run pytest tests
  ```

- If Windows cache or temporary-directory permissions prevent a normal run, use a writable repository-local UV cache and pytest base temp, then report the exact command and result. Do not confuse an environment setup failure with a product test failure.
- The PII guard in `tests/test_pii_leak_guard.py` is part of the suite. Also check the relevant artifact directly: inspect document output, changed application record, or affected UI as appropriate. Test counts may change; require a passing current suite rather than a fixed number of tests.
- Before a commit, inspect the diff and stage only files the user asked to include. Do not discard or commit unrelated pre-existing changes.
