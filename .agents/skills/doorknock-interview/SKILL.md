---
name: doorknock-interview
description: Practice one spoken interview answer at a time, then run a short mock interview for a selected DoorKnock job. Use verified candidate evidence and keep concise per-job progress in the ignored workspace.
version: 1.0.0
author: DoorKnock Team
platforms: [windows, macos, linux]
metadata:
  tags: [doorknock, interview, practice, voice, coaching]
  related_skills: [doorknock-flow, doorknock-refine, doorknock-cadence]
---

# DoorKnock Interview Practice

Use this skill when the user wants to practice for a DoorKnock job in the current AI agent conversation. Prefer speaking practice when the conversation client offers voice input. Ask questions and coach in natural spoken English unless the user requests another language. This skill does not record audio, transcribe speech, or create a user interface.

## Start

1. Resolve **one** job. For an ID, read it with `backend.app.crud.get_job_by_id(job_id)` or `GET /api/jobs/{job_id}`. For a company or title, search job IDs, companies, and titles across **all** job statuses, including applications in progress. If more than one job fits, show the short matches and ask which one. Do not choose silently. If no stored job is available, ask for the role details and practice in this conversation without creating a per-job file.
2. Read the selected job description, relevant application materials, and `workspace/master_resume/master_evidence.yaml`. If the evidence file is missing, use only facts the user supplies or confirms. A requirement in the job posting is not evidence that the candidate has done that work. Treat interview format or company claims that were not confirmed as uncertain.
3. Load `workspace/interviews/<job_id>/progress.yaml` if it exists. Validate it as described below before relying on it. Offer **one-question practice** or a **five-question mock** only if the user has not already chosen a mode. Begin promptly.

## One-question practice

- Choose a topic that matters to the job, prioritizing an unpracticed topic or a recurring need in the progress summary. Say in one short sentence why it matters, then ask **one** natural English interview question. Wait for the full answer; do not interrupt or time it.
- After the answer, say whether it answered the question. Give at most **two** high-impact, concrete improvements and one short, flexible spoken-English anchor when useful. Separate a factual gap from a delivery issue. Do not turn the answer into a polished script.
- If the answer is already clear and usable, say so and move on. Do not demand a retry. Correct only language errors that change meaning or recur.
- Ask a follow-up only when the answer's meaning is unclear or an important part of the question is missing. Stop once it is usable.

## Five-question mock interview

- Act as the interviewer and ask one question per turn. Cover motivation, relevant evidence, a behavioral example, a role-specific scenario, and the candidate's questions or closing. Adapt wording and order to the job and any **confirmed** interview stage.
- Do not coach between questions. The user may pause, skip, repeat, or stop at any time. Skipped questions are not answered questions.
- If a material fact may have been mistranscribed, ask only for factual clarification and then resume the mock. This is not a coaching pause.
- After five questions, or when the user stops, review **only answers actually given**. Identify up to three recurring strengths or practice needs and suggest the next one-question drills. Do not invent responses to skipped questions.

## Progress summary

After a completed one-question answer or mock review, update only `workspace/interviews/<job_id>/progress.yaml`. The `workspace/` directory is Git-ignored. Store short paraphrases, not the candidate's full answer, a transcript, or an audio path. Use this exact shape:

```yaml
job_id: "synthetic-job-001"
updated_at: "2026-09-23T15:00:00Z"
practiced_topics: ["motivation"]
strengths: ["Connected prior operations work to the role"]
practice_needs: ["Give the result sooner in behavioral examples"]
next_topics: ["behavioral example: investigating a discrepancy"]
```

Before using an ID as a directory name, require 1–100 characters from letters, digits, `_`, or `-` only. Read YAML with a safe parser. Accept exactly these six keys: `job_id` and `updated_at` as strings; `practiced_topics`, `strengths`, `practice_needs`, and `next_topics` as lists of strings. The file's `job_id` must equal the selected job. If an existing file is malformed or mismatched, **leave it untouched** and keep a summary only in conversation until the file is repaired. For a valid update, write a temporary sibling file, parse it back to validate its shape and job ID, then replace the target. Use a current UTC ISO 8601 timestamp. A user correction replaces the corresponding summary item; it is not an additional unverified fact.

## Evidence and voice boundaries

- Use verified candidate evidence for examples. If evidence is missing, ask for the user's real example or state that it is not established. Do not describe coursework, portfolio projects, or transferable operations work as unsupported production experience.
- In either mode, clarify a material transcription uncertainty before judging or saving that point. Never turn an uncertain transcript into a candidate fact.
- Coach for relevance, evidence, clarity, and natural speech. Do not give numerical scores or hiring predictions.
- A speech-derived text message does not prove that the agent received audio. Assess pronunciation, pace, or tone only when the active interface supplies audio information that supports it. If voice input is unavailable, offer the same one-question flow in text without claiming to have heard the user.
- Practice does not change application stages, schedule interviews, send outreach, or write external trackers. Record a real interview event through `doorknock-cadence` only when the user separately confirms it happened.
