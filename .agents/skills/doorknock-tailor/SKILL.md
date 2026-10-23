---
name: doorknock-tailor
description: Tailor an ATS resume with an optional one-page requirement or a De-AI cover letter independently for a target job using DoorKnock's Typst-native engine.
metadata:
  tags: [doorknock, resume, cover-letter, typst, tailor, job-application]
---

# DoorKnock Tailor Skill

Use this skill when tailoring an ATS resume or a cover letter for a job in DoorKnock. Generate only the document type the user requested. Each type has its own version sequence. Resume v001 always permits multiple pages. Later resume versions are unrestricted by default; users can require one page for those revisions in DoorKnock Settings.

## Core Philosophy

1. **Strict Truth Anchor (Anti-Hallucination)**:
   - Ground truth is anchored on `workspace/master_resume/master_evidence.yaml` and `workspace/profile.yaml`.
   - Never invent degrees, employers, unverified tools, or inflate numerical metrics beyond what is verified in the candidate's master resume and profile.
2. **Relevant Evidence First**:
   - Select verified accomplishments that address the posting's stated requirements; do not claim knowledge of internal problems from inference alone.
3. **Document-specific writing**:
   - **Resume:** Prioritize verified evidence, role relevance, standard ATS headings, useful detail, and clear bullets. Write directly about work the candidate performed: use the precise action and object, then the method or verified result that matters for this role. Do not weaken direct evidence with "helped," "exposure to," or "familiar with" unless that is the actual scope. Do not inflate ownership or attach inferred business effects to a verified action. Use selective Typst-native `*bold*` for supported outcomes or tools. Keep wording natural and concise; apply a light De-AI or Sepia pass only when a line is visibly formulaic or hard to read. Do not force conversational rhythm, a banned-word list, or a prose rewrite across the whole resume.
   - **Cover letter:** Apply the in-project Sepia professional standard and 4-phase architecture:
     1. *Hook*: Open with a priority stated in the posting and the candidate's relevant approach; do not open with "I am writing to apply..." or generic introductions. Do not invent employer losses, incidents, or internal problems from recon or general industry assumptions.
     2. *Grounded Proof / War Story*: Highlight a concrete technical accomplishment showing how the candidate structured work, enforced constraints/contracts, tested defensively, or handled failure recovery. Show actual methods and boundaries rather than bare buzzwords.
     3. *Domain & Operational Context*: Connect verified background to real business risk and operational environment (e.g. data integrity, transaction risk, system reliability).
     4. *Conviction & Boundaries*: Close with disciplined verification, respecting review/rollback procedures, and readiness to take ownership under technical guidance.
     *Sepia De-AI Mandate*: Strip chatbot filler, hollow praise, repeated skill lists, and generative boilerplate (e.g. "directly aligns with", "testament to", "welcome the opportunity to discuss", "Holding a degree...", "foster", "elevate", "harness", "seamless"). Never parrot the job posting verbatim or assert inferred internal company problems as facts.
   - For either document, all claims and metrics must stay within the master evidence. Sepia review or refactor can improve wording, but cannot strengthen a claim beyond its source.
4. **Resume Template Standard & Typst-Native Layout**:
   - Authoritative executive serif typography (**Times New Roman**).
   - Clean horizontal divider rules under uppercase section headings.
   - Flush right-aligned dates, locations, and degree graduation years (`align: (left, right)`).
   - Left-aligned `CERTIFICATIONS` section.
   - Compile a readable resume with enough space for the strongest relevant evidence. Resume v001 always permits multiple pages, even when the saved one-page preference is enabled. Apply that preference only to later resume versions; do not force a utilization percentage.
   - The compiler will not shrink resume body text below 9.3pt. If the content does not fit, edit for relevance or report the limit; do not bypass it with smaller type.
   - Candidate-facing clean naming: `[Name]_Resume_[Company].pdf` and `[Name]_Cover_Letter_[Company].pdf`.
