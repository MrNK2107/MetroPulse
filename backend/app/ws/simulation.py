from __future__ import annotations

import json
import logging
import asyncio
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from engine.models import SimulationParams
from engine.runner import run_simulation, set_deadline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/simulate")
async def simulation_websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
    except asyncio.TimeoutError:
        await websocket.send_json({
            "type": "ERROR",
            "code": "TIMEOUT",
            "message": "Did not receive START message within 30 seconds",
        })
        await websocket.close()
        return

    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        await websocket.send_json({
            "type": "ERROR",
            "code": "INVALID_JSON",
            "message": "Message must be valid JSON",
        })
        await websocket.close()
        return

    if data.get("type") != "START":
        await websocket.send_json({
            "type": "ERROR",
            "code": "INVALID_MESSAGE_TYPE",
            "message": "First message must have type 'START'",
        })
        await websocket.close()
        return

    try:
        params = SimulationParams(**data["params"])
    except Exception as e:
        await websocket.send_json({
            "type": "ERROR",
            "code": "VALIDATION_ERROR",
            "message": f"Invalid simulation params: {e}",
        })
        await websocket.close()
        return

    region_boundary = {
        "type": "Polygon",
        "coordinates": [[
            [-74.025, 40.700],
            [-73.925, 40.700],
            [-73.925, 40.795],
            [-74.025, 40.795],
            [-74.025, 40.700],
        ]],
    }

    set_deadline(settings.sim_timeout_ms)
    simulation_id = str(uuid4())

    try:
        async for frame in run_simulation(params, region_boundary):
            try:
                if "type" in frame and frame["type"] == "INSIGHT":
                    await websocket.send_json({
                        "type": "INSIGHT",
                        "markdown": frame["markdown"],
                    })
                else:
                    await websocket.send_json({
                        "type": "FRAME",
                        "payload": frame,
                    })
            except Exception:
                break

        await websocket.send_json({
            "type": "DONE",
            "simulationId": simulation_id,
        })

    except asyncio.CancelledError:
        logger.info(f"Simulation {simulation_id} cancelled (client disconnected)")
    except Exception as e:
        logger.exception(f"Simulation {simulation_id} failed")
        try:
            await websocket.send_json({
                "type": "ERROR",
                "code": "SIMULATION_FAILED",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
