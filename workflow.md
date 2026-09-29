# DoorKnock Workflow

This guide describes the operating paths supported by the current system. Use it when working on a job opportunity in the Web UI or an agent conversation. `AGENTS.md` sets the cross-agent boundaries; the relevant `.agents/skills/doorknock-*/SKILL.md` and current code provide task-specific details. Run only the steps needed for the user's request. Selecting a job does not start every phase automatically.

## 1. Choose the path by intent

| Goal | Path | Done when |
| --- | --- | --- |
| Assess a role or review a resume | Read, research, and identify evidence and gaps | Findings are delivered; no job, document, or application record is changed |
| Improve candidate evidence | `doorknock-refine` | Only confirmed facts are added to the private evidence file |
| Save a job | Job import flow | A confirmed job and a `saved` application are created |
| Research an employer or contact | `doorknock-scout` | Sources and uncertainty are clear; findings are saved only when requested |
| Create an application document | `doorknock-tailor` | The requested resume or cover letter passes content and PDF checks before its own version is published |
| Draft outreach | `doorknock-knock` | The draft is ready for review; nothing has been sent |
| Track a real application event | `doorknock-cadence` | Only user-confirmed events and outcomes are recorded |
| Practice an interview | `doorknock-interview` | Practice takes place in the agent conversation without changing the application stage |

Use `doorknock-flow` to coordinate multiple phases only when the user asks for an end-to-end application workflow. Check the existing record and the requested scope at each phase.

## 2. Data ownership

- `workspace/profile.yaml` holds candidate identity, contact details, and personal links.
- `workspace/master_resume/master_evidence.yaml` is the maintained source for candidate experience, education, skills, and projects. A job requirement or AI inference cannot become a candidate fact.
- `workspace/applications/` holds private document inputs, compiled output, and version metadata. `workspace/interviews/` holds concise practice progress.
- `data/jobs.db` holds jobs, match analyses, company research, contacts, outreach drafts, application stages, and timeline events. It records local application state; it is not another source of candidate accomplishments.

Both `workspace/` and `data/` are ignored by Git. Tracked code, docs, prompts, and tests must remain candidate-agnostic and use synthetic examples. Reading or analyzing private data does not authorize importing, updating, or sending it.

## 3. Job research, analysis, and import

1. Check the employer, title, requisition, and official posting. Reposts, alerts, and AI summaries are leads. State uncertainty if the opening cannot be confirmed as active.
2. The Web UI's **Import Job** dialog accepts a job URL or pasted job description (JD). `POST /api/jobs/fetch-url` tries structured job data and supported ATS page content before falling back to general page text. Access restrictions or JavaScript-only pages may still require pasting the JD. Review and edit extracted text before analysis.
3. `POST /api/jobs/analyze` analyzes the JD against private candidate evidence using the configured AI provider. It returns an analysis but **does not save a job**. Explicitly pasted text takes priority over fetched URL content.
4. Review the employer, title, pay, work arrangement, source, and match explanation. A match score is an analysis result, not a hiring probability. Separate direct evidence, transferable experience, and gaps.
5. When the user decides to save the job, the Web UI calls `POST /api/jobs/import`, creating a job and an application in the `saved` stage. For an existing job, `POST /api/jobs/{job_id}/rematch` can update its saved analysis and score when requested.

An agent research request may end with a brief. Do not call the import endpoint unless the user asks to add the job to DoorKnock.

## 4. Company research and contacts

For a saved job, read `GET /api/jobs/{job_id}` first to see the JD, existing research, contacts, and application state. The Web UI's `POST /api/jobs/{job_id}/recon` generates and saves company and department research in `jobs.company_recon_json`. Treat it as strategic context; distinguish sourced facts from inferred internal problems.

`doorknock-scout` can use available public or connected sources to find recruiters, managers, and peers. Verify current role, team relationship, and contact details so a namesake is not mistaken for the target. Save contacts through `POST /api/jobs/{job_id}/contacts` or the Web UI only when the user asks to retain them. Company research, contact research, and contacting a person are separate actions.

## 5. Application documents: agent conversation and Web UI

Both paths use the same candidate evidence, Typst layout, and publication checks. Each request generates **one document type only**. They differ in how the text is written:

| Path | Authoring and execution | Best for |
| --- | --- | --- |
| Agent conversation | The agent maps the JD to master evidence and writes the requested document. It saves structured JSON under private `workspace/`, then compiles with `uv run python -m app.tailor.cli --job-id <JOB_ID> --document-type resume --authored-json <WORKSPACE_JSON_PATH>` (or `cover_letter`). | Claim-by-claim review and focused revisions |
| Web UI | The user selects Tailor Resume or Tailor Cover Letter; `POST /api/jobs/{job_id}/tailor/resume` or `/tailor/cover-letter` generates that type with the configured AI provider. | Creating a document directly in the interface |

For a job outside the database, the agent can use `--jd-file <PATH> --company <COMPANY> --title <TITLE> --document-type <TYPE> --authored-json <WORKSPACE_JSON_PATH>`. In an agent-authored task, do not switch to the Web UI generation endpoint: it would bypass the reviewed text.

In either path, the JD describes employer needs and the master evidence establishes candidate facts. Select only relevant, supported experience and terms. Mark missing evidence as a gap or use `doorknock-refine` to clarify it. Use standard ATS headings, selectable text, and natural wording in the resume. Write the cover letter separately, without repeating the resume or presenting inferred company issues as facts. A request to “review a resume” is diagnostic; a layout-only request preserves verified experience wording.

