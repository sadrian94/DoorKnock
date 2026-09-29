from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from .config import CORS_ORIGINS
from .database import init_db
from .api.jobs import router as jobs_router
from .api.pipeline import router as pipeline_router
from .api.import_job import router as import_router
from .api.documents import router as documents_router
from .api.settings import router as settings_router
from .api.gmail import router as gmail_router
from .ai.codex import app_server

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        yield
    finally:
        await app_server.close()

app = FastAPI(title="DoorKnock (敲門) API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(jobs_router)
app.include_router(pipeline_router)
app.include_router(import_router)
app.include_router(documents_router)
app.include_router(settings_router)
app.include_router(gmail_router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "DoorKnock"}

# Static Frontend Serving
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _frontend_file(full_path: str) -> Path | None:
    """Return an existing file only when its resolved path stays inside the build."""
    try:
        root = FRONTEND_DIST.resolve(strict=True)
        candidate = (root / full_path).resolve(strict=True)
        candidate.relative_to(root)
        return candidate if candidate.is_file() else None
    except (OSError, RuntimeError, ValueError):
        return None


async def serve_spa(full_path: str):
    # Do not catch API routes
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    file_path = _frontend_file(full_path)
    if file_path is not None:
        return FileResponse(file_path)
    index_file = _frontend_file("index.html")
    if index_file is not None:
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"error": "Not found"})


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    app.add_api_route("/{full_path:path}", serve_spa, methods=["GET"])
