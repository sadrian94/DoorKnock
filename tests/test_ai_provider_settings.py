import json
import pytest
from fastapi.testclient import TestClient

from app.ai import provider
from app.ai.gemini import GeminiClient
from app.ai.codex import CodexClient
from app.ai.codex import CodexAppServer
from app.main import app


def test_settings_switch_provider_without_persisting_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(provider, "SETTINGS_PATH", tmp_path / "ai-settings.json")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-gemini-key")
    monkeypatch.setattr("app.ai.codex.shutil.which", lambda _: "synthetic-codex")

    assert isinstance(provider.get_ai_client(), GeminiClient)
    settings = provider.save_settings("codex", "")

    assert settings == {"provider": "codex", "model": "", "configured": True}
    assert isinstance(provider.get_ai_client(), CodexClient)
    assert json.loads(provider.SETTINGS_PATH.read_text()) == {
        "provider": "codex", "model": ""
    }


def test_settings_reject_unknown_provider_and_invalid_model(tmp_path, monkeypatch):
    monkeypatch.setattr(provider, "SETTINGS_PATH", tmp_path / "ai-settings.json")
    for name, model in (("unknown", "model"), ("codex", "bad model")):
        try:
            provider.save_settings(name, model)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid provider setting was accepted")
    assert not provider.SETTINGS_PATH.exists()


def test_existing_codex_default_setting_displays_blank(tmp_path, monkeypatch):
    monkeypatch.setattr(provider, "SETTINGS_PATH", tmp_path / "ai-settings.json")
    provider.SETTINGS_PATH.write_text('{"provider":"codex","model":"default"}')
    assert provider.get_settings()["model"] == ""


def test_settings_api_never_returns_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(provider, "SETTINGS_PATH", tmp_path / "ai-settings.json")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-private-token")
    with TestClient(app) as client:
        response = client.put("/api/settings/ai", json={"provider": "gemini", "model": "gemini-3.5-flash-lite"})
        assert response.status_code == 200
        assert response.json()["configured"] is True
        assert "synthetic-private-token" not in response.text
        assert "synthetic-private-token" not in client.get("/api/settings/ai").text


@pytest.mark.anyio
async def test_codex_adapter_reads_completed_json_without_api_key(monkeypatch):
    server = CodexAppServer()

    async def connected():
        return {"connected": True}

    async def fake_call(method, params):
        if method == "thread/start":
            assert params["sandbox"] == "read-only"
            return {"thread": {"id": "thread-test"}}
        assert method == "turn/start"
        assert params["approvalPolicy"] == "never"
        return {"turn": {"id": "turn-test"}}

    monkeypatch.setattr(server, "status", connected)
    monkeypatch.setattr(server, "call", fake_call)
    server.events.put({"method": "item/completed", "params": {
        "threadId": "thread-test", "item": {"type": "agentMessage", "text": '{"answer":"ok"}'}}})
    server.events.put({"method": "turn/completed", "params": {
        "turn": {"id": "turn-test", "status": "completed"}}})
    assert await server.generate_json("Return an answer", "Use synthetic input", "") == {"answer": "ok"}
