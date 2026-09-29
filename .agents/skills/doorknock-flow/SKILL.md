---
name: doorknock-flow
description: Master orchestrator for the DoorKnock job application and outreach lifecycle. Coordinates gatekeeper reconnaissance (辨門), Typst document tailoring (鑄磚), multi-touch cold outreach drafting (叩門), and follow-up cadence tracking (候應).
version: 1.0.0
author: DoorKnock Team
platforms: [windows, macos, linux]
metadata:
  tags: [doorknock, workflow, orchestrator, job-application, outreach, pipeline]
  related_skills: [doorknock-scout, doorknock-tailor, doorknock-knock, doorknock-cadence, doorknock-interview]
---

# DoorKnock Flow Skill (總生命週期調度)

Use this skill as the primary entry point when working on a job application opportunity in DoorKnock. It assesses the target opportunity stage and orchestrates the four dedicated skills to complete the application journey.

## Core Philosophy: The Four Pillars of DoorKnock

```text
┌────────────────────────────────────────────────────────┐
│               DOORKNOCK LIFECYCLE FLOW                 │
├─────────────────┬─────────────────┬──────────────────┬──────────────────┤
│  1. 辨門 (Scout) │  2. 鑄磚 (Tailor)│  3. 叩門 (Knock) │  4. 候應 (Cadence│
│  Target Recon   │  1-Page Typst   │  Multi-Touch DeAI│  Follow-Up Rhythm│
└─────────────────┴─────────────────┴──────────────────┴──────────────────┘
```

1. **辨門 (Scout)**: Identify the hiring manager, technical recruiter, and peers; discover their acute technical pain points.
2. **鑄磚 (Tailor)**: Generate evidence-anchored ATS resumes using the saved optional one-page preference, and De-AI Cover Letters.
3. **叩門 (Knock)**: Draft high-signal, speech-shaped outreach scripts (<300 char LinkedIn note, 80-120 word InMail/email).
4. **候應 (Cadence)**: Track application stages, calculate follow-up dates, and maintain pipeline hygiene.

---

## Operating Rules & Boundaries

1. **Separation of System and Data**: Never write candidate PII into source code or skills. All candidate facts are dynamically loaded from `workspace/profile.yaml` and `workspace/master_resume/master_evidence.yaml`.
2. **Zero Autonomous Send**: Every outreach message and job application must be reviewed and executed by the human user.
3. **Fail-Closed Verification**: Before declaring an opportunity ready, verify:
   - Tailored PDF compiled cleanly to 1 page.
   - Outreach drafts obey character/word limits.
   - Contacts and drafts are persisted in DoorKnock DB.

---

## Step-by-Step Flow Execution

### Interview practice route

When the user asks for interview practice, invoke **`doorknock-interview`** and keep the exercise in the current agent conversation. If no job was named, that skill asks which job or role to use. This route takes precedence over job intake, scouting, tailoring, outreach, and cadence steps below. Practice itself does not advance an application stage, schedule an interview, send outreach, or add a timeline event. Only user-confirmed real-world events go through `doorknock-cadence` for tracking.

### Step 1: Job Intake & Status Audit
- If provided a `job_id`:
  - Fetch job details via `GET /api/jobs/{job_id}`.
- If provided a new URL or raw text:
  - Import the job into DoorKnock DB via `POST /api/jobs/import` or CLI.
- Inspect the current assets:
  - Are contacts present? (`job.contacts`)
  - Are tailored PDFs present? (`job.artifacts` or `workspace/applications/...`)
  - Are outreach drafts present? (`job.contacts[].messages`)
  - What is the current application stage? (`job.application.current_stage`)

### Step 2: Pillar 1 — 辨門 (Target Reconnaissance)
- If `job.contacts` is empty:
  - Invoke **`doorknock-scout`**.
  - Query `linkedin-mcp-server` to discover the hiring manager, recruiter, and peer.
  - Save contacts into DB and write `gatekeeper-recon.json`.

### Step 3: Pillar 2 — 鑄磚 (Frictionless Proof)
- For each requested document type that does not exist:
  - Invoke **`doorknock-tailor`** for that type only.
  - Ingest target JD and extracted pain points.
  - Dynamically budget Hero Role vs. Supporting Roles.
  - Compile its PDF via Typst and verify the result before publishing its independent version. Resumes must fit one page only when the saved preference requires it; cover letters remain one page.

### Step 4: Pillar 3 — 叩門 (Multi-Touch Outreach Drafting)
- If outreach drafts do not exist:
  - Invoke **`doorknock-knock`**.
  - Draft LinkedIn connection request note (<= 300 chars).
  - Draft Hiring Manager InMail / Cold Email (80-120 words).
  - Draft Recruiter Fast-Track screen note (60-80 words).
  - Save to DB `outreach_messages` and `outreach-drafts.md`.

### Step 5: User Action Gate & Pillar 4 — 候應 (Cadence & Ledger)
- Present the prepared package to the user:
  - Download links for Resume & Cover Letter PDFs.
  - Ready-to-copy Outreach scripts with character counts.
- Wait for user confirmation that application was submitted and outreach was sent.
- Once confirmed:
  - Invoke **`doorknock-cadence`** to transition application stage to `knocked` or `applied`.
  - Automatically compute `next_followup_date` (Day +4~5).
  - Log event to `timeline_events`.
