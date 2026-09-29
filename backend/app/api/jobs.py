from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from .. import crud
from ..database import get_db
from ..ai.provider import require_ai_client
from ..ai.analyzer import analyze_job_posting
from ..ai.recon import recon_company_and_department
from ..ai.knock import generate_outreach_for_contact

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/saved")
def list_saved_jobs(search: Optional[str] = Query(None), limit: int = 100, offset: int = 0):
    """Retrieve saved/ready jobs."""
    jobs = crud.get_saved_jobs(search=search, limit=limit, offset=offset)
    return {"jobs": jobs, "count": len(jobs)}

@router.get("/{job_id}")
def get_job_detail(job_id: str):
    """Retrieve full job detail including application, contacts, and timeline."""
    job = crud.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/start-application")
def start_application(job_id: str):
    """Ensure an application entry exists for a saved job."""
    app = crud.create_application_for_job(job_id)
    return app

@router.delete("/{job_id}")
def delete_job(job_id: str):
    """Delete a job and its associated application and artifacts."""
    success = crud.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "deleted_id": job_id}

@router.post("/{job_id}/contacts")
def create_job_contact(job_id: str, payload: Dict[str, Any]):
    """Add a gatekeeper contact to a target job."""
    job = crud.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    name = payload.get("name")
    role_title = payload.get("role_title")
    if not name or not role_title:
        raise HTTPException(status_code=400, detail="Name and role_title are required")
    contact = crud.add_contact(
        job_id=job_id,
        name=name,
        role_title=role_title,
        contact_type=payload.get("contact_type", "hiring_manager"),
        linkedin_url=payload.get("linkedin_url"),
        email=payload.get("email"),
        notes=payload.get("notes"),
    )
    return contact

@router.patch("/contacts/{contact_id}")
def update_job_contact(contact_id: str, payload: Dict[str, Any]):
    """Update details of an existing gatekeeper contact."""
    updated = crud.update_contact(
        contact_id=contact_id,
        name=payload.get("name"),
        role_title=payload.get("role_title"),
        contact_type=payload.get("contact_type"),
        linkedin_url=payload.get("linkedin_url"),
        email=payload.get("email"),
        notes=payload.get("notes"),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated

@router.delete("/contacts/{contact_id}")
def delete_job_contact(contact_id: str):
    """Delete a gatekeeper contact and all associated outreach messages."""
    success = crud.delete_contact(contact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"ok": True, "deleted_contact_id": contact_id}

@router.post("/contacts/{contact_id}/messages")
def create_contact_message(contact_id: str, payload: Dict[str, Any]):
    """Add an outreach draft message for a contact."""
    body = payload.get("body")
    if not body:
        raise HTTPException(status_code=400, detail="Message body is required")
    msg = crud.add_outreach_message(
        contact_id=contact_id,
        channel=payload.get("channel", "linkedin_connect"),
        archetype=payload.get("archetype", "pain_point_solution"),
        body=body,
        subject=payload.get("subject"),
        status=payload.get("status", "draft"),
    )
    return msg

@router.patch("/messages/{message_id}/status")
def update_message_status(message_id: str, payload: Dict[str, Any]):
    """Update status of an outreach message (e.g. draft -> ready_to_send -> sent)."""
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Status is required")
    updated = crud.update_outreach_status(
        message_id=message_id,
        status=status,
        sent_at=payload.get("sent_at"),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Message not found")
    return updated

@router.post("/{job_id}/rematch")
async def rematch_job(job_id: str):
    """Re-run AI Match Analysis on an existing job and update its analysis_json, suitability_score, and suitability_reason."""
    job = crud.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    raw_text = job.get("job_description") or job.get("job_brief") or ""
    if not raw_text or len(raw_text.strip()) < 30:
        raise HTTPException(status_code=400, detail="Job description text is too short to analyze.")

    try:
        ai_client = require_ai_client()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        analysis = await analyze_job_posting(
            raw_text=raw_text,
            source_url=job.get("company_url") or job.get("job_url"),
            gemini_client=ai_client
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match analysis failed: {str(e)}")

    now_str = datetime.now().isoformat()
    analysis_str = json.dumps(analysis)
    score = analysis.get("suitability_score")
    reason = analysis.get("suitability_reason")

    with get_db() as conn:
        conn.execute("""
            UPDATE jobs
            SET suitability_score = ?,
                suitability_reason = ?,
                analysis_json = ?,
                updated_at = ?
            WHERE id = ?
        """, (score, reason, analysis_str, now_str, job_id))
        conn.commit()

    updated_job = crud.get_job_by_id(job_id)
    return {"ok": True, "job": updated_job, "analysis": analysis}

@router.post("/{job_id}/recon")
async def run_company_recon(job_id: str):
    """Execute tactical reconnaissance on employer business model and department charter."""
    job = crud.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        ai_client = require_ai_client()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        recon_data = await recon_company_and_department(
            company=job.get("company", ""),
            role_title=job.get("title", ""),
            job_description=job.get("job_description") or job.get("job_brief") or "",
            company_url=job.get("company_url") or job.get("job_url"),
            gemini_client=ai_client,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Company recon failed: {str(e)}")

    updated_job = crud.update_job_company_recon(job_id, recon_data)
    return {"ok": True, "job": updated_job, "recon": recon_data}

@router.get("/{job_id}/recon")
def get_company_recon(job_id: str):
    """Get existing company recon intel for a job."""
    job = crud.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    recon_raw = job.get("company_recon_json")
    recon_data = None
    if recon_raw:
        try:
            recon_data = json.loads(recon_raw) if isinstance(recon_raw, str) else recon_raw
        except Exception:
            pass
    return {"ok": True, "recon": recon_data}

@router.post("/{job_id}/contacts/{contact_id}/generate-outreach")
async def generate_contact_outreach(job_id: str, contact_id: str):
    """Generate high-conversion, Sepia-compliant outreach message drafts for a contact."""
    job = crud.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        ai_client = require_ai_client()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        messages = await generate_outreach_for_contact(
            job_id=job_id,
            contact_id=contact_id,
            gemini_client=ai_client,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Outreach generation failed: {str(e)}")

    updated_job = crud.get_job_by_id(job_id)
    updated_contact = next((c for c in updated_job.get("contacts", []) if c["id"] == contact_id), None)
    return {"ok": True, "contact": updated_contact, "messages": messages}



