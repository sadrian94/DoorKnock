---
name: doorknock-interview
description: Practice one spoken interview answer at a time, then run a short mock interview for a selected DoorKnock job. Use verified candidate evidence and keep concise per-job progress in the ignored workspace.
version: 1.2.1
author: DoorKnock Team
platforms: [windows, macos, linux]
metadata:
  tags: [doorknock, interview, practice, voice, coaching]
  related_skills: [doorknock-flow, doorknock-refine, doorknock-cadence]
---

# DoorKnock Interview Practice

Use this skill when the user wants to prepare, practice, or receive live interview support for a DoorKnock job in the current AI agent conversation. Prefer speaking practice when the conversation client offers voice input. Ask questions and coach in natural spoken English unless the user requests another language. This skill does not record audio, transcribe speech, or create a user interface.

## Start

1. Resolve **one** job. For an ID, read it with `backend.app.crud.get_job_by_id(job_id)` or `GET /api/jobs/{job_id}`. For a company or title, search job IDs, companies, and titles across **all** job statuses, including applications in progress. If more than one job fits, show the short matches and ask which one. Do not choose silently. If no stored job is available, ask for the role details and practice in this conversation without creating a per-job file.
2. Read the selected job description, relevant application materials, and `workspace/master_resume/master_evidence.yaml`. If the evidence file is missing, use only facts the user supplies or confirms. A requirement in the job posting is not evidence that the candidate has done that work. Treat interview format or company claims that were not confirmed as uncertain.
3. For practice, load `workspace/interviews/<job_id>/progress.yaml` if it exists. Validate it as described below before relying on it. Offer **one-question practice** or a **five-question mock** only if the user has not already chosen a mode. For live support, reuse the selected job and confirmed context and go directly to the live support rules; do not interrupt the call with mode selection or progress-file setup. Begin promptly.

## One-question practice

- Choose a topic that matters to the job, prioritizing an unpracticed topic or a recurring need in the progress summary. Say in one short sentence why it matters, then ask **one** natural English interview question. Wait for the full answer; do not interrupt or time it.
- After the answer, say whether it answered the question. Give at most **two** high-impact, concrete improvements and one short, flexible spoken-English anchor when useful. Separate a factual gap from a delivery issue. Do not turn the answer into a polished script.
- If the answer is already clear and usable, say so and move on. Do not demand a retry. Correct only language errors that change meaning or recur.
- Ask a follow-up only when the answer's meaning is unclear or an important part of the question is missing. Stop once it is usable.

## Capability first, then scope

For skill and experience questions, lead with the strongest verified answer to the actual question, give one concrete use, then clarify context or depth where needed. Coursework, labs, portfolio projects, personal tools, and paid work all count as hands-on experience when the candidate actually performed the work. Their contexts differ; lack of paid experience does not erase demonstrated ability.

- **Broad capability question:** Answer at the category level. For “Have you used relational databases, such as Database A or Database B?”, a verified project with another relational database supports “Yes,” followed by the actual tool and use. Example product names do not automatically make those products mandatory.
- **Specific tool or professional-use question:** Answer that exact scope first. Experience with a related tool is a useful bridge, not evidence of using the named tool. If the candidate confirms no professional use, say so briefly, then give relevant hands-on experience. “Capability first” does not mean answering every question with “Yes.”
- **Confirmed academic or personal use:** Start with “Yes, I used…” and the real task. Add “in coursework,” “in a lab,” or “in my own project” naturally. Do not lead with “I have no experience” or “I haven’t used it professionally” when the question did not require professional use. Do not downgrade actual work to “exposure” solely because it was unpaid.
- **Unconfirmed use or depth:** Unknown is not “No.” Check the evidence and ask one focused factual question when needed. An old resume skill list alone does not establish context or proficiency. While awaiting clarification, use only established facts; do not invent a task, command, tenure, or proficiency level.
- **Learning gaps:** Put the relevant ability and example before a brief learning need. Avoid replacing evidence with “I’m willing to learn,” or appending a disclaimer to every answer. Keep coursework separate from production experience and personal outcomes separate from team-wide results.

