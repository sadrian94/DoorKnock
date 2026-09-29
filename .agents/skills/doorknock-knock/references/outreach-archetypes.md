# DoorKnock Outreach Archetypes & Character Limits (叩門話術矩陣)

This reference defines the 4 core outreach archetypes in DoorKnock, with strict character/word limits, narrative structure, and Sepia De-AI compliance rules.

---

## Strict Boundaries & Anti-Spam Constraints

1. **Human-in-the-Loop Confirmation**: All generated outreach is saved as a `draft` in DoorKnock DB (`outreach_messages`) and output markdown. The user must review, customize if desired, and send manually.
2. **Zero Hallucination Anchor**: Every metric, achievement, and technical toolchain cited must trace directly to `workspace/master_resume/master_evidence.yaml` and `workspace/profile.yaml`.
3. **Sepia De-AI Blacklist**:
   - Strictly ban chatbot filler: *"I hope this email finds you well"*, *"I came across your profile and was impressed"*, *"I would love the opportunity to"*, *"As a passionate and results-driven professional"*.
   - Strictly ban sycophancy: Never flatter blindly; respect their time by getting straight to the technical point.

---

## 1. Archetype A: LinkedIn Connection Request Note (好友邀請隨附備註)

- **Hard Constraint**: **<= 300 Characters (including spaces)**. LinkedIn enforces a hard character ceiling for connection notes without LinkedIn Premium.
- **Goal**: Break connection friction by highlighting a shared technical interest or specific post, without pitching prematurely.
- **Structure**:
  1. *Common ground / Hook*: Mention their specific post, talk, or shared technology focus.
  2. *Punchy technical alignment*: 1 compact clause demonstrating you work in the same domain.
  3. *Zero-pressure ask*: Connect to follow their team updates or exchange insights.
- **Template Architecture**:
  > Hi [Name], saw your post on [specific topic/challenge]. Working on similar [domain] reconciliation and pipeline latency challenges locally. Would love to connect and follow your team insights.

---

## 2. Archetype B: Hiring Manager InMail / Cold Email (決策主管痛點直擊稿)

- **Constraint**: **80 - 120 Words**.
- **Tone**: Senior peer or technical consultant speaking directly to an engineering peer.
- **Three-Part Arc (Problem-First, Proof-Second)**:
  1. *Paragraph 1 (The Hook)*: Address an acute operational friction, data silo, or pipeline bottleneck typical for their team or noted in their JD/posts.
  2. *Paragraph 2 (The Proof)*: Cite one concrete, verified proof point from the master resume (e.g. automating a 7,000+ item discrepancy check or reducing manual audit cycle time).
  3. *Paragraph 3 (The Low-Friction Ask)*: A 15-minute exploratory chat or async question. Provide an easy out (no aggressive sales pressure).
- **Template Architecture**:
  > Hi [Name],
  >
  > Notice [Company] is scaling [target team/pipeline initiative]. Often that introduces severe discrepancies between [System A] and [System B] as data volumes grow.
  >
  > In my recent work, I designed automated reconciliation workflows that audited [verified metric from Master Resume, e.g. 7,000+ transaction discrepancies] and cut cycle time by [verified %]. 
  >
  > Even if you are not currently hiring for your immediate team, I would welcome 15 minutes next week to share notes on how you approach [specific technical challenge]. If you are stretched for time, no problem at all.
  >
  > Best,  
  > [Candidate Name]

---

## 3. Archetype C: Recruiter Fast-Track Ping (招募人員直通車)

- **Constraint**: **60 - 80 Words**.
- **Goal**: Move an already-submitted application from the ATS backlog directly onto the recruiter screen shortlist.
- **Structure**:
  1. *Role & Req Confirmation*: State submission for [Job Title + Req ID].
  2. *Two-Sentence Fit Anchor*: Highlight work authorization eligibility and the exact required tech stack.
  3. *Readiness Offer*: Offer to provide work samples or discuss qualifications.
- **Template Architecture**:
  > Hi [Name],
  >
  > I just submitted my application for the [Job Title] role (Req #[ID]) at [Company].
  >
  > My background anchors on [Core Tool 1, Core Tool 2] and [Domain], with [a verified work-authorization statement, if relevant].
  >
  > Happy to provide any additional project briefs or portfolio walk-throughs if helpful for your initial review.
  >
  > Best,  
  > [Candidate Name]

---

## 4. Archetype D: Peer Informational Inquiry (同儕技術交流)

- **Constraint**: **70 - 90 Words**.
- **Goal**: Learn about day-to-day engineering reality, tech stack trade-offs, and team culture.
- **Structure**:
  1. *Genuine context*: Note their work on the target team.
  2. *Specific inquiry*: Ask 1 sharp question about tooling or delivery cadence.
  3. *Informal coffee ask*: Low-pressure 15-minute chat.