Before publication, the requested PDF must compile, contain its required sections and extractable text, and pass a visual readability and content check. Resumes may use multiple pages by default; the user can require a single page in Settings. Cover letters remain one page. Validate the PDF in private staging first. Publish resumes under immutable `workspace/applications/<...>/resume/v001`, `v002`, and so on; publish cover letters independently under `cover-letter/v001`, `v002`, and so on. The root `workspace-metadata.json` records each type's latest published version. A failed attempt leaves previous versions available. Existing paired files under `versions/vNNN/` remain readable but are not the destination for new versions.

## 6. Outreach drafts and human sending

Use `doorknock-knock` to draft for a verified contact with relevant factual support. A LinkedIn connection note is limited to 300 characters; check other message lengths and style against the skill. Drafts may stay under private `workspace/applications/`. Save to `outreach_messages` with initial status `draft` only when the user asks to retain them. The Web UI's **Generate Outreach Drafts** action also saves drafts; regeneration deletes that contact's existing `draft` messages, while previously sent messages should remain.

The user reviews, copies, and sends messages. `ready_to_send` or copied text does not mean the message was sent. Mark it `sent` or update the application only after the user confirms the real-world action. Agents do not autonomously submit applications, upload documents, send invitations or email, contact recruiters, or change external trackers.

## 7. Pipeline, follow-ups, and interviews

`GET /api/pipeline/kanban` displays applications. The current stages are `saved`, `applied`, `knocked`, `recruiter_screen`, `assessment`, `team_match`, `technical_interview`, `final_round`, `offer`, and `closed`. Rejection is `closed` with `outcome: rejected`, not a separate stage. Import creates a `saved` application; `POST /api/jobs/{job_id}/start-application` can add an application record to an older saved job.

After the user confirms a real event, read the existing application and timeline before calling `PATCH /api/pipeline/applications/{application_id}/stage`. This endpoint writes a `stage_change` event. It does not itself prove that outreach was sent or capture every interview detail. Moving to `applied` or `knocked` currently sets the next follow-up date to **three days from the transition date**; moving to `offer` or `closed` clears it. That default date is not a commitment by the user to make contact.

`GET /api/pipeline/followups?days=3` lists upcoming follow-ups; `GET /api/pipeline/stale?days=14` lists applications that have not been updated recently. These are review lists. They **do not automatically send, change stages, or classify an application as ghosted**. Check actual correspondence, draft a follow-up when useful, and record an outcome only when the user confirms it.

### Gmail application scan

The Settings page can connect one Gmail account using Google's read-only OAuth scope. Set `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in the local environment or ignored `.env` file, enable the Gmail API for that Google Cloud project, and register `http://localhost:8000/api/gmail/callback` as an authorized redirect URI for its web OAuth client. If the backend uses another local address, set `GMAIL_REDIRECT_URI` to the matching registered callback. OAuth tokens are stored only in ignored `data/gmail-token.json`; keep that file private.

Click **Scan Gmail** to check recent received mail. The default is 14 days and 150 messages; the UI accepts 1–30 days and 100–200 messages per scan. A scan reads at most one Gmail result page. If more matching messages exist, use **Scan next page** to continue that same date window. Repeated scans ignore previously saved message IDs.

The scan saves only a Gmail message/thread reference, matched application when known, timestamp, event code, and match reason in the local database. It does not store the message body, subject, sender, or attachments. A unique company plus role or requisition match is required for automatic changes. Only clear application acknowledgments, explicit rejections, and confirmed recruiter/phone screens can change a stage automatically. Uncertain messages appear in **Needs review** without changing any stage: open the original Gmail message, choose the correct application and stage, then confirm or dismiss it. Messages with no application match and no recognizable application event are ignored. Each stage change records a timeline event with the Gmail message ID so it can be audited. Running a scan is the user's authorization for the limited automatic transitions; no message is sent or modified in Gmail.

Job-board alerts are filtered using a combination of platform sender identity and recommendation/digest signals in the subject, body, or bulk-mail headers. LinkedIn, Handshake, and HiringCafe recommendation mail is excluded from matches and the review queue; direct application updates from the same platforms remain eligible. Filtered message IDs and fixed reason codes are retained locally for deduplication without saving sender, subject, or body. A new scan also rechecks pending review items in its date window and removes those identified as job-board alerts. Previously recorded stage changes are not silently reversed.

Interview practice uses `doorknock-interview` in the current agent conversation: one question at a time, or a five-question mock if the user chooses it. Store only a concise progress summary in `workspace/interviews/<job_id>/progress.yaml`, not a transcript or audio. Practice is not a scheduled or completed interview and does not change the board.

## 8. Running and verifying the system

- `run.ps1` starts the local service, with the Web UI and API at `http://localhost:8000` by default. The Web UI has Dashboard, Saved Jobs, Kanban, and Settings views. Job details provide JD, research, contacts, documents, and timeline tabs. Dashboard shows saved/ready jobs, applications with a recorded applied date, active pipeline records, follow-ups due within three days, a 12-week application chart, current stage counts, and a review list. Current stage counts are a snapshot, not a conversion funnel; stale records do not establish an outcome.
- Settings selects the AI provider. Confirm that it is configured before AI-based analysis, research, drafting, or Web UI document generation. Agent-authored documents can use the local CLI compilation path.
- Check Git status before changing code or this guide, and preserve existing work. After a repository change, run `uv run pytest tests`. If Windows cache or temporary-directory permissions block the run, use writable private paths inside the repo. Check the actual artifact and `tests/test_pii_leak_guard.py`; do not rely on a fixed test count.

This guide describes current capabilities. If it conflicts with the running code or a newer skill, inspect the difference and correct the documentation or implementation. Do not present planned behavior as shipped behavior.