5. **JD-Driven Selection**:
   - Select relevant evidence, projects, and skills for the target job without fixed bullet counts or categories.
   - Count work experience entries in the master evidence, excluding projects. With one to three entries, retain every job by default and vary its detail by relevance; summarize less relevant work briefly rather than omitting the entry. Only with more than three entries should you consider omitting entire jobs, weighing relevance, recency, and career continuity. This is an omission threshold, not a three-job maximum. Preserve exact employers, titles, dates, and locations. Shorten bullets and other sections before dropping a job merely to fit one page. Keep complete work history in the master evidence; this selection applies only to the tailored resume.
   - Use terms from the posting only when they accurately describe the candidate's evidence.
   - Review the finished resume for substance, not just page count: give a relevant project enough room to show method, validation, and result when the evidence supports them. Do not shrink useful content merely to leave white space or meet a visual utilization target.
   - Write the resume summary as a brief overview of relevant work and strengths, not an accomplishment bullet or a stack of target-role keywords. Supported JD terms are welcome when they clarify the work. Lead with what the candidate has done; mention a transition only when needed to clarify the fit, and do so once. Give the cover letter a concrete opening tied to the role. Do not repeat the same skills list in both places.
   - Check the letter header and signature for a generic profile headline that conflicts with the target role. A role-specific subject line is enough; do not imply the candidate already holds the target title.
   - When a key requirement has no convincing evidence, use `doorknock-refine` to look for existing detail or ask for facts. Do not fabricate a bridge.

## Agent Mode: Write Here, Compile Locally

When invoked in an agent conversation, the current agent writes and reviews the requested document. Do not run the provider generation path or call `POST /api/jobs/{job_id}/tailor/{doc_type}` for agent-mode drafting.

1. Read the target posting and the gitignored `workspace/master_resume/master_evidence.yaml` and `workspace/profile.yaml`. Keep candidate facts inside `workspace/`; never put them in tracked source, prompts, or tests.
2. Build `keyword_alignment` before drafting, using the contract below. Map the main job requirements to specific verified evidence, retaining important unsupported requirements as gaps. Treat company recon as uncertain context.
   Use that map as the writing brief: read each linked source statement, identify its actual action, object, method and supported result, then rewrite that same work using equivalent JD verbs and nouns in the planned document sections. Change sentence structure and emphasis where useful; preserve domain, tools, employer/project, responsibility, seniority, provenance and metric scope. If a JD term would change the meaning, keep accurate wording and leave that term as a gap. Rewrite only the tailored document; preserve the evidence bank's original statements. The Summary synthesizes the selected experience rather than repeating the rewritten bullets.
3. For a resume, draft positioning, then Experience and Projects, then Skills, Education and Certifications. Preserve exact identity, dates, degrees, certifications, employers, tools, and metrics from evidence. Review each section against its sources.
   Apply the work experience selection rule above before drafting and check it again during review: one to three jobs are all retained by default; more than three permits selective omission without imposing a three-job maximum.
   In the Skills section, use concise skill names without parenthetical provenance labels such as `(coursework)`. Keep coursework provenance in the master evidence and never imply paid use or production experience from it.
4. Write the resume Summary last from its selected content. Make it a brief, natural overview for a human reader. Check every claim against evidence; remove keyword lists, unsupported target-title claims, and repeated bullet metrics.
   Read the Summary and each bullet aloud. Replace vague nouns with concrete descriptions of verified work. Preserve the original domain and the candidate's actual level of ownership.
5. For a cover letter, write and review it independently from verified evidence and the posting following the 4-phase architecture (Hook, Grounded Proof / War Story, Domain & Operational Context, Conviction & Boundaries). If an existing resume is relevant, it may inform emphasis; generating a cover letter never regenerates the resume. Do not assert inferred internal company problems as facts.
6. Review the completed document against every evidence boundary, including claims not covered by the keyword map. Supply `claim_review` using the contract below. Fix findings and repeat the manual review before setting `ready`; never clear findings without fixing the text. Save a UTF-8 JSON package under the gitignored application workspace. A resume package contains `tailor_strategy` and `resume`; a cover letter package contains `cover_letter`. Both new packages include `keyword_alignment` and `claim_review`. Run the local CLI with `--document-type` and `--authored-json` to compile and publish that PDF alone. Review it visually and verify text, page count, and claim fidelity before presenting it.
   Compare rewritten wording with its linked original statements. JD synonyms are allowed when they preserve the actual action and scope; flag wording that recasts transferable work as direct domain experience. The publication check compares exact employer, role, date, location, education, project names, and numeric claims against master evidence. It cannot judge paraphrased duties, skill context, or whether a claim is misleading, so finish the manual evidence review before compiling.

### Keyword alignment and claim-review contract

Every new authored package must include these top-level fields:

```json
{
  "keyword_alignment": [
    {
      "keyword": "discrepancies",
      "requirement": "Investigate discrepancies",
      "support": "direct",
      "evidence_ids": ["<existing evidence bullet ID>"],
      "placements": ["experiences"],
      "boundary": "Operational records; no product-catalog or ERP ownership claim."
    }
  ],
  "claim_review": {"status": "ready", "findings": []}
}
```

