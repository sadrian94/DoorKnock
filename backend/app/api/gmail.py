import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .. import gmail_sync

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


class ScanRequest(BaseModel):
    recent_days: int = Field(default=14, ge=1, le=30)
    limit: int = Field(default=150, ge=100, le=200)
    page_token: str | None = None
    window_start: int | None = None


class ReviewDecision(BaseModel):
    action: str
    application_id: str | None = None
    to_stage: str | None = None


@router.get("/status")
def status():
    return {"configured": gmail_sync.configured(), "connected": gmail_sync.connected()}


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
def messages():
    return {"messages": gmail_sync.saved_messages()}


@router.get("/reviews")
def reviews():
    return gmail_sync.pending_reviews()


@router.post("/reviews/{message_id}/resolve")
def resolve_review(message_id: str, decision: ReviewDecision):
    try:
        return gmail_sync.resolve_review(message_id, decision.action,
                                         decision.application_id, decision.to_stage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
