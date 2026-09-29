from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class JobBase(BaseModel):
    title: str
    company: str
    company_url: Optional[str] = None
    location: Optional[str] = None
    workplace_type: Optional[str] = "onsite"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "USD"
    salary_interval: Optional[str] = "year"
    job_url: Optional[str] = None
    application_url: Optional[str] = None
    job_description: Optional[str] = None
    job_brief: Optional[str] = None
    suitability_score: Optional[float] = None
    suitability_reason: Optional[str] = None
    status: str = "saved"

class JobCreate(JobBase):
    source: str = "manual"
    source_job_id: Optional[str] = None

class JobResponse(JobBase):
    id: str
    source: str
    source_job_id: Optional[str] = None
    created_at: str
    updated_at: str

class ContactBase(BaseModel):
    name: str
    role_title: str
    contact_type: str = "hiring_manager"
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class ContactCreate(ContactBase):
    job_id: str

class ContactResponse(ContactBase):
    id: str
    job_id: str
    created_at: str

class OutreachMessageBase(BaseModel):
    channel: str = "linkedin_connect"
    archetype: str = "pain_point_solution"
    subject: Optional[str] = None
    body: str
    status: str = "draft"

class OutreachMessageCreate(OutreachMessageBase):
    contact_id: str

class OutreachMessageResponse(OutreachMessageBase):
    id: str
    contact_id: str
    sent_at: Optional[str] = None
    created_at: str
    updated_at: str

class StageTransitionRequest(BaseModel):
    to_stage: str
    outcome: Optional[str] = None
    note: Optional[str] = None

class KanbanCard(BaseModel):
    application_id: str
    job_id: str
    title: str
    company: str
    location: Optional[str] = None
    workplace_type: Optional[str] = None
    current_stage: str
    outcome: Optional[str] = None
    applied_date: Optional[str] = None
    next_followup_date: Optional[str] = None
    followup_count: int = 0
    suitability_score: Optional[float] = None
    job_url: Optional[str] = None
    contact_count: int = 0
    message_count: int = 0
    updated_at: str

class KanbanBoardResponse(BaseModel):
    stages: Dict[str, List[KanbanCard]]
    total_applications: int

class SyncResult(BaseModel):
    imported_jobs: int
    updated_jobs: int
    imported_applications: int
    imported_events: int
    message: str
