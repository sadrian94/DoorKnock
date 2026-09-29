# Gatekeeper Personas & Reconnaissance Reference (辨門人物誌)

This reference outlines the three key gatekeeper personas to scout for any target role in DoorKnock, along with recommended search parameters and hook extraction angles.

---

## 1. Persona 1: The Hiring Manager / Technical Leader (握有決策權與預算的主管)

- **Target Titles**:
  - `Engineering Manager`, `Software Development Manager`, `Director of Engineering`
  - `Lead Data Analyst`, `Analytics Manager`, `Director of Enterprise Analytics`
  - `Head of Data / AI`, `VP of Engineering / Technology`
- **Why Scout Them**:
  - They feel the day-to-day pain of understaffing, technical debt, and pipeline latency.
  - They have the authority to pull a candidate resume out of the ATS black hole.
- **Search Parameters via `linkedin-mcp-server`**:
  - `search_people(keywords="Engineering Manager [Domain Keyword]", current_company="[Company Name]", location="[Region]")`
- **Authentic Hook Angles**:
  - Recent LinkedIn posts discussing architecture migrations, data quality hurdles, or team expansion.
  - Tech talks, meetup presentations, or open-source repositories they maintain.
  - Sizing up team scale and domain friction (e.g. migrating Snowflake/dbt, handling regulatory compliance).

---

## 2. Persona 2: The In-House Technical Recruiter (把守大門的篩選官)

- **Target Titles**:
  - `Technical Recruiter`, `Senior Talent Acquisition Partner`
  - `Early Career Recruiter`, `Campus Talent Lead`, `University Relations Specialist`
- **Why Scout Them**:
  - They are measured on time-to-fill and candidate pipeline quality.
  - A crisp, relevant outreach pointing to an existing job application ID can fast-track screening.
- **Search Parameters via `linkedin-mcp-server`**:
  - `search_people(keywords="Technical Recruiter OR Talent Acquisition", current_company="[Company Name]", location="[Region]")`
- **Authentic Hook Angles**:
  - Exact job requisition ID they posted about.
  - Address work-authorization constraints only when they are relevant to the role and verified for the candidate.
  - Concise match of must-have toolchains.

---

## 3. Persona 3: The Peer / Team Incumbent (站在第一線的同袍)

- **Target Titles**:
  - `Data Analyst II`, `Software Engineer`, `Associate Consultant`
  - Current members of the target rotational program or team (e.g., `Crew Member`, `LDP Associate`)
  - University alumni or shared community members (e.g. shared local tech meetups)
- **Why Scout Them**:
  - Lowest psychological friction for informal coffee chats.
  - High fidelity insight into the team real day-to-day tech stack, interview stages, and culture.
- **Search Parameters via `linkedin-mcp-server`**:
  - `search_people(keywords="[Target Role Title]", current_company="[Company Name]")`
- **Authentic Hook Angles**:
  - Shared alma mater, shared certifications, or mutual connections.
  - Specific technical curiosity regarding their team deployment cycle or tooling choices.

---

## 4. Record Formatting Contract (Contacts Schema)

When writing discovered gatekeepers into DoorKnock DB (`contacts` table):

| Field | Type | Description |
|---|---|---|
| `job_id` | `TEXT` | Target Job ID in DoorKnock |
| `name` | `TEXT` | Full Name |
| `role_title` | `TEXT` | Current Role Title at Company |
| `contact_type` | `TEXT` | `hiring_manager`, `recruiter`, `peer`, or `alumni` |
| `linkedin_url` | `TEXT` | LinkedIn Profile URL |
| `email` | `TEXT` | Work/Direct Email if publicly discovered |
| `notes` | `TEXT` | Key discussion hook, recent post reference, or shared context |
