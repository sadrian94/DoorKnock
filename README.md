# DoorKnock

DoorKnock is a local-first workspace for organizing a job search: track applications, research roles and contacts, prepare evidence-based documents, and manage outreach drafts and follow-ups.

## What it does

- **Track applications:** Keep job records, contacts, stages, and follow-up history in a local SQLite database.
- **Analyze and tailor:** Compare a job description with candidate evidence and generate resume or cover-letter documents with Typst.
- **Prepare outreach:** Research decision-makers, draft contact messages, and track follow-up cadence. DoorKnock prepares drafts; it does not send messages.
- **Use an AI provider:** Choose Gemini or Codex in Settings for AI-assisted analysis and drafting.

## Workflow

The candidate workflow has five stages. The `doorknock-flow` agent skill coordinates them.

1. **Refine evidence** — maintain accurate, reusable candidate facts.
2. **Scout** — research the employer, role, and relevant contacts.
3. **Tailor** — prepare documents grounded in candidate evidence.
4. **Knock** — draft concise, role-specific outreach.
5. **Track cadence** — record confirmed events and plan follow-ups.

## Data and AI privacy

The application database (`data/`) and candidate workspace (`workspace/`) stay on your machine by default and are excluded from Git. AI-assisted operations send relevant job and candidate context to the provider you select—Gemini or Codex/ChatGPT. Review the provider's data-handling terms before using real candidate information. Never commit `.env`, `workspace/`, or `data/`.

## Quick start

### Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node.js and npm (to build the frontend)
- A Gemini API key or an authenticated Codex CLI account for AI features

See [Prerequisites & Infrastructure](docs/prerequisites.md) for recommended versions and optional MCP setup.

### Install and run

From the repository root:

```sh
uv sync --extra dev
```

Copy `.env.example` to `.env` and add `GEMINI_API_KEY` if you plan to use Gemini. You can use Codex instead by installing and signing in to Codex CLI, then selecting Codex in the app's Settings.

Build the frontend:

```sh
cd frontend
npm ci
npm run build
cd ..
```

Start the application:

```sh
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

## Set up your candidate workspace

Candidate-specific features use two private files:

```text
workspace/profile.yaml
workspace/master_resume/master_evidence.yaml
```

Create them locally using the examples and guidance in [Separation of System and Data](docs/code-data-separation.md). These paths are Git-ignored. The repository includes task-specific `doorknock-*` agent skills, but no separate first-run setup skill; you can initialize the workspace manually without one. A setup skill could make agent-guided onboarding easier, but is not required to run the app.

## Agent skills

The repository includes `doorknock-*` skills for evidence refinement, research, tailoring, outreach, interview practice, and application cadence. They are discovered by compatible agent tools from `.agents/skills/`.

Sepia is an optional third-party writing skill and is not bundled here. See the [installation notes](docs/prerequisites.md#2-optional-sepia-agent-skill) to install it from its upstream project.

## Development

Run the backend test suite:

```sh
uv run pytest tests
```

For a frontend development server, run `npm run dev` from `frontend/` while the backend is running; Vite proxies `/api` requests to port 8000.

## Documentation

- [Workflow operating manual](workflow.md)
- [Core philosophy](docs/philosophy.md)
- [Prerequisites and infrastructure](docs/prerequisites.md)
- [System and candidate-data separation](docs/code-data-separation.md)

## License

DoorKnock is licensed under the MIT License. See [LICENSE](LICENSE).
