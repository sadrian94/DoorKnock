import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.parametrize("url", ["/", "/index.html", "/dashboard", "/?v=current-build"])
def test_spa_entry_prevents_reusing_old_bundle_references(tmp_path, monkeypatch, url):
    main = importlib.import_module("app.main")
    dist = tmp_path / "dist"
    dist.mkdir()
    index = dist / "index.html"
    index.write_text('<script src="/assets/old-build.js"></script>', encoding="utf-8")
    monkeypatch.setattr(main, "FRONTEND_DIST", dist)
    frontend = FastAPI()
    frontend.add_api_route("/{full_path:path}", main.serve_spa, methods=["GET"])

    with TestClient(frontend) as client:
        first = client.get(url)
        assert first.status_code == 200
        assert "no-store" in first.headers.get("cache-control", "")
        index.write_text('<script src="/assets/new-build.js"></script>', encoding="utf-8")
        updated = client.get(url, headers={"If-None-Match": first.headers["etag"]})
        assert updated.status_code == 200
        assert "no-store" in updated.headers.get("cache-control", "")
        assert "/assets/new-build.js" in updated.text
        assert "/assets/old-build.js" not in updated.text
