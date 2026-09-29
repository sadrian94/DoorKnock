# DoorKnock agent interview practice

## Purpose and scope

DoorKnock should help a candidate start speaking practice when they do not know which interview question to choose or whether an answer worked. Practice happens in the existing AI agent conversation, with voice as the primary input when the conversation client supports it. There is no frontend, audio service, or backend API in this design.

The first release supports two modes for one selected DoorKnock job: one-question practice and a five-question mock interview. The agent keeps questions and coaching in natural spoken English unless the user requests another language. Short setup and explanations may follow the user's preferred language. The agent asks one question at a time and moves on once an answer is clear and usable.

## Components

1. **`doorknock-interview` agent skill.** A repository skill under `.agents/skills/doorknock-interview/` defines mode selection, question choice, coaching, fact checks, and progress updates. It works through normal agent conversation; it does not call a speech API or assume that it can access an audio file.
2. **Read-only source context.** The skill uses the selected job's description and application materials, plus `workspace/master_resume/master_evidence.yaml` and profile data when needed. Candidate facts remain in `workspace/`. A claim in a job description is a role requirement, not evidence that the candidate has done it. Company research and guessed interview formats must be labeled as such.
3. **Per-job progress summary.** The agent writes `workspace/interviews/<job_id>/progress.yaml`, where `<job_id>` is the existing DoorKnock job identifier. The file is Git-ignored with the rest of `workspace/`. It records `job_id`, `updated_at`, practiced question topics, concise strengths, recurring practice needs, and suggested next topics. It does not contain verbatim answers, transcripts, raw audio, or invented experience. The agent may update it after each completed practice question or mock interview without asking again, because the user has approved storing summaries.

The first release does not change application stages, send messages, schedule interviews, or write to external trackers. It does not add a dedicated interview table.

## Conversation flow

### Start or resume

The user names or selects a DoorKnock job and requests interview practice. The agent loads the relevant job and any existing progress summary, offers **one-question practice** or **mock interview** if the user did not specify a mode, and begins promptly. If it cannot identify a unique job, it asks which job to use. If no progress exists, it creates it after the first completed question.

### One-question practice

The agent chooses a question by weighing the job's main requirements, likely interview stage if confirmed, unpracticed topics, and recurring needs in the progress summary. It asks the question in English and waits for the user's spoken answer. It does not interrupt, time, or grade speech while the user is answering.

After the answer, the agent gives a compact response: whether the answer addressed the question, one or two high-impact improvements, and one short spoken-English anchor the user could actually say. It distinguishes factual gaps from delivery issues. If the meaning is unclear, it asks one focused follow-up; if the answer is already usable, it says so and offers the next question. It does not insist on repetition or rewrite the candidate into a polished script.

### Mock interview

The agent asks five questions one at a time, covering motivation, relevant evidence, a behavioral example, a role-specific scenario, and the candidate's questions or closing. It can adapt the order to the job and confirmed interview stage. During the mock, it behaves as interviewer and withholds coaching until the five questions are complete or the user stops. The review identifies up to three recurring strengths or needs and proposes the next one-question drills. The user can pause, skip, repeat a question, or stop at any point; a stopped mock receives a summary based only on answered questions.

## Evidence and feedback rules

- Use only verified candidate evidence for example answers. When a useful example is missing, ask for the candidate's real example or say that the evidence is not established. Do not turn coursework, portfolio work, or transferable operations experience into unsupported production experience.
- Treat the speech transcript supplied by the conversation client as potentially imperfect. If recognition changes a material fact or makes a sentence unclear, ask the user to clarify before judging or saving that point.
- Coach for relevance, evidence, clarity, and natural speech. Give actionable observations, not numerical scores or invented hiring predictions.
- Keep practice in the user's own voice. Offer short anchors and flexible phrasing, not memorized paragraphs. Correct only language errors that materially affect meaning or recur.
- Progress notes summarize practice, not the candidate's complete answer. User corrections override earlier summaries.

## Failure handling and boundaries

If voice input is unavailable in the current conversation client, the agent explains that spoken practice needs a voice-capable client and offers the same one-question flow through text. If a job or evidence source cannot be read, the agent states what is missing and can practice from user-provided job details, clearly marking that context as unverified. If a summary file is unreadable or malformed, the agent preserves it and starts a fresh in-conversation summary rather than overwriting it blindly.

The agent does not claim to assess pronunciation, pace, or tone unless the current interface actually supplies suitable audio information. It does not retain audio by default. Full transcripts and recordings are outside the first release and require a separate design and explicit user choice.

## Acceptance criteria

1. Given a selected job and verified evidence, the agent can start one-question spoken practice without a frontend change and explain why that question matters.
2. Each completed answer gets at most two high-impact improvements, grounded in what the candidate said and what the job asks for; a usable answer is allowed to stand.
3. A five-question mock asks one question at a time and defers coaching until completion or user stop.
4. A later conversation can read the per-job summary and prioritize a previously difficult topic without re-reading or storing full transcripts.
5. Missing or uncertain candidate facts stay labeled; no candidate PII enters tracked source, skills, documentation, or synthetic tests.
6. The design can be verified with synthetic job and candidate fixtures, a resume-from-summary scenario, a speech-recognition correction scenario, and the repository's required test suite.
