export interface Job {
  id: string;
  source: string;
  source_job_id?: string | null;
  title: string;
  company: string;
  company_url?: string;
  location?: string;
  workplace_type?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  salary_interval?: string;
  job_url?: string;
  application_url?: string;
  job_description?: string;
  job_brief?: string;
  suitability_score?: number;
  suitability_reason?: string;
  analysis_json?: string;
  company_recon_json?: string | null;
  company_recon?: CompanyReconData | null;
  status: string;
  created_at: string;
  updated_at: string;
  contact_count?: number;
  artifact_count?: number;
  application_stage?: string;
  contacts?: Contact[];
  artifacts?: any[];
  timeline?: TimelineEvent[];
  application?: any;
}

export interface Contact {
  id: string;
  job_id: string;
  name: string;
  role_title: string;
  contact_type: string;
  linkedin_url?: string;
  email?: string;
  notes?: string;
  created_at: string;
  messages?: OutreachMessage[];
}

export interface OutreachMessage {
  id: string;
  contact_id: string;
  channel: string;
  archetype: string;
  subject?: string;
  body: string;
  status: string;
  sent_at?: string;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  application_id: string;
  event_type: string;
  from_stage?: string;
  to_stage?: string;
  title: string;
  description?: string;
  occurred_at: string;
}

export interface KanbanCard {
  application_id: string;
  job_id: string;
  title: string;
  company: string;
  location?: string;
  workplace_type?: string;
  current_stage: string;
  outcome?: string;
  applied_date?: string;
  next_followup_date?: string;
  followup_count: number;
  suitability_score?: number;
  analysis_json?: string;
  job_url?: string;
  contact_count: number;
  message_count: number;
  updated_at: string;
}

export interface KanbanBoardResponse {
  stages: Record<string, KanbanCard[]>;
  total_applications: number;
}

export interface DashboardSummary {
  saved_jobs: number;
  submitted: number;
  active: number;
  followups_due: number;
  stage_counts: Record<string, number>;
  weekly_applications: { week_start: string; count: number }[];
  attention_items: {
    application_id: string;
    job_id: string;
    title: string;
    company: string;
    kind: 'followup' | 'stale';
    date: string;
  }[];
}

export interface TriageResult {
  decision: "STRONG_KNOCK" | "SELECTIVE_APPLY" | "HIGH_RISK_LOW_ROI" | "HARD_PASS";
  dealbreakers_detected: string[];
  strategic_thesis: string;
}

export interface EmployerMandate {
  role_archetype?: string;
  acute_operational_frictions: string[];
  immediate_value_hook: string;
}

export interface GapAndMitigation {
  gap: string;
  severity: string;
  compensating_evidence: string;
}

export interface JobAnalysisResult {
  title: string;
  company: string;
  company_url?: string;
  location?: string;
  workplace_type?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  salary_interval?: string;
  job_brief?: string;
  technical_skills_required?: string[];
  suitability_score?: number;
  suitability_reason?: string;
  triage?: TriageResult;
  employer_mandate?: EmployerMandate;
  gaps_and_mitigation?: GapAndMitigation[];
  technical_fit_score?: number;
  domain_fit_score?: number;
  eligibility_fit_score?: number;
  key_strengths?: string[];
  gaps_or_risks?: string[];
  employer_pain_points?: string[];
  source_url?: string;
  raw_text?: string;
}

export interface DocumentVersion {
  version: string;
  filename: string;
  size_bytes: number;
  updated_at: string;
  file_path: string;
  download_filename?: string;
}

export interface DocumentTypeInfo {
  available: boolean;
  latest_version: string | null;
  download_filename?: string | null;
  versions: DocumentVersion[];
}

export interface JobDocumentsInfo {
  job_id: string;
  has_documents: boolean;
  application_dir: string | null;
  resume: DocumentTypeInfo;
  cover_letter: DocumentTypeInfo;
}

export interface CompanyReconData {
  company_name: string;
  business_model?: {
    revenue_engine?: string;
    target_customers?: string;
    value_proposition?: string;
    macro_challenges?: string;
  };
  company_stage?: {
    scale_and_momentum?: string;
    funding_or_tier?: string;
    market_standing?: string;
  };
  department_intel?: {
    team_name?: string;
    team_charter?: string;
    role_archetype?: string;
    hiring_manager_profile?: string;
    manager_core_pressure?: string;
  };
  strategic_positioning_for_candidate?: {
    tailor_summary_angle?: string;
    cover_letter_hook_angle?: string;
  };
  researched_at?: string;
}

