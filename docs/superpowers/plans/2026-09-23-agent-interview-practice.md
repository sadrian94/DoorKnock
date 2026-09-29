# DoorKnock Agent Interview Practice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user practice spoken interview answers with the DoorKnock agent, one question at a time, then move into a five-question mock interview.

**Architecture:** One new agent skill defines the conversation flow and a small YAML progress summary in Git-ignored `workspace/`. Existing DoorKnock skills route interview-practice requests to it. No frontend, backend endpoint, audio service, database table, or general-purpose persistence library is needed.

**Tech Stack:** Markdown agent skills, existing DoorKnock job/evidence read paths, YAML in `workspace/`.

**Spec:** `docs/superpowers/specs/2026-09-23-agent-interview-practice-design.md`

## Global Constraints

- Keep real candidate facts and practice summaries in Git-ignored `workspace/`; tracked files use synthetic examples only.
- Use natural spoken English unless the user asks for another language. Ask one question at a time.
- Save a brief progress summary, never verbatim answers, transcripts, or raw audio.
- Do not change application stages or send, schedule, or update anything external during practice.
- Do not assess pronunciation, pace, or tone unless the current interface actually supplies suitable audio information.
- Run `uv run pytest tests` before concluding; use repo-local cache and base temp paths on this Windows workspace if needed.

## Review Focus

1. An ambiguous job name must lead to a choice, not an arbitrary match.
2. A disputed speech transcript must be clarified before using it as evidence or saving a summary.
3. A malformed progress file must remain untouched; practice can continue in conversation.
4. A mock stopped early must review answered questions only.
5. A text-only conversation must not be described as audio heard by the agent.

---

### Task 1: Add the interview skill

**Files:**
- Create: `.agents/skills/doorknock-interview/SKILL.md`

**Interfaces:**
- Reads: `backend.app.crud.get_job_by_id(job_id)` or `GET /api/jobs/{job_id}`, `workspace/master_resume/master_evidence.yaml`, and optional `workspace/interviews/<job_id>/progress.yaml`.
- Writes: only `workspace/interviews/<job_id>/progress.yaml` after a completed practice answer or mock review.

- [ ] **Step 1: Check the current behavior.** Search existing DoorKnock skills for an interview practice flow. Confirm none defines one-question coaching, a five-question mock, or a per-job practice summary. This is the baseline the new skill must improve.

- [ ] **Step 2: Write `SKILL.md` with the full minimal contract.** Use frontmatter like neighboring DoorKnock skills and these sections: Start, One-question practice, Mock interview, Progress summary, Evidence rules, Limitations. Put the following rules in the corresponding sections:

```text
Start: Resolve one DoorKnock job. Use get_job_by_id when the ID is known. For a name, search jobs across all statuses using read-only id/company/title fields; if more than one matches, ask which job. Read the job description and verified candidate evidence. Load any matching progress summary. If neither a job nor user-provided role details are available, ask for them.
One-question practice: Choose a relevant unpracticed or difficult topic, explain briefly why it matters, ask one English question, and wait. After the answer, state whether it addressed the question, give at most two actionable improvements, and offer one short natural spoken anchor. If it is usable, move on; if a material phrase may have been mistranscribed, clarify it first.
Mock interview: Ask five questions one at a time: motivation, relevant evidence, a behavioral example, a role scenario, and candidate questions or closing. Do not coach between questions. On completion or stop, review only answered questions and suggest up to three next drills. Allow pause, skip, repeat, and stop.
Evidence: Separate job requirements from candidate experience. Use verified facts only for example answers. Ask for a real example when evidence is missing. Do not give numerical scores or hiring predictions. Correct only high-impact or recurring language problems.
Limitations: Use voice input when the conversation client offers it. Speech-derived text does not prove the agent received audio. In text-only mode offer the same practice by text, without claims about pronunciation, pace, or tone.
```

- [ ] **Step 3: Include the progress format in the same skill.** Use only these fields; keep all list entries short paraphrases. Validate that `<job_id>` contains only letters, digits, `_`, or `-` before using it as a directory name; confirm the YAML's `job_id` matches the selected job. On malformed or mismatched existing YAML, leave it untouched and continue with an in-conversation summary. For a valid update, write a temporary sibling file, parse it back, then replace the target.

```yaml
job_id: "synthetic-job-001"
updated_at: "2026-09-23T15:00:00Z"
practiced_topics: ["motivation"]
strengths: ["Connected prior operations work to the role"]
practice_needs: ["Give the result sooner in behavioral examples"]
next_topics: ["behavioral example: investigating a discrepancy"]
```

- [ ] **Step 4: Check the skill against synthetic conversations.** Use invented job and candidate facts, with no real candidate records: (a) one answer that is already usable; expect no forced retry, (b) a mock stopped after two answers; expect no coaching between questions and a review of two answers, (c) a corrected transcription or malformed summary; expect clarification or preservation before persistence, (d) two jobs with the same name; expect a choice before practice, (e) text-only input; expect no claim about hearing audio. A live microphone check is separate and must be reported as untested unless run in voice chat.

- [ ] **Step 5: Commit only the new skill file.** Check the staged path and whitespace; do not include existing backend changes.

### Task 2: Route practice requests

**Files:**
- Modify: `.agents/skills/doorknock-flow/SKILL.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: `.agents/skills/doorknock-interview/SKILL.md` from Task 1.
- Produces: a clear route for interview-practice requests without a stage transition.

- [ ] **Step 1: Update the shared contract.** Change its skill count from six to seven and add a candidate-agnostic `doorknock-interview` entry describing spoken drills, mock interviews, and Git-ignored progress summaries.

- [ ] **Step 2: Update the flow skill.** Add `doorknock-interview` to `related_skills` and add this routing rule:

```text
For interview practice on a selected job, invoke doorknock-interview and keep the exercise in the agent conversation. Practice itself does not advance a stage, schedule an interview, send outreach, or add an application timeline event. Only user-confirmed real-world events go through cadence tracking.
```

- [ ] **Step 3: Check and commit.** Trace a synthetic “practice one question” request through the flow text; it must reach `doorknock-interview` without an application mutation. Check staged paths and commit only these two files.

## Final verification

- [ ] Confirm no real candidate facts appear in tracked files and the progress path is inside Git-ignored `workspace/`.
- [ ] Run `uv run pytest tests`; report the actual result and warnings.
- [ ] Report the manual synthetic conversation checks and whether a real voice-chat check was possible.
- [ ] Inspect `git status --short` and keep pre-existing backend changes separate.
