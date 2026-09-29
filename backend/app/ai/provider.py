"""Shared interface and selection for text generation providers."""

import json
import os
from typing import Any, Optional, Protocol

from ..config import WORKSPACE_DIR, GEMINI_MODEL
from .gemini import GeminiClient
from .codex import CodexClient

SETTINGS_PATH = WORKSPACE_DIR / "ai-settings.json"


class AIClient(Protocol):
    def is_configured(self) -> bool: ...
    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> dict[str, Any]: ...


def get_settings() -> dict[str, Any]:
    saved: dict[str, Any] = {}
    if SETTINGS_PATH.is_file():
        try:
            saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
    provider = saved.get("provider", "gemini")
    if provider not in ("gemini", "codex"):
        provider = "gemini"
    if provider == "codex":
        # Empty means Codex chooses its configured default model.
        model = saved.get("model", "")
        if model == "default":
            model = ""
    else:
        model = saved.get("model") or GEMINI_MODEL
    configured = bool(os.getenv("GEMINI_API_KEY")) if provider == "gemini" else CodexClient().is_configured()
    return {"provider": provider, "model": model, "configured": configured}


def save_settings(provider: str, model: str) -> dict[str, Any]:
    if provider not in ("gemini", "codex"):
        raise ValueError("Unsupported AI provider")
    model = model.strip()
    if provider == "codex" and model == "default":
        model = ""
    if (not model and provider != "codex") or len(model) > 100 or any(c.isspace() for c in model):
        raise ValueError("Enter a valid model ID")
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = SETTINGS_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps({"provider": provider, "model": model}), encoding="utf-8")
    temp_path.replace(SETTINGS_PATH)
    return get_settings()


def get_ai_client() -> AIClient:
    settings = get_settings()
    if settings["provider"] == "codex":
        return CodexClient(model=settings["model"])
    return GeminiClient(model=settings["model"])


def require_ai_client() -> AIClient:
    client = get_ai_client()
    if not client.is_configured():
        provider = get_settings()["provider"]
        if provider == "codex":
            raise ValueError("Codex CLI is not installed or not on the server PATH")
        raise ValueError("GEMINI_API_KEY is not configured in the server environment")
    return client