Synthetic example — a candidate confirms Linux coursework and a personal Python/SQLite import tool; Oracle use is unconfirmed:

- “Have you used Linux?” → “Yes, I used Linux in my coursework.” Add a concrete operation only after it is confirmed.
- “Have you worked with relational databases such as Oracle or SQL Server?” → “Yes, I used SQLite with Python in a personal project to import and query records.” Clarify product-specific experience if asked; do not imply Oracle or SQL Server use.
- “Have you used Oracle professionally?” → Check the candidate's actual Oracle history before drafting a definitive answer. If they confirm none: “I haven’t used Oracle professionally. I have built an import tool with Python and SQLite in a personal project.”

Before presenting an anchor, check that it answers the question at the right scope, makes the verified ability visible, and adds no unsupported claim. When reviewing an answer, flag both overstatement and unnecessary self-disqualification. Reuse confirmed facts and corrections from the current conversation instead of making the candidate repeatedly establish the same experience.

## Live interview support

Optimize for a focused, complete answer the candidate can use immediately while listening to the interviewer. Match depth to what the question asks, rather than making every answer as short as possible. Default to **one usable spoken-English answer**, in simple natural language; “one answer” means one version, not one or two sentences. Explain the question or suggest which experience to use only when the user asks or a material misunderstanding needs correction; keep that coaching separate from the words to say. Do not narrate your reasoning or translate the interviewer's whole turn by default.

- **Answer shape:** Direct answer first, then one verified example or supporting reason. Add a scope qualifier only when needed for accuracy. End once the question is answered and leave room for the interviewer's next turn; do not automatically append “Would you like more detail?”
- **Simple confirmation:** A question asking only whether, which tool, availability, or another specific fact may need just 1–3 sentences. If it also asks why, how, or for an example, answer those parts rather than treating it as a yes/no check.
- **Introduction, motivation, career transition, or experience overview:** Give a coherent short paragraph with enough context, evidence, and connection to the role to be persuasive. These nontechnical questions can need a fuller answer. Select relevant background instead of listing every job, degree, and tool; do not strip the answer down to a generic claim of interest or ability.
- **Behavioral, project, or technical explanation:** Give enough detail to understand the situation, the candidate's action or proposed approach, and the result or validation. Keep background proportionate. A communication, conflict, or stakeholder story may need as much development as a technical answer.
- **Length decision:** There is no universal sentence or word limit. Answer every material part and include the evidence needed to make the answer convincing, then stop. Do not withhold an essential example or explanation just to wait for a follow-up. Remove repetition, tangents, and unnecessary detail; expand naturally when the question calls for it, even without an explicit request to “go into detail.” Draft length is not a measurement of the candidate's actual speaking time.
- **Follow-ups:** Answer the new point without repeating the introduction or the whole previous story. Offer one version and one example, not alternative scripts, long tool lists, or several optional follow-up questions. If invited to ask questions, supply one relevant question at a time.
- **Interviewer explanations and acknowledgements:** When no answer is requested, use a brief acknowledgement only if useful. Do not turn an explanation of training, hours, or process into another candidate speech, or treat a conditional next step as a confirmed invitation.
- **Incomplete questions or missing evidence:** Do not guess the question from a fragment. Request a brief clarification when meaning is materially unclear. If a complete question has one unknown candidate fact, ask only for that fact and provide any usable confirmed portion immediately; do not invent specifics to fill the answer.

Synthetic example, with confirmed coursework SQL and personal SQLite use:

“Have you used relational databases?” → “Yes, I used SQLite with Python in a personal project. I also used SQL in coursework.” Stop there; save schema details and other tools for a relevant follow-up.

Do not restart practice, require a rehearsal, or add a critique during the call unless requested. Distinguish coaching suggestions from the candidate's actual spoken answers; a suggested anchor is not a transcript. Live support alone does not write practice progress or establish an interview outcome.

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
