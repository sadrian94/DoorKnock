# Architecture Guide: Separation of System and Data (系統與數據分治)

## 1. Core Architectural Philosophy

In DoorKnock, **System** and **Data** are strictly decoupled into two isolated realms:

```text
┌────────────────────────────────────────────────────────┐
│               DOORKNOCK SYSTEM (Tracked in Git)        │
│                                                        │
│  - backend/          (Engines, FastAPI endpoints)      │
│  - frontend/         (React + Tailwind UI)             │
│  - templates/        (Typst & Jinja2 layouts)          │
│  - .agents/skills/   (Agent workflows & rules)         │
│  - docs/ & tests/    (Specifications & test suites)    │
│                                                        │
│  * 100% Candidate-Agnostic, Reusable, Open-Source Ready│
└───────────────────────────┬────────────────────────────┘
                            │ Dynamic Runtime Injection
                            ▼
┌────────────────────────────────────────────────────────┐
│           CANDIDATE TRUTH DATA (Ignored in Git)        │
│                                                        │
│  workspace/                                            │
│  ├── profile.yaml                                      │
│  │   (Name, phone, email, links, project URLs)        │
│  ├── master_resume/master_evidence.yaml               │
│  │   (Full factual employment & degree history)        │
│  └── applications/                                     │
│      (Generated PDFs, Typst source, tailored metadata) │
│                                                        │
│  * Strictly Local, Zero PII Leaks, Total Privacy       │
└────────────────────────────────────────────────────────┘
```

- **System (The Engine)**: Candidate-agnostic logic, compilation pipelines, UI state machines, prompt structures, and typing contracts. Contains zero personal names, phone numbers, emails, or specific work metrics.
- **Data (The Truth)**: Candidate evidence, verified background, contact information, and output artifacts. Stored exclusively under the gitignored `workspace/` directory.

---

## 2. Five Defense-in-Depth Mechanisms to Prevent PII Leaks

To ensure no personal information accidentally leaks into the `frontend/`, `backend/`, `.agents/skills/`, or git-tracked repository, DoorKnock implements a 5-layer defense strategy:

### Layer 1: The Root Agent Contract (`AGENTS.md`)
Every autonomous AI assistant (Antigravity, Codex, Hermes, Claude) reads `AGENTS.md` at the repository root as its highest-priority operating manual before writing code.
- **Rule**: Explicitly bans hardcoding personal names, phone numbers, emails, real companies, or specific metrics into source code, prompts, configs, and skills.
- **Rule**: Mandates that all candidate facts must resolve dynamically from `workspace/`.

### Layer 2: Automated PII Leak Guard in CI / Pytest (`tests/test_pii_leak_guard.py`)
DoorKnock incorporates an automated test that runs on every local test run and CI build:
- Dynamically parses sensitive tokens from `workspace/profile.yaml` (full name, email, phone digits, personal URLs).
- Recursively scans all tracked files in `backend/`, `frontend/`, `.agents/skills/`, `docs/`, and `tests/`.
- If any tracked file contains a candidate PII token, the test **immediately fails** and prints the exact offending file and line.

### Layer 3: Abstract Schemas & Dynamic URL Registries
Instead of hardcoding personal logic in engines or prompts:
- **LLM Prompts**: Use generic schema placeholders (e.g., `<Employer Name from Candidate's Master Resume>`, `<University Name from Master Resume>`) rather than example company names.
- **Project URL Resolution**: Uses `workspace/profile.yaml` as a metadata registry. Project links are matched dynamically via name and keywords (`projects_meta`), removing all hardcoded GitHub URLs from Python code.
- **Display Naming**: System defaults to `"Candidate"` if profile metadata is absent.

### Layer 4: Synthetic Test Fixtures Mandate
Unit and integration tests must never use live candidate credentials:
- All test fixtures in `tests/` use fictional personas (e.g., `Alex Taylor`, `Jane Doe`, `alex.taylor@example.com`, `(555) 019-2834`).
- Fictional institutions and employers (e.g., `Apex Logistics`, `Global Tech University`, `Summit Commercial Property Group`) are used in compilation test suites.

### Layer 5: Git Boundary & Pre-Commit Protection
- **`.gitignore` Isolation**: The entire `workspace/` and `data/` directory trees are permanently gitignored.
- **Pre-Commit Linting**: Running `uv run pytest tests` before committing verifies that all 18+ tests pass and that zero candidate PII has leaked into git-staged files.

---

## 3. How to Set Up a New Candidate Workspace

To use DoorKnock for a different candidate:

1. Clone or copy DoorKnock repository.
2. Initialize `workspace/profile.yaml`:
   ```yaml
   full_name: "Your Full Name"
   preferred_name: "Your Preferred Name"
   email: "your.email@example.com"
   phone: "(555) 123-4567"
   location: "City, State"
   work_authorization: "<candidate-confirmed work authorization details, if applicable>"
   linkedin_url: "https://linkedin.com/in/yourprofile"
   github_url: "https://github.com/yourprofile"
   projects:
     - name: "Your Primary Project"
       keywords: ["keyword1", "keyword2"]
       url: "https://github.com/yourprofile/project-repo"
   ```
3. Place structured, evidence-backed candidate history at `workspace/master_resume/master_evidence.yaml`.
4. Run the automated check:
   ```powershell
   uv run pytest tests
   ```
5. Author the requested document as JSON under the ignored `workspace/` directory, then compile that type:
   ```powershell
   uv run python -m app.tailor.cli --job-id <JOB_ID> --document-type resume --authored-json <WORKSPACE_JSON_PATH>
   ```
   Use `--document-type cover_letter` for a cover letter. Each type is generated and versioned separately.
The engine will dynamically adapt to the new candidate's background with zero changes to source code or skills.
