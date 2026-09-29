---
name: doorknock-knock
description: Draft high-conversion, low-friction outreach scripts across LinkedIn and email for gatekeepers (Hiring Managers, Recruiters, and Peers) using Sepia De-AI standards. Enforces strict character and word limits with zero autonomous sending. (Pillar 3: 叩門)
version: 1.0.0
author: DoorKnock Team
platforms: [windows, macos, linux]
metadata:
  tags: [doorknock, knock, outreach, linkedin, cold-email, de-ai, networking]
  related_skills: [doorknock-flow, doorknock-scout, doorknock-tailor, sepia-hemingway]
---

# DoorKnock Knock Skill (叩門)

Use this skill to draft personalized, multi-touch outreach scripts across LinkedIn connection requests, InMails, recruiter follow-ups, and cold emails.

## Core Philosophy

1. **Problem-First, Proof-Second (以痛點開道，以實證立信)**:
   - Never begin with "I am writing to express my interest in..." or self-congratulatory summaries.
   - Begin with the recipient acute operational, technical, or data governance challenge identified during reconnaissance or in the JD.
   - Frame the candidate verified master resume achievements as the active, demonstrated solution.
2. **Sepia De-AI Writing Mandate**:
   - Strictly ban conversational chatbot filler (*"I hope this email finds you well"*, *"thrilled to apply"*, *"esteemed company"*).
   - Enforce speech-shaped syntax and sentence length variety (The Read-Aloud Test).
   - Apply the **74/18/8 Rule** (74% replace / 18% delete / 8% insert) to cut fluff and prioritize active verbs.
3. **Hard Boundaries**:
   - **Zero Autonomous Send**: All messages are drafted into `workspace/applications/<folder>/outreach-drafts.md` and saved to DoorKnock DB `outreach_messages` with status `draft`. The user reviews, copies, and sends manually.
   - **Strict Character & Word Caps**:
     - LinkedIn Connection Note: **<= 300 characters** (including spaces).
     - Hiring Manager InMail / Cold Email: **80 - 120 words**.
     - Recruiter Screen Ping: **60 - 80 words**.
     - Peer Coffee Chat: **70 - 90 words**.
   - **Zero PII Leaks**: The skill template remains candidate-agnostic; all candidate names and links resolve dynamically from `workspace/profile.yaml`.

---

## Workflow Steps

### Step 1: Input Ingestion
- Retrieve target contact details from DoorKnock DB (`contacts` table) or `gatekeeper-recon.json`:
  - Contact Name, Title, Type (`hiring_manager`, `recruiter`, `peer`), and identified discussion hooks.
- Retrieve candidate factual anchors from:
  - `workspace/profile.yaml` (Name, contact, LinkedIn URL, work authorization status).
  - `workspace/master_resume/master_evidence.yaml` (Confirmed metrics, tools, and employer track record).

### Step 2: Draft Across Archetypes
Generate tailored drafts for the appropriate channels based on available contact points:

1. **LinkedIn Connection Note** (<= 300 characters):
   - Hook + 1 compact technical proof point + low-pressure request to connect.
2. **Hiring Manager Outreach** (80 - 120 words):
   - Paragraph 1: Specific team friction or scaling challenge.
   - Paragraph 2: Verified proof point from Master Resume demonstrating past solution.
   - Paragraph 3: Low-friction ask for 15-minute sync or async technical exchange.
3. **Recruiter Application Fast-Track** (60 - 80 words):
   - Confirmation of submission for [Job Title + Req ID] + Work authorization + Core tech stack alignment.
4. **Peer Informational Inquiry** (70 - 90 words):
   - Shared engineering context + specific inquiry on team cadence/tooling.

### Step 3: De-AI & Limit Validation
- Verify character count for LinkedIn Connection note is `<= 300`.
- Verify word counts for email/InMail drafts fall within target ranges.
- Scan for banned filler words (`"hope this finds you well"`, `"thrilled"`, `"foster"`, `"elevate"`).

### Step 4: Persistence to DoorKnock DB & Local Workspace
- Save drafts to DoorKnock DB:
  - `POST /api/jobs/contacts/{contact_id}/messages`
  - Payload:
    ```json
    {
      "channel": "linkedin_connect",
      "archetype": "pain_point_solution",
      "body": "<Drafted text>",
      "status": "draft"
    }
    ```
- Write all drafts to a clean Markdown file:
  `workspace/applications/YYYY-MM-DD-[company]-[position]/outreach-drafts.md`

### Step 5: User Presentation
- Output the drafted scripts directly in the chat with clear copy-paste blocks and character/word counters.
- Provide clear next instructions for user execution.
