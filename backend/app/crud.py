import uuid
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from .database import get_db

KANBAN_STAGES = [
    "saved",
    "applied",
    "knocked",
    "recruiter_screen",
    "assessment",
    "team_match",
    "technical_interview",
    "final_round",
    "offer",
    "closed"
]

def get_saved_jobs(search: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    with get_db() as conn:
        query = """
            SELECT j.*, 
                   (SELECT COUNT(*) FROM contacts c WHERE c.job_id = j.id) as contact_count,
                   (SELECT COUNT(*) FROM job_artifacts a WHERE a.job_id = j.id) as artifact_count,
                   app.current_stage as application_stage
            FROM jobs j
            LEFT JOIN applications app ON app.job_id = j.id
            WHERE j.status IN ('saved', 'ready')
        """
        params: List[Any] = []
        if search:
            query += " AND (j.title LIKE ? OR j.company LIKE ? OR j.location LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        
        query += " ORDER BY j.suitability_score DESC NULLS LAST, j.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        job = dict(row)
        
        # Get application
        app_cursor = conn.execute("SELECT * FROM applications WHERE job_id = ?", (job_id,))
        app_row = app_cursor.fetchone()
        job["application"] = dict(app_row) if app_row else None
        
        # Get contacts
        contacts_cursor = conn.execute("SELECT * FROM contacts WHERE job_id = ? ORDER BY created_at ASC", (job_id,))
        contacts = [dict(r) for r in contacts_cursor.fetchall()]
        
        # For each contact, get messages
        for c in contacts:
            msg_cursor = conn.execute("SELECT * FROM outreach_messages WHERE contact_id = ? ORDER BY created_at ASC", (c["id"],))
            c["messages"] = [dict(m) for m in msg_cursor.fetchall()]
        
        job["contacts"] = contacts
        
        # Get artifacts
        art_cursor = conn.execute("SELECT * FROM job_artifacts WHERE job_id = ? ORDER BY created_at DESC", (job_id,))
        job["artifacts"] = [dict(a) for a in art_cursor.fetchall()]
        
        # Get timeline if application exists
        if job["application"]:
            timeline_cursor = conn.execute(
                "SELECT * FROM timeline_events WHERE application_id = ? ORDER BY occurred_at DESC",
                (job["application"]["id"],)
            )
            job["timeline"] = [dict(t) for t in timeline_cursor.fetchall()]
        else:
            job["timeline"] = []
            
        return job

def get_kanban_board() -> Dict[str, Any]:
    stages: Dict[str, List[Dict[str, Any]]] = {stage: [] for stage in KANBAN_STAGES}
    with get_db() as conn:
        query = """
            SELECT 
                app.id as application_id,
                app.job_id,
                app.current_stage,
                app.outcome,
                app.applied_date,
                app.next_followup_date,
                app.followup_count,
                app.updated_at,
                j.title,
                j.company,
                j.location,
                j.workplace_type,
                j.suitability_score,
                j.analysis_json,
                j.job_url,
                (SELECT COUNT(*) FROM contacts c WHERE c.job_id = j.id) as contact_count,
                (SELECT COUNT(*) FROM outreach_messages m JOIN contacts c ON m.contact_id = c.id WHERE c.job_id = j.id) as message_count
            FROM applications app
            JOIN jobs j ON j.id = app.job_id
            ORDER BY app.updated_at DESC
        """
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        total = len(rows)
        for row in rows:
            card = dict(row)
            stage = card.get("current_stage")
            if stage in stages:
                stages[stage].append(card)
            else:
                stages["saved"].append(card)
                
        return {"stages": stages, "total_applications": total}


def get_dashboard_summary() -> Dict[str, Any]:
    """Read-only pipeline measures for the local dashboard."""
    today = date.today()
    first_week = today - timedelta(days=today.weekday() + 7 * 11)
    weeks = {
        (first_week + timedelta(weeks=index)).isoformat(): 0
        for index in range(12)
    }
    with get_db() as conn:
        saved_jobs = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN ('saved', 'ready')"
        ).fetchone()[0]
        applications = conn.execute(
            "SELECT current_stage, applied_date FROM applications"
        ).fetchall()
        stage_counts = {stage: 0 for stage in KANBAN_STAGES}
        submitted = 0
        for application in applications:
            stage = application["current_stage"]
            if stage in stage_counts:
                stage_counts[stage] += 1
            applied_date = application["applied_date"]
            if not applied_date:
                continue
            submitted += 1
            try:
                applied_day = date.fromisoformat(applied_date)
            except ValueError:
                continue
            week_start = (applied_day - timedelta(days=applied_day.weekday())).isoformat()
            if week_start in weeks:
                weeks[week_start] += 1

    followups = get_upcoming_followups(days_ahead=3)
    stale = get_stale_applications(days_dormant=14)
    attention_items = []
    seen = set()
    for kind, records in (("followup", followups), ("stale", stale)):
        for record in records:
            if record["id"] in seen:
                continue
            seen.add(record["id"])
            attention_items.append({
                "application_id": record["id"],
                "job_id": record["job_id"],
                "title": record["title"],
                "company": record["company"],
                "kind": kind,
                "date": record["next_followup_date"] if kind == "followup" else record["updated_at"],
            })

    return {
        "saved_jobs": saved_jobs,
        "submitted": submitted,
        "active": sum(count for stage, count in stage_counts.items()
                      if stage not in ("saved", "closed", "offer")),
        "followups_due": len(followups),
        "stage_counts": stage_counts,
        "weekly_applications": [
            {"week_start": week, "count": count} for week, count in weeks.items()
        ],
        "attention_items": attention_items,
    }

