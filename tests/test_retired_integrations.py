from fastapi.testclient import TestClient

from app import documents
from app.main import app


def test_retired_sync_endpoint_is_not_available():
    with TestClient(app) as client:
        response = client.post("/api/sync/job-ops")

    assert response.status_code in {404, 405}


def test_unregistered_api_get_returns_not_found():
    with TestClient(app) as client:
        response = client.get("/api/unregistered-resource")

    assert response.status_code == 404


def test_document_lookup_ignores_external_application_folder(tmp_path, monkeypatch):
    job_id = "synthetic-external-job"
    workspace = tmp_path / "workspace"
    applications_dir = workspace / "applications"
    external_root = tmp_path / "external-system"
    external_applications = external_root / "workspace" / "applications"
    external_resume = external_applications / job_id / "resume"
    external_resume.mkdir(parents=True)
    (external_resume / "final.pdf").write_bytes(b"synthetic pdf fixture")

    monkeypatch.setattr(documents, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(documents, "APPLICATIONS_DIR", applications_dir)
    monkeypatch.setattr(
        documents,
        "HIREFLOW_APPLICATIONS_DIR",
        external_applications,
        raising=False,
    )
    monkeypatch.setattr(documents, "HIREFLOW_DIR", external_root, raising=False)

    assert documents.find_application_directory(job_id) is None
    assert documents.resolve_document_file_path(job_id, "resume") is None
