import os
import sys
from pathlib import Path
import pytest

# Ensure backend directory is in sys.path for test discovery
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

@pytest.fixture(scope="session", autouse=True)
def isolate_test_db(tmp_path_factory):
    """
    Ensure all tests run against a fresh isolated SQLite database.
    """
    temp_dir = tmp_path_factory.mktemp("doorknock_test_db")
    test_db_path = temp_dir / "test_jobs.db"

    old_env = os.environ.get("DOORKNOCK_DB_PATH")
    os.environ["DOORKNOCK_DB_PATH"] = str(test_db_path)

    import app.config as config
    config.DOORKNOCK_DB_PATH = test_db_path

    from app.database import init_db
    init_db(test_db_path)

    yield test_db_path

    if old_env is not None:
        os.environ["DOORKNOCK_DB_PATH"] = old_env
        config.DOORKNOCK_DB_PATH = config.get_db_path()
    else:
        os.environ.pop("DOORKNOCK_DB_PATH", None)
        config.DOORKNOCK_DB_PATH = config.get_db_path()