def transition_application_stage(application_id: str, to_stage: str, outcome: Optional[str] = None, note: Optional[str] = None) -> Optional[Dict[str, Any]]:
    # Pipeline contract: only "closed" is the terminal stage, never "rejected"
    normalized_stage = to_stage.lower().strip()
    if normalized_stage == "rejected":
        normalized_stage = "closed"
    if normalized_stage not in KANBAN_STAGES:
        raise ValueError(f"Invalid stage '{to_stage}'. Stage must be one of: {', '.join(KANBAN_STAGES)}")

    to_stage = normalized_stage

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
        app = cursor.fetchone()
        if not app:
            return None
        from_stage = app["current_stage"]
        now_str = datetime.now().isoformat()
        
        applied_date = app["applied_date"]
        if to_stage == "applied" and not applied_date:
            applied_date = date.today().isoformat()
            
        # Calculate next follow up date if stage is applied or knocked
        next_followup = app["next_followup_date"]
        if to_stage in ("applied", "knocked"):
            next_followup = (date.today() + timedelta(days=3)).isoformat()
        elif to_stage in ("closed", "offer"):
            next_followup = None
            
        if outcome is not None:
            clean_outcome = None if outcome.lower().strip() in ("", "clear", "none", "null") else outcome.strip()
        else:
            # When moving to an active stage (not closed/offer), automatically clear any stale terminal outcome
            clean_outcome = None if to_stage not in ("closed", "offer") else app["outcome"]

        conn.execute("""
            UPDATE applications
            SET current_stage = ?, outcome = ?, 
                applied_date = COALESCE(?, applied_date),
                next_followup_date = ?,
                updated_at = ?
            WHERE id = ?
        """, (to_stage, clean_outcome, applied_date, next_followup, now_str, application_id))
        
        # Also update job status if appropriate
        job_status = "in_progress"
        if to_stage == "closed":
            job_status = "archived"
        elif to_stage == "saved":
            job_status = "saved"
        elif to_stage == "applied":
            job_status = "applied"
            
        conn.execute("UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?", (job_status, now_str, app["job_id"]))
        
        # Log timeline event
        event_id = str(uuid.uuid4())
        title = f"Stage changed to {to_stage.replace('_', ' ').title()}"
        if outcome:
            title += f" ({outcome})"
            
        conn.execute("""
            INSERT INTO timeline_events (id, application_id, event_type, from_stage, to_stage, title, description, occurred_at)
            VALUES (?, ?, 'stage_change', ?, ?, ?, ?, ?)
        """, (event_id, application_id, from_stage, to_stage, title, note, now_str))
        
        conn.commit()
        
        updated_app = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        return dict(updated_app) if updated_app else None

def create_application_for_job(job_id: str, stage: str = "saved") -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM applications WHERE job_id = ?", (job_id,))
        existing = cursor.fetchone()
        if existing:
            return dict(existing)
            
        app_id = str(uuid.uuid4())
        now_str = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO applications (id, job_id, current_stage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (app_id, job_id, stage, now_str, now_str))
        conn.commit()
        return dict(conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone())

