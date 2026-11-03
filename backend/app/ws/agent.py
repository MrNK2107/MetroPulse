"""`/ws/agent` — streaming ReAct agent over a WebSocket (M2 re-mount).

Guards, applied before any work is done for a connection:

* **Auth** — the endpoint is disabled unless ``AGENT_WS_TOKEN`` is set. Clients
  present the token as ``?token=...`` or an ``Authorization: Bearer ...`` header;
  it is compared in constant time. Failures close with 1008 (policy violation)
  before the socket is accepted.
* **Connection limit** — at most ``WS_MAX_CONNECTIONS`` concurrent agent
  sessions. Extra connections are closed with 1013 (try again later).

Errors sent to the client are generic; details go to the server log only.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.db import get_db
from app.llm import call_llm
from engine.agent import UrbanAgent, AgentTools
from engine.config import CityConfig

logger = logging.getLogger(__name__)
router = APIRouter()

WS_POLICY_VIOLATION = 1008
WS_TRY_AGAIN_LATER = 1013
MAX_MESSAGE_CHARS = 4000


class ConnectionLimiter:
    """Counts live sessions; all access happens on the event loop thread."""

    def __init__(self) -> None:
        self.active = 0

    def try_acquire(self, limit: int) -> bool:
        if self.active >= max(0, limit):
            return False
        self.active += 1
        return True

    def release(self) -> None:
        self.active = max(0, self.active - 1)


limiter = ConnectionLimiter()


def _presented_token(websocket: WebSocket) -> str:
    token = websocket.query_params.get("token", "")
    if token:
        return token
    auth = websocket.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def is_authorized(websocket: WebSocket) -> bool:
    expected = settings.agent_ws_token
    if not expected:
        return False
    presented = _presented_token(websocket)
    return bool(presented) and hmac.compare_digest(
        presented.encode("utf-8"), expected.encode("utf-8")
    )


@router.get("/api/agent/status")
async def agent_status():
    """Lets the UI tell "disabled" apart from "bad token" / "server down".

    A browser cannot read the close code of a socket rejected before accept
    (it only sees 1006), so the chat client asks here first. Never reveals the
    token itself.
    """
    enabled = bool(settings.agent_ws_token)
    return {
        "success": True,
        "data": {
            "enabled": enabled,
            "available": enabled and limiter.active < max(0, settings.ws_max_connections),
            "path": "/ws/agent",
        },
        "error": None,
        "meta": {},
    }


@router.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    if not is_authorized(websocket):
        reason = "unauthorized" if settings.agent_ws_token else "agent websocket disabled"
        await websocket.close(code=WS_POLICY_VIOLATION, reason=reason)
        return

    if not limiter.try_acquire(settings.ws_max_connections):
        await websocket.close(code=WS_TRY_AGAIN_LATER, reason="too many connections")
        return

    try:
        await websocket.accept()
        await _run_session(websocket)
    finally:
        limiter.release()


async def _run_session(websocket: WebSocket) -> None:
    agent_id = str(uuid4())
    db = await get_db()

    city_configs: dict[str, CityConfig] = {}
    agent_tools = AgentTools(db=db, city_configs=city_configs)
    agent = UrbanAgent(llm_fn=call_llm, tools=agent_tools)

    try:
        data = await _receive_agent_start(websocket)
        user_message = data["message"]

        await websocket.send_json({
            "type": "AGENT_START",
            "agentId": agent_id,
        })

        async for event in agent.run(user_message):
            event_type = event.get("type", "")

            if event_type == "agent_think":
                await websocket.send_json({
                    "type": "AGENT_THINK",
                    "content": event.get("content", ""),
                    "step": agent._step_count,
                })

            elif event_type == "agent_action":
                await websocket.send_json({
                    "type": "AGENT_ACTION",
                    "tool": event.get("tool", ""),
                    "args": event.get("args", {}),
                    "step": agent._step_count,
                })

            elif event_type == "agent_ask":
                await websocket.send_json({
                    "type": "AGENT_ASK",
                    "question": event.get("question", ""),
                    "options": event.get("options", []),
                    "step": agent._step_count,
                })

            elif event_type == "__wait_for_reply":
                response_data = await _receive_agent_response(websocket)
                agent.provide_reply(response_data.get("text", ""))

            elif event_type == "agent_result":
                await websocket.send_json({
                    "type": "AGENT_RESULT",
                    "content": event.get("content", ""),
                    "summary": event.get("summary", {}),
                    "step": agent._step_count,
                })
                await websocket.send_json({"type": "AGENT_DONE", "agentId": agent_id})

            elif event_type == "agent_error":
                await websocket.send_json({
                    "type": "AGENT_ERROR",
                    "content": event.get("content", "Unknown error"),
                })

    except WebSocketDisconnect:
        logger.info("Agent %s: client disconnected", agent_id)
        return
    except asyncio.TimeoutError:
        await _safe_send(websocket, {
            "type": "AGENT_ERROR",
            "content": "Timed out waiting for your response. Please start again.",
        })
    except Exception:
        logger.exception("Agent %s failed", agent_id)
        await _safe_send(websocket, {
            "type": "AGENT_ERROR",
            "content": "The agent hit an internal error. Please try again.",
        })
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


def _clip(text: object) -> str:
    return str(text or "").strip()[:MAX_MESSAGE_CHARS]


async def _receive_agent_start(websocket: WebSocket) -> dict:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 30.0
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        message = await asyncio.wait_for(websocket.receive_text(), timeout=remaining)
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            await _safe_send(websocket, {"type": "AGENT_ERROR", "content": "Invalid JSON."})
            continue
        if not isinstance(payload, dict):
            await _safe_send(websocket, {"type": "AGENT_ERROR", "content": "Expected a JSON object."})
            continue
        if payload.get("type") == "PING":
            await _safe_send(websocket, {"type": "PONG"})
            continue
        if payload.get("type") == "AGENT_START":
            text = _clip(payload.get("message"))
            if len(text) < 4:
                await _safe_send(websocket, {
                    "type": "AGENT_ERROR",
                    "content": "Message too short. Describe your urban planning goal.",
                })
                continue
            return {"message": text}
        await _safe_send(websocket, {
            "type": "AGENT_ERROR",
            "content": "Send { type: 'AGENT_START', message: '...' }",
        })


async def _receive_agent_response(websocket: WebSocket) -> dict:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 120.0
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        message = await asyncio.wait_for(websocket.receive_text(), timeout=min(remaining, 60.0))
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("type") == "PING":
            await _safe_send(websocket, {"type": "PONG"})
            continue
        if payload.get("type") == "AGENT_REPLY":
            return {"text": _clip(payload.get("message"))}
        await _safe_send(websocket, {
            "type": "AGENT_ERROR",
            "content": "Expected { type: 'AGENT_REPLY', message: '...' }",
        })


async def _safe_send(websocket: WebSocket, data: dict) -> None:
    try:
        await websocket.send_json(data)
    except Exception:
        pass
