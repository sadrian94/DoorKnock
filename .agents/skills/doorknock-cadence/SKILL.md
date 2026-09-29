---
name: doorknock-cadence
description: Manage application lifecycle stages, compute multi-touch follow-up cadences, draft value-add follow-up messages, and triage stale/ghosted applications. (Pillar 4: 候應)
version: 1.0.0
author: DoorKnock Team
platforms: [windows, macos, linux]
metadata:
  tags: [doorknock, cadence, followup, pipeline, kanban, triage, tracking]
  related_skills: [doorknock-flow, doorknock-knock]
---

# DoorKnock Cadence Skill (候應)

Use this skill to maintain application pipeline hygiene, monitor follow-up schedules, draft non-spammy value-add follow-up messages, and archive stale or ghosted opportunities.

## Core Philosophy

1. **Rhythm over Randomness (進退有據，候應有時)**:
   - A single outreach touchpoint easily gets lost in a busy manager inbox. A structured 3-touch cadence doubles conversion without crossing into spam.
   - Every application in `applied` or `knocked` state must have a computed `next_followup_date`.
2. **Value-Add Follow-Ups**:
   - Strictly forbid hollow bumps (*"Just checking in"*, *"Any update on this?"*).
   - Follow-up 1 (Day 4–5): Share a tangible technical update, repo link, or brief observation on their technology domain.
   - Follow-up 2 (Day 10–12): Provide a clean, respectful closing loop acknowledging their busy priorities.
3. **Ghosting & Pipeline Hygiene**:
   - Dormant applications with zero response after 14 days should be proactively triaged and archived to `closed (ghosted)`, clearing mental clutter.
4. **Hard Stage Contracts**:
   - Terminal stage is always `closed`, never `rejected`. When a rejection occurs, transition to `closed` with outcome `rejected`.

---

## Workflow Steps

### Step 1: Pipeline Triage & Follow-up Review
- Query upcoming follow-ups:
  - Call `GET /api/pipeline/followups?days=3`
  - Identify cards where `next_followup_date` is today or overdue.
- Query stale applications:
  - Call `GET /api/pipeline/stale?days=14`
  - Identify opportunities dormant >14 days.

### Step 2: Draft Value-Add Follow-Up
- If an application is due for Follow-up 1 (Day 4–5):
  - Ingest the company original pain point and the candidate latest relevant project commit or technical tool from `workspace/master_resume/master_evidence.yaml`.
  - Draft a crisp 50–70 word value-add note connecting to that pain point.
- If an application is due for Follow-up 2 (Day 10–12):
  - Draft a polite 40–50 word close-the-loop note.
- Present drafts to the user for review.

### Step 3: Advance Stage & Log Timeline Events
- When user confirms an outreach was sent, interview scheduled, or offer received:
  - Call `PATCH /api/pipeline/applications/{application_id}/stage`
  - Payload:
    ```json
    {
      "to_stage": "recruiter_screen",
      "outcome": null,
      "note": "Recruiter scheduled 30-min phone screen for Thursday."
    }
    ```
  - The DoorKnock backend automatically creates a `timeline_event` and recalculates `next_followup_date`.

### Step 4: Stale Triage Execution
- For jobs confirmed ghosted by the user:
  - Call `PATCH /api/pipeline/applications/{application_id}/stage`
  - Payload:
    ```json
    {
      "to_stage": "closed",
      "outcome": "ghosted",
      "note": "No response after 14 days and 2 follow-ups. Archived."
    }
    ```
