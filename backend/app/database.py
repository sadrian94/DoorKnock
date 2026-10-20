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
        if 'company_recon_status' not in {row['name'] for row in conn.execute('PRAGMA table_info(jobs)')}:
            conn.execute('ALTER TABLE jobs ADD COLUMN company_recon_status TEXT')
        if 'resolution_metadata' not in {row['name'] for row in conn.execute('PRAGMA table_info(gmail_review_items)')}:
            conn.execute('ALTER TABLE gmail_review_items ADD COLUMN resolution_metadata TEXT')
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN analysis_json TEXT;")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN company_recon_json TEXT;")
        except Exception:
            pass
        # Existing tables retain their original SQLite defaults. Normalize only
        # newly inserted SQLite UTC defaults; leave historical values untouched.
        for table, columns in {
            "jobs": ("created_at", "updated_at"),
            "job_artifacts": ("created_at", "updated_at"),
            "contacts": ("created_at",),
            "outreach_messages": ("created_at", "updated_at"),
            "applications": ("created_at", "updated_at"),
            "timeline_events": ("occurred_at",),
            "gmail_application_messages": ("created_at",),
            "gmail_review_items": ("created_at",),
        }.items():
            for column in columns:
                conn.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS utc_insert_{table}_{column}
                    AFTER INSERT ON {table}
                    WHEN NEW.{column} GLOB '????-??-?? ??:??:??'
                    BEGIN
                        UPDATE {table}
                        SET {column} = replace(NEW.{column}, ' ', 'T') || 'Z'
                        WHERE rowid = NEW.rowid;
                    END
                """)
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
