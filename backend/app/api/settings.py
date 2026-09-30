from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..ai.provider import get_settings, save_settings
from ..ai.codex import app_server, CodexError
from ..tailor.settings import get_resume_settings, save_resume_settings
from ..clock import get_time_settings, save_time_settings, timezone_names, utc_now

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AISettingsRequest(BaseModel):
    provider: str
    model: str


class ResumeSettingsRequest(BaseModel):
    require_single_page: bool


class TimeSettingsRequest(BaseModel):
    timezone: str


@router.get("/time")
def read_time_settings():
    return {**get_time_settings(), "available_timezones": timezone_names(),
            "current_time": utc_now().isoformat()}


@router.put("/time")
def update_time_settings(request: TimeSettingsRequest):
    try:
        return save_time_settings(request.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ai")
def read_ai_settings():
    return get_settings()


@router.put("/ai")
def update_ai_settings(request: AISettingsRequest):
    try:
        return save_settings(request.provider, request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/resume")
def read_resume_settings():
    return get_resume_settings()


@router.put("/resume")
def update_resume_settings(request: ResumeSettingsRequest):
    try:
        return save_resume_settings(request.require_single_page)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/codex/status")
async def codex_status():
    try:
        return await app_server.status()
    except (CodexError, OSError):
        return {"connected": False, "auth_type": None}


@router.post("/codex/connect")
async def codex_connect():
    try:
        data = await app_server.start_login()
        return {"auth_url": data.get("authUrl")}
    except (CodexError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
