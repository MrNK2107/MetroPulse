from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket
from pydantic import ValidationError

from app.config import settings
from app.db import build_case_study_context, get_db
from app.rag import build_evidence_pack, coefficient_factors, extract_coefficient_adjustments
from app.realtime import build_demo_manifest, snapshot_quality
from app.realtime_models import SnapshotData, utc_now
from engine.models import AggregateMetrics, StartScenarioMessage, InputResponseMessage
from engine.prediction_generator import generate_prediction
from engine.runner import run_simulation, SimulationTimeoutError
from engine.scenario_parser import ScenarioParseError, build_params
from engine.tertiary_loop import synthesize_evidence
from engine.nl_engine.router import IntentRouter
from engine.nl_engine.conversation import ConversationManager, ConversationMode
from engine.nl_engine.group_scorer import score_groups, compute_satisfaction

logger = logging.getLogger(__name__)
router = APIRouter()

_intent_router = IntentRouter()


@router.websocket("/ws/simulate")
async def simulation_websocket(websocket: WebSocket):
    await websocket.accept()
    simulation_id = str(uuid4())
    db = await get_db()

    conv = ConversationManager()

    try:
        data = await _receive_start(websocket)
        scenario_text = data.scenario

        # ── Parsing stage with conversation ──────────────────────────
        await _send_stage(websocket, "parsing", "Reading your scenario...")
        
        is_json = False
        if scenario_text.strip().startswith("{"):
            try:
                parsed_data = json.loads(scenario_text)
                from engine.models import ParsedScenario, SECTOR_NAMES
                # Reconstruct parsed scenario directly
                sector_deltas = {
                    s: float(parsed_data.get("sector_deltas", {}).get(s, 0.0))
                    for s in SECTOR_NAMES
                }
                parsed = ParsedScenario(
                    city=parsed_data.get("city", "mumbai"),
                    sector_deltas=sector_deltas,
                    policies_active=list(parsed_data.get("policies_active", [])),
                    public_works_zone=parsed_data.get("public_works_zone"),
                    horizon_months=int(parsed_data.get("horizon_months", 24)),
                    causal_chain=parsed_data.get("causal_chain", "Direct parameter specification"),
                    keywords=list(parsed_data.get("keywords", ["mumbai"])),
                    confidence="high",
                    assumptions=list(parsed_data.get("assumptions", ["Direct numeric specification by user."])),
                )
                confidence = 1.0
                conv.mode = ConversationMode.DEEP
                is_json = True
            except Exception as e:
                logger.warning("Failed to parse scenario as JSON, falling back to NLP routing: %s", e)
        
        if not is_json:
            parsed, confidence = await _intent_router.route(scenario_text)
            conv.mode = conv.detect_mode(scenario_text)

        # If low confidence or incomplete params, ask follow-up
        followup = conv.get_followup(parsed)
        if followup and conv.mode == ConversationMode.QUICK:
            options = conv.get_followup_options(parsed)
            await websocket.send_json({
                "type": "NEEDS_INPUT",
                "question": followup,
                "inferred_params": {
                    "city": parsed.city,
                    "sectors": [
                        {"name": s, "delta": d}
                        for s, d in parsed.sector_deltas.items()
                        if d != 0.0
                    ],
                },
                "options": options,
                "mode": conv.mode.value,
            })

            # Wait for user response
            response_data = await _receive_input_response(websocket)
            combined_text = f"{scenario_text} {response_data.text}"
            parsed, confidence = await _intent_router.route(combined_text)

        # Ensure we have a city
        if not parsed.city:
            from engine.config import list_available_cities
            supported = ", ".join(c["name"] for c in list_available_cities()[:8])
            await websocket.send_json({
                "type": "ERROR",
                "stage": "parsing",
                "code": "CLARIFICATION_NEEDED",
                "message": (
                    "I couldn't find a city in your scenario. "
                    f"Supported cities: {supported}. "
                    "Example: 'What happens to Hyderabad if pharma FDI drops 40%?'"
                ),
            })
            return

        params = build_params(parsed)
        snapshot = await db.get_latest_snapshot(params.city)
        quality = snapshot_quality(snapshot)
        if snapshot is None:
            if settings.realtime_mode_required:
                await websocket.send_json({
                    "type": "ERROR",
                    "stage": "parsing",
                    "code": "REALTIME_SNAPSHOT_UNAVAILABLE",
                    "message": (
                        "Real-Time Mode has no usable Bengaluru snapshot yet. "
                        "Run ingestion or disable REALTIME_MODE_REQUIRED to use explicit Demo Mode."
                    ),
                })
                return
            snapshot = SnapshotData(
                id=f"demo-{params.city}",
                city=params.city,
                snapshot_at=utc_now(),
                status="demo",
                quality_score=0.25,
                source_manifest=build_demo_manifest(),
            )
            quality = snapshot_quality(snapshot)
        params.realtime_snapshot = snapshot
        evidence_pack = build_evidence_pack(parsed, scenario_text)
        coefficient_adjustments = extract_coefficient_adjustments(parsed.sector_deltas, evidence_pack)
        params.evidence_pack = evidence_pack.model_dump()
        params.coefficient_adjustments = {
            sector: adjustment.model_dump()
            for sector, adjustment in coefficient_adjustments.items()
        }
        params.coefficient_factors = coefficient_factors(coefficient_adjustments)
        boundary = await db.get_region_boundary(params.city)
        if boundary is None:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "parsing",
                "code": "CITY_DATA_MISSING",
                "message": f"No boundary data found for {params.city}.",
            })
            return
        if quality.status == "degraded":
            await _send_stage(websocket, "parsing", quality.message)
        elif quality.status == "demo":
            await _send_stage(websocket, "parsing", quality.message)
        await websocket.send_json({
            "type": "PARSED",
            "params": parsed.model_dump(),
            "boundary": boundary,
            "snapshot": {
                "id": snapshot.id,
                "city": snapshot.city,
                "status": quality.status,
                "qualityScore": quality.quality_score,
                "sourceManifest": snapshot.manifest_for_json(),
            },
        })

        # ── Prediction stage ─────────────────────────────────────────
        prediction_source = "llm"
        await _send_stage(websocket, "predicting", "Generating a before-simulation expectation.")
        try:
            prediction = await generate_prediction(params)
        except Exception as e:
            logger.warning("Prediction generation failed, using deterministic fallback: %s", e)
            from engine.prediction_generator import _deterministic_prediction
            prediction = _deterministic_prediction(params)
            prediction_source = "deterministic_fallback"

        prediction_data = prediction.model_dump()
        prediction_data["source"] = prediction_source
        await websocket.send_json({"type": "PREDICTION", "prediction": prediction_data})

        # ── Simulation stage ─────────────────────────────────────────
        await _send_stage(websocket, "simulating", "Animating monthly H3 cell changes across the city.")
        deadline = asyncio.get_running_loop().time() + settings.sim_timeout_ms / 1000.0
        frames = []
        grid_state_ref: list = []
        try:
            async for frame in run_simulation(params, boundary, db=None, deadline=deadline, state_ref=grid_state_ref):
                frames.append(frame)
                await websocket.send_json({"type": "FRAME", "payload": frame})
        except SimulationTimeoutError:
            raise
        except Exception as e:
            logger.error("Simulation loop failed at frame %d: %s", len(frames), e)
            if not frames:
                await websocket.send_json({
                    "type": "ERROR",
                    "stage": "simulating",
                    "code": "SIMULATION_FAILED",
                    "message": f"Simulation failed: {e}",
                })
                return

        if not frames:
            await websocket.send_json({
                "type": "ERROR",
                "stage": "simulating",
                "code": "NO_FRAMES",
                "message": "Simulation produced no frames.",
            })
            return

        final_frame = frames[-1]

        # ── Case studies stage ───────────────────────────────────────
        case_studies = []
        case_context = build_case_study_context(parsed, original_query=scenario_text)
        await _send_stage(websocket, "retrieving", "Finding Indian urban precedents.")
        try:
            case_studies = await db.search_case_studies(
                parsed.keywords, city=parsed.city, top_k=5, context=case_context,
            )
            await websocket.send_json({
                "type": "CASE_STUDIES",
                "studies": [case.model_dump() for case in case_studies],
            })
        except Exception as e:
            logger.warning("Case study retrieval failed: %s", e)
            await websocket.send_json({"type": "CASE_STUDIES", "studies": []})

        # ── Group scoring stage ──────────────────────────────────────
        await _send_stage(websocket, "synthesizing", "Computing social group impacts.")
        groups = []
        try:
            metrics_data = final_frame["metrics"]
            if isinstance(metrics_data, dict):
                metrics_obj = AggregateMetrics(**metrics_data)
            else:
                metrics_obj = metrics_data
            groups = score_groups(parsed.sector_deltas, metrics_obj)
            satisfaction = compute_satisfaction(groups)
            await websocket.send_json({
                "type": "GROUP_SCORES",
                "groups": [g.to_dict() for g in groups],
                "citizen_satisfaction": satisfaction,
            })
        except Exception as e:
            logger.warning("Group scoring failed: %s", e)
            await websocket.send_json({
                "type": "GROUP_SCORES",
                "groups": [],
                "citizen_satisfaction": 50,
            })

        # ── Evidence stage ───────────────────────────────────────────
        try:
            evidence = synthesize_evidence(
                params, prediction, final_frame, case_studies,
                original_query=scenario_text,
                group_impacts=groups,
                case_retrieval=db.last_case_retrieval.model_dump(),
                evidence_pack=params.evidence_pack,
                grid_state=grid_state_ref[0] if grid_state_ref else None,
            )
            await websocket.send_json({"type": "EVIDENCE", "evidence": evidence})
        except Exception as e:
            logger.warning("Evidence synthesis failed: %s", e)
            await websocket.send_json({
                "type": "EVIDENCE",
                "evidence": {
                    "markdown": "Evidence synthesis encountered an error. The simulation results above are still valid.",
                    "verdict": "Error",
                    "metrics": final_frame.get("metrics", {}),
                    "proof": final_frame.get("proof", {}),
                    "assumptions": params.assumptions,
                },
            })

        # ── Done ─────────────────────────────────────────────────────
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
    deadline = asyncio.get_event_loop().time() + 30.0
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        message = await asyncio.wait_for(websocket.receive_text(), timeout=remaining)
        try:
            payload = json.loads(message)
        except json.JSONDecodeError as e:
            raise ScenarioParseError(f"First message must be valid JSON. {e}") from e
        # Skip heartbeat pings
        if payload.get("type") == "PING":
            await websocket.send_json({"type": "PONG"})
            continue
        try:
            return StartScenarioMessage(**payload)
        except ValidationError as e:
            raise ScenarioParseError(
                f"First message must be {{ type: 'START', scenario: '...' }}. Got: {payload.get('type', 'unknown')}"
            ) from e


async def _receive_input_response(websocket: WebSocket) -> InputResponseMessage:
    message = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
    try:
        payload = json.loads(message)
        return InputResponseMessage(**payload)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ScenarioParseError(f"Invalid input response: {e}") from e


async def _send_stage(websocket: WebSocket, stage: str, message: str) -> None:
    await websocket.send_json({"type": "STAGE", "stage": stage, "message": message})
