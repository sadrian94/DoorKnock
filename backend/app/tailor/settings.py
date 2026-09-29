"""User preferences for resume document generation."""

import json
from typing import Any

from ..config import WORKSPACE_DIR

SETTINGS_PATH = WORKSPACE_DIR / "resume-settings.json"
DEFAULT_SETTINGS = {"require_single_page": False}


def get_resume_settings() -> dict[str, bool]:
    """Read resume preferences, defaulting safely when no valid file exists."""
    try:
        saved: Any = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    require_single_page = saved.get("require_single_page", DEFAULT_SETTINGS["require_single_page"])
    if not isinstance(require_single_page, bool):
        require_single_page = DEFAULT_SETTINGS["require_single_page"]
    return {"require_single_page": require_single_page}


def save_resume_settings(require_single_page: bool) -> dict[str, bool]:
    """Persist resume preferences without storing candidate data."""
    if not isinstance(require_single_page, bool):
        raise ValueError("require_single_page must be a boolean")
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = SETTINGS_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps({"require_single_page": require_single_page}), encoding="utf-8"
    )
    temporary_path.replace(SETTINGS_PATH)
    return get_resume_settings()
