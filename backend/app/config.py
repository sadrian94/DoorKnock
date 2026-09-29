from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

def get_db_path() -> Path:
    env_path = os.getenv("DOORKNOCK_DB_PATH")
    if env_path:
        return Path(env_path)
    return DATA_DIR / "jobs.db"

DOORKNOCK_DB_PATH = get_db_path()

# Load .env
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Gemini configuration (model requested: gemini-3.5-flash-lite, configurable via .env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Candidate PII isolated workspace
WORKSPACE_DIR = BASE_DIR / "workspace"
APPLICATIONS_DIR = WORKSPACE_DIR / "applications"
DOORKNOCK_MASTER_EVIDENCE_YAML_PATH = WORKSPACE_DIR / "master_resume" / "master_evidence.yaml"


CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
