---
name: doorknock-scout
description: Target intelligence and gatekeeper reconnaissance for target employers using linkedin-mcp-server. Discovers hiring managers, technical recruiters, and peers, extracts authentic hooks, and persists contacts. (Pillar 1: 辨門)
version: 1.0.0
author: DoorKnock Team
platforms: [windows, macos, linux]
metadata:
  tags: [doorknock, scout, reconnaissance, gatekeeper, linkedin, target-intelligence]
  related_skills: [doorknock-flow, doorknock-tailor, doorknock-knock]
---

# DoorKnock Scout Skill (辨門)

Use this skill to conduct reconnaissance on target companies, identify key decision-makers (Hiring Managers, Technical Recruiters, and Peers), and extract authentic hooks for high-conversion outreach.

## Core Philosophy

1. **Strategic Power Structure (辨明虛實與權力結構)**:
   - Resumes sent through public ATS portals enter an anonymous queue. Identifying and engaging the real person living with the business problem breaks informational asymmetry.
   - For every target opportunity, identify up to 3 distinct personas:
     - **Hiring Manager / Tech Lead**: Owns the team, budget, and pain points.
     - **In-House Recruiter**: Screens candidates and controls interview scheduling.
     - **Direct Peer / Alumni**: Understands daily team rhythm, tech stack, and culture.
2. **Authentic Friction over Flattery (真痛點重於諂媚)**:
   - Ground outreach in real operational challenges (e.g. data latency, reporting bottlenecks, tech stack migrations, regulatory compliance) rather than generic praise.
3. **Hard Boundaries**:
   - **Zero Autonomous Send**: NEVER send messages, connection requests, or modify external profiles autonomously. DoorKnock scouts and drafts; the user executes.
   - **Zero PII Leaks**: Never hardcode candidate PII into skills or source code.
   - **Deterministic Persistence**: Store gatekeeper profiles into DoorKnock SQLite `contacts` table and write findings to `workspace/applications/<folder>/gatekeeper-recon.json`.

---

## Prerequisites & Tools

- **`linkedin-mcp-server`**:
  - `search_people(keywords, location, current_company)`
  - `get_person_profile(profile_id)`
  - `get_company_profile(company_id)`
  - `get_company_employees(company_id)`
  - `get_company_posts(company_id)`
- **Reference**:
  - Detailed persona criteria in `.agents/skills/doorknock-scout/references/gatekeeper-personas.md`.

---

## Workflow Steps

### Step 1: Target Context & Role Intake
- Retrieve job details from DoorKnock database:
  - Read `jobs` table by `job_id` or examine target company name, title, workplace type, and job description.
- Identify the target department and keywords (e.g. "Enterprise Analytics", "Cloud Infrastructure", "Supply Chain BI").

### Step 2: Company Reconnaissance
- Query `get_company_profile` to establish official company URN, size, headquarters, and tech leadership structure.
- Check `get_company_posts` to discover recent engineering announcements, product launches, or team expansion posts.

### Step 3: Gatekeeper Discovery
- Search for the 3 key personas using `search_people`:
  1. **Hiring Manager**: `keywords="Engineering Manager [Domain]"`, `current_company="[Company]"`
  2. **Technical Recruiter**: `keywords="Technical Recruiter OR Talent Partner"`, `current_company="[Company]"`
  3. **Peer / Alumni**: `keywords="[Role Title]"`, `current_company="[Company]"`
- For top candidate profiles, inspect details with `get_person_profile`:
  - Verify current tenure and team scope.
  - Check for shared alumni ties (e.g. WGU or regional tech meetups).

### Step 4: Extract Authentic Hooks
- Identify 1-2 concrete, verifiable discussion hooks:
  - A recent post discussing architectural challenges or pipeline bottlenecks.
  - A specific repository, framework, or standard they advocate.
  - Shared professional or community context.

### Step 5: Persistence to DoorKnock DB & Local Workspace
- Record discovered contacts into DoorKnock DB via FastAPI endpoint or Python helper:
  - `POST /api/jobs/{job_id}/contacts`
  - Body:
    ```json
    {
      "name": "<Gatekeeper Name>",
      "role_title": "<Role Title>",
      "contact_type": "hiring_manager",
      "linkedin_url": "https://linkedin.com/in/...",
      "notes": "<Authentic hook and context notes>"
    }
    ```
- Save structured JSON to:
  `workspace/applications/YYYY-MM-DD-[company]-[position]/gatekeeper-recon.json`

---

## Deliverables & Next Step Handoff

Upon completing reconnaissance:
1. Provide a concise summary to the user highlighting the discovered decision-maker and the exact hook identified.
2. Signal readiness to proceed to **`doorknock-tailor`** (to align resume bullets with the team pain point) and **`doorknock-knock`** (to draft the personalized outreach messages).
