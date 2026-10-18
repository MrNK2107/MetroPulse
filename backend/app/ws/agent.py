from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket

from app.db import get_db
from app.simulation.llm import call_llm
from engine.agent import UrbanAgent, AgentTools
from engine.config import CityConfig

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    await websocket.accept()
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

    except asyncio.TimeoutError:
        await _safe_send(websocket, {
            "type": "AGENT_ERROR",
            "content": "Timed out waiting for your response. Please start again.",
        })
    except Exception as e:
        logger.exception("Agent %s failed", agent_id)
        await _safe_send(websocket, {
            "type": "AGENT_ERROR",
            "content": f"Agent encountered an error: {e}",
        })
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


async def _receive_agent_start(websocket: WebSocket) -> dict:
    deadline = asyncio.get_event_loop().time() + 30.0
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        message = await asyncio.wait_for(websocket.receive_text(), timeout=remaining)
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            await _safe_send(websocket, {"type": "AGENT_ERROR", "content": "Invalid JSON."})
            continue
        if payload.get("type") == "PING":
            await _safe_send(websocket, {"type": "PONG"})
            continue
        if payload.get("type") == "AGENT_START":
            text = payload.get("message", "").strip()
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
    deadline = asyncio.get_event_loop().time() + 120.0
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        message = await asyncio.wait_for(websocket.receive_text(), timeout=min(remaining, 60.0))
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "PING":
            await _safe_send(websocket, {"type": "PONG"})
            continue
        if payload.get("type") == "AGENT_REPLY":
            return {"text": payload.get("message", "")}
        await _safe_send(websocket, {
            "type": "AGENT_ERROR",
            "content": "Expected { type: 'AGENT_REPLY', message: '...' }",
        })


async def _safe_send(websocket: WebSocket, data: dict) -> None:
    try:
        await websocket.send_json(data)
    except Exception:
        pass
