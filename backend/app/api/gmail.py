import httpx
from datetime import date
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .. import gmail_sync

router = APIRouter(prefix="/api/gmail", tags=["gmail"])
PREVIEW_HEADERS = {'Cache-Control': 'no-store, private', 'Pragma': 'no-cache'}


class ScanRequest(BaseModel):
    recent_days: int = Field(default=14, ge=1, le=30)
    limit: int = Field(default=150, ge=100, le=200)
    page_token: str | None = None
    window_start: int | None = None


class ReviewDecision(BaseModel):
    action: str
    application_id: str | None = None
    to_stage: str | None = None
    due_date: date | None = None
    outcome: Literal['rejected', 'withdrawn', 'offer_accepted', 'offer_declined'] | None = None


@router.get("/status")
def status():
    return {"configured": gmail_sync.configured(), **gmail_sync.connection_status()}


@router.post("/connect")
def connect():
    try:
        return {"auth_url": gmail_sync.authorization_url()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/callback", response_class=HTMLResponse)
async def callback(code: str, state: str):
    try:
        await gmail_sync.exchange_code(code, state)
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400, detail="Gmail connection failed; try connecting again") from exc
    return "<p>Gmail connected. Return to DoorKnock and run a scan.</p>"


@router.post("/scan")
async def scan(request: ScanRequest):
    try:
        return await gmail_sync.scan_recent(days=request.recent_days, limit=request.limit,
                                            page_token=request.page_token,
                                            window_start=request.window_start)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Gmail request failed; scan may be partial. Check recent matches before retrying") from exc


@router.get("/messages")
def messages(application_id: str | None = None):
    return {"messages": gmail_sync.saved_messages(application_id=application_id)}


@router.get("/reviews")
def reviews(status: Literal['pending', 'processed'] = 'pending', offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    return gmail_sync.pending_reviews(limit, status=status, offset=offset)


@router.post("/reviews/{message_id}/resolve")
def resolve_review(message_id: str, decision: ReviewDecision):
    try:
        return gmail_sync.resolve_review(message_id, decision.action,
                                         decision.application_id, decision.to_stage,
                                         due_date=decision.due_date.isoformat() if decision.due_date else None,
                                         outcome=decision.outcome)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/reviews/{message_id}/preview')
async def preview_review(message_id: str):
    try:
        return JSONResponse(await gmail_sync.preview_message(message_id), headers=PREVIEW_HEADERS)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail='Review item not found', headers=PREVIEW_HEADERS) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc), headers=PREVIEW_HEADERS) from exc
    except httpx.HTTPStatusError as exc:
        missing = exc.response.status_code == 404
        raise HTTPException(status_code=404 if missing else 502,
                            detail='The original email is no longer available in Gmail.' if missing else 'Could not load email preview. Try again or open the original in Gmail.',
                            headers=PREVIEW_HEADERS) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail='Could not load email preview. Try again or open the original in Gmail.', headers=PREVIEW_HEADERS) from exc


@router.post('/reviews/{message_id}/undo')
def undo_review(message_id: str):
    try:
        return gmail_sync.undo_review(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
