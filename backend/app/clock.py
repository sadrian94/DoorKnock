"""UTC event clocks and the user-selected local calendar. Never use host TZ."""

from datetime import date, datetime, timezone
from functools import lru_cache
import json
import os
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo, available_timezones

from .config import WORKSPACE_DIR

SETTINGS_PATH = WORKSPACE_DIR / "time-settings.json"
DEFAULT_TIMEZONE = "America/Chicago"


@lru_cache(maxsize=1)
def timezone_names() -> tuple[str, ...]:
    # IANA's Factory placeholder means an unspecified zone, not a user choice.
    return tuple(sorted(available_timezones() - {"Factory"}))


def get_time_settings() -> dict[str, str]:
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    name = saved.get("timezone") if isinstance(saved, dict) else None
    if not isinstance(name, str) or name not in timezone_names():
        name = DEFAULT_TIMEZONE
    return {"timezone": name}


def save_time_settings(name: str) -> dict[str, str]:
    if name not in timezone_names():
        raise ValueError("Choose a valid IANA time zone, such as America/Chicago")
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Unique temp files prevent concurrent settings saves from sharing a file.
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=SETTINGS_PATH.parent,
                            prefix="time-settings-", suffix=".tmp", delete=False) as handle:
        json.dump({"timezone": name}, handle)
        temporary_path = handle.name
    try:
        os.replace(temporary_path, SETTINGS_PATH)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return {"timezone": name}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    return utc_now().astimezone(ZoneInfo(get_time_settings()["timezone"]))


def local_today() -> date:
    return local_now().date()


def local_date_of(instant: str) -> str:
    """Convert an explicit event instant to the selected calendar date."""
    parsed = datetime.fromisoformat(instant)
    if parsed.tzinfo is None:
        raise ValueError("Event time must include a time zone")
    return parsed.astimezone(ZoneInfo(get_time_settings()["timezone"])).date().isoformat()
