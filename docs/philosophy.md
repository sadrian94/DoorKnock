# The DoorKnock Philosophy

Traditional Chinese original: [philosophy-ZH.md](philosophy-ZH.md)

> **A door will not open simply because you wait. You have to knock. But only those who bring genuine proof and sincerity can open the right door.**

---

## I. Foundational worldview: from a passive lottery to an equal exchange

The traditional job market is marked by severe information asymmetry and wasted effort:

- **The job seeker's dilemma:** Send resumes full of irrelevant history into the black hole of application systems, wait anxiously, and leave the outcome to chance—or use AI to generate piles of inflated, hollow boilerplate that impresses no one.
- **The recruiter's dilemma:** Face hundreds of nearly identical, AI-polished resumes every day and struggle to identify who can actually solve the business problems at hand.

**What DoorKnock stands for:**

Looking for work is not begging. It is an **equal exchange of value and a commercial negotiation**.

DoorKnock helps candidates reclaim the initiative. They use refined, verifiable evidence to find the right door, identify its gatekeepers, make a precise approach, and manage each next step with confidence and dignity.

---

## II. The three foundational axioms

### 1. Separate the system from the truth

- **The system should be impartial.** Code, typesetting engines, research strategies, and prompt templates are unbiased, reusable public tools. They should not hardcode anyone's personal information (zero PII) and should be suitable for open-source use.
- **The truth stays with the candidate.** The candidate's work history, metrics, repositories, and factual anchors in `workspace/` are the sole source of truth. The system must never invent facts (no hallucinations); its job is to present real evidence as clearly and compellingly as possible.

### 2. Problem first, proof second

- **Buyers do not buy your autobiography; they buy a solution to a problem.** Do not dump an unfocused history of accomplishments (anti-evidence dump).
- **Start with the other side's friction.** Every interaction and document should first identify the operational friction facing the role and its decision-makers—such as data hygiene, scale, or legacy migration. Then retrieve matching, objective evidence from the candidate's fact base to show how they can address it.

### 3. Remove the gloss; make proof frictionless

- **Reject AI-sounding prose.** Cut empty words such as *foster*, *elevate*, *tapestry*, and *seamless*. Prefer verbs, numbers, constraints, and decision logic.
- **Reduce the reader's cognitive load:**
  - A **single-page Typst resume** acts as a calling card and presents the strongest signals in ten seconds.
  - An outreach message is a **precise note under 300 characters** that respects the reader's time and gets to the point.

---

## III. The five-pillar lifecycle

DoorKnock breaks a job search into five connected stages:

~~~text
[0. Refine]  — Build an objective evidence base
      |
[1. Scout]   — Identify decision-makers and business needs
      |
[2. Tailor]  — Produce a focused, single-page resume
      |
[3. Knock]   — Start a direct, low-friction conversation
      |
[4. Cadence] — Manage follow-ups and the application pipeline
~~~

| Stage | Guiding idea | Operating principle | Example implementation |
| :--- | :--- | :--- | :--- |
| **0. Refine** | **Build a foundation** | Use Socratic questions and repository reviews to turn past work into structured facts—without exaggeration or needless self-doubt. | `master_evidence.yaml`, GitHub MCP |
| **1. Scout** | **Know both sides** | Identify the relevant gatekeepers—hiring managers, recruiters, and peers—and understand the organization's current needs before reaching out. | LinkedIn decision-maker research, in-depth job-description analysis |
| **2. Tailor** | **Fit the document to the role** | Replace fragile manual layout with deterministic, code-based compilation to produce a precise, ATS-friendly one-page resume. | Native Typst compilation pipeline, Jinja2 templates |
| **3. Knock** | **Start an equal conversation** | Get past the application-system black hole with concise, sincere outreach in plain language. | LinkedIn notes under 300 characters, 80–120-word InMail |
| **4. Cadence** | **Move at a steady pace** | Record each interaction and plan follow-ups. When there is no response, follow up with dignity or step away without draining your energy. | Kanban board, cadence state machine |

---

## IV. Engineering philosophy for the frontend and backend

DoorKnock's frontend and backend are more than a database and a display. Together, they make the job-search process deliberate and repeatable.

### 1. Backend: a deterministic proof engine

The backend follows one principle: **constrain uncertain AI generation within a deterministic engineering process that prevents data leaks.**

- **Dynamic truth injection:** The system does not embed personal data. At runtime, it loads factual files from the local `workspace/`. Keeping the engine separate from candidate evidence makes the system reusable and protects private data.
- **Friction analysis and evidence grounding:** AI modules analyze and align information; they do not invent a candidate's story. They examine the job description for technical constraints and team needs, then retrieve the most relevant real evidence from the candidate's fact base.
- **Deterministic, single-page layout:** Instead of relying on document formats with unpredictable layout, DoorKnock uses Typst's code-based compilation pipeline and strict layout constraints to produce precise, ATS-friendly one-page documents.

### 2. Frontend: a cockpit for taking the initiative

The frontend aims to **reduce decision anxiety and cognitive load so that each next step is clear.**

- **A unified pipeline and cadence board:** Turn scattered applications into a visible workflow (`Wishlist → Applied → Reached Out → Interviewing → Archive`). Candidates can see the status of each opportunity and when it is time to follow up.
- **A unified detail and tailoring workflow:** Keep job details, gatekeeper notes, resume previews, and outreach drafts together. Candidates can make decisions without switching among dozens of browser tabs, folders, and email drafts.
- **Low-friction opportunity intake:** Make it easy to capture a job opportunity and reduce the effort between finding it and starting outreach.

### 3. The shared purpose of the frontend and backend

> **The frontend gives candidates visibility and control. The backend supplies grounded evidence and reliable tools. Together, they turn a job search into an efficient, evidence-based process that preserves the candidate's dignity and agency.**

---

## V. Conclusion: the calm confidence to knock

DoorKnock does not promise miracles. It does promise that **each action is grounded in truth, and each approach is made with care and as little friction as possible**.

With refined evidence, a clear view of the people at the door, and a focused calling card in hand, a job search becomes less like passive pleading and more like a confident, mutually beneficial exchange.
