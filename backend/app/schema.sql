-- DoorKnock (敲門) SQLite Schema

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'manual',
    source_job_id TEXT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    company_url TEXT,
    location TEXT,
    workplace_type TEXT, -- 'remote', 'hybrid', 'onsite'
    salary_min REAL,
    salary_max REAL,
    salary_currency TEXT DEFAULT 'USD',
    salary_interval TEXT, -- 'year', 'hour', etc.
    job_url TEXT,
    application_url TEXT,
    job_description TEXT,
    job_brief TEXT,
    suitability_score REAL,
    suitability_reason TEXT,
    analysis_json TEXT, -- Full structured AI fit breakdown
    company_recon_json TEXT, -- Structured company & department recon intelligence
    status TEXT NOT NULL DEFAULT 'saved', -- 'saved', 'ready', 'applied', 'in_progress', 'archived'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_job_id ON jobs(source, source_job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);

CREATE TABLE IF NOT EXISTS job_artifacts (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    version TEXT NOT NULL DEFAULT 'v001',
    pain_points_json TEXT,
    matched_evidence_json TEXT,
    resume_path TEXT,
    cover_letter_content TEXT,
    status TEXT NOT NULL DEFAULT 'draft', -- 'draft', 'approved', 'stale'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_job_artifacts_job_id ON job_artifacts(job_id);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role_title TEXT NOT NULL,
    contact_type TEXT NOT NULL DEFAULT 'hiring_manager', -- 'hiring_manager', 'recruiter', 'peer', 'alumni', 'other'
    linkedin_url TEXT,
    email TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_contacts_job_id ON contacts(job_id);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    channel TEXT NOT NULL DEFAULT 'linkedin_connect', -- 'linkedin_connect', 'linkedin_inmail', 'email'
    archetype TEXT NOT NULL DEFAULT 'pain_point_solution', -- 'pain_point_solution', 'recruiter_qualification', 'peer_coffee_chat'
    subject TEXT,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft', -- 'draft', 'ready_to_send', 'sent', 'replied', 'ignored'
    sent_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_outreach_contact_id ON outreach_messages(contact_id);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    current_stage TEXT NOT NULL DEFAULT 'saved',
    -- stages: 'saved', 'applied', 'knocked', 'recruiter_screen', 'assessment', 'team_match', 'technical_interview', 'final_round', 'offer', 'closed'
    outcome TEXT, -- 'offer_accepted', 'offer_declined', 'rejected', 'withdrawn', 'ghosted'
    applied_date TEXT,
    next_followup_date TEXT,
    followup_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_applications_stage ON applications(current_stage);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);

CREATE TABLE IF NOT EXISTS timeline_events (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, -- 'stage_change', 'outreach_sent', 'message_received', 'interview_scheduled', 'note_added', 'follow_up'
    from_stage TEXT,
    to_stage TEXT,
    title TEXT NOT NULL,
    description TEXT,
    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_timeline_app_id ON timeline_events(application_id);

CREATE TABLE IF NOT EXISTS gmail_application_messages (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    received_at TEXT NOT NULL,
    event_code TEXT NOT NULL,
    match_reason TEXT NOT NULL,
    stage_applied INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_gmail_messages_application ON gmail_application_messages(application_id);

CREATE TABLE IF NOT EXISTS gmail_review_items (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    received_at TEXT NOT NULL,
    event_code TEXT NOT NULL,
    proposed_stage TEXT,
    reason_code TEXT NOT NULL,
    candidate_application_ids TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    resolved_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_gmail_review_status ON gmail_review_items(status, received_at);