def delete_job(job_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0

def add_contact(
    job_id: str,
    name: str,
    role_title: str,
    contact_type: str = "hiring_manager",
    linkedin_url: Optional[str] = None,
    email: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    with get_db() as conn:
        contact_id = str(uuid.uuid4())
        now_str = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO contacts (id, job_id, name, role_title, contact_type, linkedin_url, email, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (contact_id, job_id, name, role_title, contact_type, linkedin_url, email, notes, now_str))
        conn.commit()
        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        return dict(row)

def update_contact(
    contact_id: str,
    name: Optional[str] = None,
    role_title: Optional[str] = None,
    contact_type: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    email: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        conn.execute("""
            UPDATE contacts
            SET name = COALESCE(?, name),
                role_title = COALESCE(?, role_title),
                contact_type = COALESCE(?, contact_type),
                linkedin_url = COALESCE(?, linkedin_url),
                email = COALESCE(?, email),
                notes = COALESCE(?, notes)
            WHERE id = ?
        """, (name, role_title, contact_type, linkedin_url, email, notes, contact_id))
        conn.commit()
        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
        return dict(row) if row else None

def delete_contact(contact_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        return cursor.rowcount > 0

def delete_draft_outreach_messages(contact_id: str) -> int:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM outreach_messages WHERE contact_id = ? AND status = 'draft'", (contact_id,))
        conn.commit()
        return cursor.rowcount

def add_outreach_message(
    contact_id: str,
    channel: str,
    archetype: str,
    body: str,
    subject: Optional[str] = None,
    status: str = "draft",
) -> Dict[str, Any]:
    with get_db() as conn:
        msg_id = str(uuid.uuid4())
        now_str = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO outreach_messages (id, contact_id, channel, archetype, subject, body, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, contact_id, channel, archetype, subject, body, status, now_str, now_str))
        conn.commit()
        row = conn.execute("SELECT * FROM outreach_messages WHERE id = ?", (msg_id,)).fetchone()
        return dict(row)

def update_outreach_status(message_id: str, status: str, sent_at: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        now_str = datetime.now().isoformat()
        if status == "sent" and not sent_at:
            sent_at = now_str
        conn.execute("""
            UPDATE outreach_messages
            SET status = ?, sent_at = COALESCE(?, sent_at), updated_at = ?
            WHERE id = ?
        """, (status, sent_at, now_str, message_id))
        conn.commit()
        row = conn.execute("SELECT * FROM outreach_messages WHERE id = ?", (message_id,)).fetchone()
        return dict(row) if row else None

def get_stale_applications(days_dormant: int = 14) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cutoff = (datetime.now() - timedelta(days=days_dormant)).isoformat()
        query = """
            SELECT app.*, j.title, j.company, j.job_url
            FROM applications app
            JOIN jobs j ON j.id = app.job_id
            WHERE app.current_stage NOT IN ('closed', 'offer', 'saved')
              AND app.updated_at <= ?
            ORDER BY app.updated_at ASC
        """
        cursor = conn.execute(query, (cutoff,))
        return [dict(r) for r in cursor.fetchall()]

def get_upcoming_followups(days_ahead: int = 3) -> List[Dict[str, Any]]:
    with get_db() as conn:
        today_str = date.today().isoformat()
        target_str = (date.today() + timedelta(days=days_ahead)).isoformat()
        query = """
            SELECT app.*, j.title, j.company, j.job_url
            FROM applications app
            JOIN jobs j ON j.id = app.job_id
            WHERE app.current_stage IN ('applied', 'knocked', 'recruiter_screen')
              AND app.next_followup_date IS NOT NULL
              AND app.next_followup_date <= ?
            ORDER BY app.next_followup_date ASC
        """
        cursor = conn.execute(query, (target_str,))
        return [dict(r) for r in cursor.fetchall()]

def update_job_company_recon(job_id: str, recon_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        now_str = datetime.now().isoformat()
        recon_str = json.dumps(recon_data)
        conn.execute("""
            UPDATE jobs
            SET company_recon_json = ?, updated_at = ?
            WHERE id = ?
        """, (recon_str, now_str, job_id))
        conn.commit()
    return get_job_by_id(job_id)

