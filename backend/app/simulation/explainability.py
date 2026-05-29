from __future__ import annotations

from typing import Any

from app.core.provenance import confidence_label
from engine.models import SECTOR_LABELS, SimulationParams


def build_explanation(
    params: SimulationParams,
    metrics: dict[str, float],
    proof: dict[str, Any],
    evidence_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    confidence = float(proof.get("overallConfidence", 0.35))
    active = proof.get("activeEffects", [])
    evidence_conf = float((evidence_pack or {}).get("overall_evidence_confidence", 0.0) or 0.0)
    sectors = [
        SECTOR_LABELS.get(sector, sector)
        for sector, delta in params.sector_deltas.items()
        if abs(delta) > 0
    ]
    top_drivers = []
    if sectors:
        top_drivers.append({
            "factor": f"Scenario sector shock: {', '.join(sectors[:2])}",
            "contribution": 42,
            "origin": "scenario_input",
        })
    if proof.get("dataMode") == "real_time":
        top_drivers.append({
            "factor": "real-time contextual signal overlay",
            "contribution": 23,
            "origin": "real_time_context",
        })
    if evidence_conf > 0:
        top_drivers.append({
            "factor": "retrieved evidence coefficient adjustment",
            "contribution": 20,
            "origin": "rag_evidence",
        })
    top_drivers.append({
        "factor": "estimated city baseline sector weights",
        "contribution": 15,
        "origin": "estimated",
    })

    return {
        "summary": _summary(params, metrics),
        "confidence": confidence,
        "confidence_label": confidence_label(confidence),
        "top_drivers": top_drivers[:4],
        "active_effects": active,
        "limitations": [
            "This is a model estimate, not a prediction.",
            "Real-time news is used as contextual signal, not direct measurement.",
            "Some city baselines and spatial anchors are estimated.",
            "Evidence adjusts bounded coefficients and explanations; it does not create exact forecasts.",
        ],
    }


def _summary(params: SimulationParams, metrics: dict[str, float]) -> str:
    gdp = metrics.get("gdpDelta", 0.0)
    direction = "increase" if gdp >= 0 else "decrease"
    return (
        f"{params.city_config.name} shows a scenario-estimated {direction} "
        f"of {abs(gdp) * 100:.1f}% in modeled economic activity."
    )
