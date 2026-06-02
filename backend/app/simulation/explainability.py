from __future__ import annotations

from typing import Any

from app.core.provenance import confidence_label
from engine.models import SECTOR_LABELS, SimulationParams


def _compute_driver_contributions(
    params: SimulationParams,
    proof: dict[str, Any],
    evidence_conf: float,
) -> list[dict[str, Any]]:
    """Compute data-driven contribution percentages for each driver.

    Contributions are proportional to the strength of each signal source,
    then normalised so they sum to 100 %.
    """
    # 1. Scenario input: proportional to |delta * sector_weight|
    scenario_raw = sum(
        abs(d) * params.city_config.sector_weights.get(s, 0.1)
        for s, d in params.sector_deltas.items()
        if abs(d) > 0
    )

    # 2. Real-time overlay: proportional to overlay signal strength
    overlay_summary = proof.get("overlaySummary") or {}
    overlay_conf = float(overlay_summary.get("confidence", 0) or 0)
    realtime_raw = overlay_conf if proof.get("dataMode") == "real_time" else 0.0

    # 3. RAG evidence: proportional to evidence confidence
    rag_raw = float(evidence_conf) if evidence_conf > 0 else 0.0

    # 4. Baseline: always present as the foundation
    baseline_raw = 1.0

    total = scenario_raw + realtime_raw + rag_raw + baseline_raw
    if total <= 0:
        total = 1.0

    drivers: list[dict[str, Any]] = []

    if scenario_raw > 0:
        sectors = [
            SECTOR_LABELS.get(sector, sector)
            for sector, delta in params.sector_deltas.items()
            if abs(delta) > 0
        ]
        drivers.append({
            "factor": f"Scenario sector shock: {', '.join(sectors[:2])}",
            "contribution": round(scenario_raw / total * 100),
            "origin": "scenario_input",
        })

    if realtime_raw > 0:
        drivers.append({
            "factor": "real-time contextual signal overlay",
            "contribution": round(realtime_raw / total * 100),
            "origin": "real_time_context",
        })

    if rag_raw > 0:
        drivers.append({
            "factor": "retrieved evidence coefficient adjustment",
            "contribution": round(rag_raw / total * 100),
            "origin": "rag_evidence",
        })

    # Baseline gets the remainder to ensure exact 100 %
    used = sum(d["contribution"] for d in drivers)
    baseline_pct = max(100 - used, 0)
    drivers.append({
        "factor": "estimated city baseline sector weights",
        "contribution": baseline_pct,
        "origin": "estimated",
    })

    return drivers


def build_explanation(
    params: SimulationParams,
    metrics: dict[str, float],
    proof: dict[str, Any],
    evidence_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    confidence = float(proof.get("overallConfidence", 0.35))
    active = proof.get("activeEffects", [])
    evidence_conf = float((evidence_pack or {}).get("overall_evidence_confidence", 0.0) or 0.0)

    top_drivers = _compute_driver_contributions(params, proof, evidence_conf)

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
