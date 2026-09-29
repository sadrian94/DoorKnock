import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
from .config import get_db_path, DATA_DIR

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def init_db(db_path: Optional[Path] = None):
    target_path = db_path or get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db(target_path) as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN analysis_json TEXT;")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN company_recon_json TEXT;")
        except Exception:
            pass
        conn.commit()

@contextmanager
def get_db(db_path: Optional[Path] = None):
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    try:
        yield conn
    finally:
        conn.close()
