from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket
from pydantic import ValidationError

from app.config import settings
from app.db import get_db
from engine.models import StartScenarioMessage
from engine.prediction_generator import generate_prediction
from engine.runner import run_simulation, SimulationTimeoutError
from engine.scenario_parser import ScenarioParseError, build_params, parse_scenario
from engine.tertiary_loop import synthesize_evidence

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/simulate")
async def simulation_websocket(websocket: WebSocket):
    await websocket.accept()
    simulation_id = str(uuid4())
    db = await get_db()

    try:
        data = await _receive_start(websocket)
        await _send_stage(websocket, "parsing", "Reading the scenario and resolving city, sectors, policy, and horizon.")
        parsed = await parse_scenario(data.scenario)

        params = build_params(parsed)
        boundary = await db.get_region_boundary(params.city)
        if boundary is None:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "parsing",
                "code": "CITY_DATA_MISSING",
                "message": f"No boundary data found for {params.city}.",
            })
            return

        await websocket.send_json({"type": "PARSED", "params": parsed.model_dump(), "boundary": boundary})

        await _send_stage(websocket, "predicting", "Generating a before-simulation expectation to compare against the math.")
        prediction = await generate_prediction(params)
        await websocket.send_json({"type": "PREDICTION", "prediction": prediction.model_dump()})

        await _send_stage(websocket, "simulating", "Animating monthly H3 cell changes across the city.")
        deadline = asyncio.get_running_loop().time() + settings.sim_timeout_ms / 1000.0
        final_frame = None
        async for frame in run_simulation(params, boundary, db=db, deadline=deadline):
            final_frame = frame
            await websocket.send_json({"type": "FRAME", "payload": frame})

        if final_frame is None:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "simulating",
                "code": "NO_FRAMES",
                "message": "Simulation produced no frames.",
            })
            return

        await _send_stage(websocket, "retrieving", "Finding Indian urban precedents that match the scenario.")
        case_studies = await db.search_case_studies(
            parsed.keywords,
            city=parsed.city,
            top_k=5,
        )
        await websocket.send_json({
            "type": "CASE_STUDIES",
            "studies": [case.model_dump() for case in case_studies],
        })

        await _send_stage(websocket, "synthesizing", "Comparing prediction vs simulation and preparing proof.")
        evidence = synthesize_evidence(params, prediction, final_frame, case_studies)
        await websocket.send_json({"type": "EVIDENCE", "evidence": evidence})

        saved_id = await db.save_simulation(
            region_id=None,
            params=params.to_dict(),
            horizon_months=params.horizon_months,
            result_summary=final_frame["metrics"],
            cell_states=final_frame["cells"],
        )
        await websocket.send_json({"type": "DONE", "simulationId": saved_id or simulation_id})

    except ScenarioParseError as e:
        await websocket.send_json({
            "type": "ERROR",
            "stage": "parsing",
            "code": "CLARIFICATION_NEEDED",
            "message": str(e),
        })
    except asyncio.TimeoutError:
        await websocket.send_json({
            "type": "ERROR",
            "stage": "parsing",
            "code": "TIMEOUT",
            "message": "Did not receive START message within 30 seconds.",
        })
    except SimulationTimeoutError:
        await websocket.send_json({
            "type": "ERROR",
            "stage": "simulating",
            "code": "TIMEOUT",
            "message": "Simulation exceeded the time limit. Try a shorter horizon or fewer sector changes.",
        })
    except Exception as e:
        logger.exception("Simulation %s failed", simulation_id)
        try:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "simulating",
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


async def _receive_start(websocket: WebSocket) -> StartScenarioMessage:
    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
    try:
        payload = json.loads(message)
        return StartScenarioMessage(**payload)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ScenarioParseError(f"First message must be valid JSON shaped as {{ type: 'START', scenario: '...' }}. {e}") from e


async def _send_stage(websocket: WebSocket, stage: str, message: str) -> None:
    await websocket.send_json({"type": "STAGE", "stage": stage, "message": message})