- `requirement` quotes the current JD verbatim and contains `keyword`. Preserve the requirement's domain when judging support; a matching word alone is insufficient. Include the principal activities, tools, deliverables, qualifications, and important gaps without keyword quotas.
- `support` is `direct`, `transferable`, or `unsupported`. Direct requires support in the stated context. Transferable retains the original domain, provenance, tools, responsibility and results. Unsupported entries use empty `evidence_ids` and `placements`.
- Use existing work/project or bullet IDs, preferring specific bullet IDs. For skill evidence without an ID, reference `technical_skills/<category>/<zero-based index>` from the current YAML. Do not infer confirmed claims from tags or unchecked metrics. Read the parent confirmation limits as well as the bullet.
- Resume placements: `summary`, `experiences`, `projects`, `skills`. Cover-letter placements: `paragraphs`. A keyword's planned placement is advisory; missing words do not justify invented experience.
- `boundary` states what the rewrite must preserve and must not imply. Skills supported by coursework or projects do not establish paid use. Do not turn reconciliation into product-data management, or tenant/building specifications into software or catalog ownership.
- Cover letters connect one or two concrete examples to the main requirements. Use supported terminology, not copied JD sentences or repeated skill lists. Keep hypothetical consequences and recon inferences out of factual employer claims.
- Review all completed claims for stronger domain, ownership, tools, seniority or results, and for employer speculation. A review with issues uses `status: "needs_revision"` and `findings`, each containing `section`, an exact document `quote`, `issue`, and an evidence-safe `suggestion`. Resume sections match the allowed placements; letter findings use `paragraphs`. Publication stops until the text is corrected and reviewed again. Do not automatically retry provider generation.
- Published versions include a private `keyword-review.json` with the mapping, literal coverage, claim review, source and input/document fingerprints. Read the report and consider supported terms marked `could_improve` and `missing_placements`; do not chase a score. ID validity and literal coverage cannot prove truthful paraphrasing; agent/provider review is not independent verification.
- Old authored packages omitting both fields remain compilable for compatibility, but are explicitly marked `not_reviewed`. Never omit the fields from new packages to bypass a finding, and never describe a legacy package as having passed alignment review.

Resume content shape (also include the alignment and review fields above):
```json
{
  "tailor_strategy": {"target_role_header": "ANALYST", "primary_angle": "Evidence-based fit"},
  "resume": {"summary": "...", "experiences": [], "projects": [], "skills": [], "education": [], "certifications": ""}
}
```
Cover letter content shape (also include the alignment and review fields above):
```json
{
  "cover_letter": {
    "paragraphs": ["<hook_paragraph>", "<war_story_paragraph>", "<domain_context_paragraph>", "<conviction_paragraph>"],
    "recipient_title": "Engineering Hiring Team",
    "salutation": "Engineering Hiring Team"
  }
}
```
The arrays use the existing Typst template fields: experiences contain `company`, `location`, `title`, `dates`, and `bullets`; projects contain `name`, `tech_stack`, and `bullets`; skills contain `category` and `items`; education contains `institution`, `degree`, `year`, `location`, and `focus`.

The UI endpoints use the configured provider. Resume generation includes the alignment map in positioning, then writes sections and Summary and performs a separate claim review. Cover-letter generation independently plans alignment, drafts paragraphs, and reviews claims. This uses five provider calls for a resume and three for a cover letter, without automatic revision retries.

## How to Trigger

### Option A: From DoorKnock Database (by Job ID)
When the job exists in the DoorKnock database:
```powershell
uv run python -m app.tailor.cli --job-id <JOB_ID> --document-type resume --authored-json <WORKSPACE_JSON_PATH>
```

### Option B: From Raw JD File
When testing a new JD outside the database:
```powershell
uv run python -m app.tailor.cli --jd-file <PATH_TO_JD_FILE> --company "<COMPANY>" --title "<TITLE>" --document-type cover_letter --authored-json <WORKSPACE_JSON_PATH>
```

### Option C: Via FastAPI Endpoint (from Web UI)
`POST /api/jobs/{job_id}/tailor/resume` and `POST /api/jobs/{job_id}/tailor/cover-letter` each generate one type and update document availability in the DoorKnock UI.

## Output Artifacts
All generated files are saved under:
```
workspace/applications/YYYY-MM-DD-[company]-[position]-[job-key]/
├── resume/
│   └── v001/[Candidate_Name]_Resume_[Company].pdf (+ .typ and workspace-metadata.json)
├── cover-letter/
│   └── v001/[Candidate_Name]_Cover_Letter_[Company].pdf (+ .typ and workspace-metadata.json)
└── workspace-metadata.json (latest published version of each type)
```
Each type increments separately. Existing paired `versions/vNNN/` files remain readable.
