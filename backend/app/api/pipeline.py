from fastapi import APIRouter, HTTPException
from .. import crud, cadence
from ..models import StageTransitionRequest, CadenceEventRequest

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

@router.get('/applications/{application_id}/cadence')
def get_cadence(application_id: str):
    result = cadence.get_schedule(application_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Application not found')
    return result

@router.post('/applications/{application_id}/cadence')
def record_cadence_event(application_id: str, req: CadenceEventRequest):
    try:
        result = cadence.record_event(application_id, **req.model_dump(mode='json'))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail='Application not found')
    return result

@router.get("/kanban")
def get_kanban():
    """Retrieve all pipeline cards grouped by stage."""
    return crud.get_kanban_board()


@router.get("/dashboard")
def get_dashboard():
    """Retrieve read-only dashboard measures and attention items."""
    return crud.get_dashboard_summary()

@router.patch("/applications/{application_id}/stage")
def transition_stage(application_id: str, req: StageTransitionRequest):
    """Move an application to a new stage."""
    to_stage = req.to_stage.lower().strip()
    outcome = req.outcome
    if to_stage == "rejected":
        to_stage = "closed"
        outcome = "rejected"

    if to_stage not in crud.KANBAN_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{req.to_stage}'. Allowed stages: {', '.join(crud.KANBAN_STAGES)}. Note: 'rejected' is not a valid stage, use 'closed' instead."
        )

    updated = crud.transition_application_stage(
        application_id=application_id,
        to_stage=to_stage,
        outcome=outcome,
        note=req.note
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return updated

@router.get("/stale")
def get_stale_pipeline_cards(days: int = 30):
    """Retrieve applications that have been dormant for more than N days."""
    stale_apps = crud.get_stale_applications(days_dormant=days)
    return {"stale_applications": stale_apps, "count": len(stale_apps)}

@router.get("/followups")
def get_upcoming_pipeline_followups(days: int = 3):
    """Retrieve applications that need a follow-up action within N days."""
    followups = crud.get_upcoming_followups(days_ahead=days)
    return {"upcoming_followups": followups, "count": len(followups)}



@router.delete('/applications/{application_id}/timeline/{event_id}')
def delete_timeline_event(application_id: str, event_id: str):
    result = cadence.correct_timeline_event(application_id, event_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Timeline event not found')
    return result


@router.post('/applications/{application_id}/timeline/{event_id}/restore')
def restore_timeline_event(application_id: str, event_id: str):
    result = cadence.correct_timeline_event(application_id, event_id, restore=True)
    if result is None:
        raise HTTPException(status_code=404, detail='Timeline event not found')
    return result
