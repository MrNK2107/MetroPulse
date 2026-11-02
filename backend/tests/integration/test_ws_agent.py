"""/ws/agent: auth gate, connection limit, and a scripted end-to-end session.

The LLM and the database are replaced with fakes, so no network or Supabase is
needed. TestClient is used without its context manager so the app lifespan
(real-time ingestion loop) never starts.
"""
from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.ws.agent as agent_ws
from app.main import app

TOKEN = "test-agent-token"


class _FakeDb:
    pass


def _scripted_llm(responses: list[dict]):
    queue = [json.dumps(r) for r in responses]

    async def fake_call_llm(prompt: str) -> str:
        if not queue:
            return json.dumps({"type": "final", "content": "done"})
        return queue.pop(0)

    return fake_call_llm


@pytest.fixture
def client(monkeypatch):
    async def fake_get_db():
        return _FakeDb()

    monkeypatch.setattr(agent_ws.settings, "agent_ws_token", TOKEN)
    monkeypatch.setattr(agent_ws.settings, "ws_max_connections", 10)
    monkeypatch.setattr(agent_ws, "get_db", fake_get_db)
    monkeypatch.setattr(agent_ws.limiter, "active", 0)
    return TestClient(app)


def _assert_rejected(client: TestClient, url: str, code: int, **kwargs) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(url, **kwargs) as ws:
            ws.receive_text()
    assert exc.value.code == code


def test_route_is_mounted():
    assert app.url_path_for("agent_websocket") == "/ws/agent"


def test_disabled_when_no_token_configured(client, monkeypatch):
    monkeypatch.setattr(agent_ws.settings, "agent_ws_token", "")
    _assert_rejected(client, "/ws/agent?token=anything", agent_ws.WS_POLICY_VIOLATION)


def test_rejects_missing_token(client):
    _assert_rejected(client, "/ws/agent", agent_ws.WS_POLICY_VIOLATION)


def test_rejects_wrong_token(client):
    _assert_rejected(client, "/ws/agent?token=nope", agent_ws.WS_POLICY_VIOLATION)


def test_rejects_when_connection_limit_reached(client, monkeypatch):
    monkeypatch.setattr(agent_ws.settings, "ws_max_connections", 1)
    monkeypatch.setattr(agent_ws.limiter, "active", 1)
    _assert_rejected(client, f"/ws/agent?token={TOKEN}", agent_ws.WS_TRY_AGAIN_LATER)


def test_bearer_header_is_accepted_and_ping_pongs(client, monkeypatch):
    monkeypatch.setattr(agent_ws, "call_llm", _scripted_llm([]))
    with client.websocket_connect(
        "/ws/agent", headers={"Authorization": f"Bearer {TOKEN}"}
    ) as ws:
        ws.send_text(json.dumps({"type": "PING"}))
        assert ws.receive_json() == {"type": "PONG"}
        assert agent_ws.limiter.active == 1
    # Slot is released once the session ends.
    assert agent_ws.limiter.active == 0


def test_full_session_think_tool_ask_reply_final(client, monkeypatch):
    monkeypatch.setattr(agent_ws, "call_llm", _scripted_llm([
        {"type": "think", "content": "Need the city list first."},
        {"type": "tool_call", "tool": "list_cities", "args": {}},
        {"type": "ask", "question": "Which city?", "options": ["Pune", "Delhi"]},
        {"type": "final", "content": "Pune it is."},
    ]))
    with client.websocket_connect(f"/ws/agent?token={TOKEN}") as ws:
        ws.send_text("not json")
        assert ws.receive_json()["type"] == "AGENT_ERROR"
        ws.send_text(json.dumps({"type": "AGENT_START", "message": "hi"}))
        assert "too short" in ws.receive_json()["content"]

        ws.send_text(json.dumps({"type": "AGENT_START", "message": "Plan a metro line"}))
        assert ws.receive_json()["type"] == "AGENT_START"
        think = ws.receive_json()
        assert think["type"] == "AGENT_THINK" and "city list" in think["content"]
        action = ws.receive_json()
        assert action["type"] == "AGENT_ACTION" and action["tool"] == "list_cities"
        ask = ws.receive_json()
        assert ask["type"] == "AGENT_ASK" and ask["options"] == ["Pune", "Delhi"]

        ws.send_text(json.dumps({"type": "AGENT_REPLY", "message": "Pune"}))
        result = ws.receive_json()
        assert result["type"] == "AGENT_RESULT"
        assert result["content"] == "Pune it is."
        assert "list_cities" in result["summary"]["tools_used"]
        assert ws.receive_json()["type"] == "AGENT_DONE"
    assert agent_ws.limiter.active == 0


def test_internal_errors_are_not_leaked(client, monkeypatch):
    async def boom(prompt: str) -> str:
        raise RuntimeError("secret-key-sk-123 exploded")

    monkeypatch.setattr(agent_ws, "call_llm", boom)
    with client.websocket_connect(f"/ws/agent?token={TOKEN}") as ws:
        ws.send_text(json.dumps({"type": "AGENT_START", "message": "Plan a metro line"}))
        assert ws.receive_json()["type"] == "AGENT_START"
        err = ws.receive_json()
        assert err["type"] == "AGENT_ERROR"
        assert "secret" not in err["content"]
    assert agent_ws.limiter.active == 0


def test_limiter_never_goes_negative():
    lim = agent_ws.ConnectionLimiter()
    assert lim.try_acquire(1) is True
    assert lim.try_acquire(1) is False
    lim.release()
    lim.release()
    assert lim.active == 0
    assert lim.try_acquire(0) is False


def test_status_reports_disabled_without_token(client, monkeypatch):
    monkeypatch.setattr(agent_ws.settings, "agent_ws_token", "")
    body = client.get("/api/agent/status").json()
    assert body["success"] is True
    assert body["data"] == {"enabled": False, "available": False, "path": "/ws/agent"}


def test_status_reports_enabled_and_capacity_without_leaking_token(client, monkeypatch):
    res = client.get("/api/agent/status")
    assert res.status_code == 200
    assert TOKEN not in res.text
    assert res.json()["data"]["enabled"] is True
    assert res.json()["data"]["available"] is True
    monkeypatch.setattr(agent_ws.settings, "ws_max_connections", 1)
    monkeypatch.setattr(agent_ws.limiter, "active", 1)
    assert client.get("/api/agent/status").json()["data"]["available"] is False
