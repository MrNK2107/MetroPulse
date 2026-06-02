from __future__ import annotations

from typing import Any

from app.core.provenance import confidence_label
from engine.models import SECTOR_LABELS, SimulationParams
from engine.simulation_explainability import _generate_summary


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
    
    # Dynamically compute driver scores based on inputs
    shock_val = sum(abs(v) for v in params.sector_deltas.values())
    shock_score = min(40.0, shock_val * 1.5)
    rt_score = 25.0 if proof.get("dataMode") == "real_time" else 0.0
    ev_score = min(25.0, evidence_conf * 30.0)
    base_score = 15.0
    
    total = max(1.0, shock_score + rt_score + ev_score + base_score)
    shock_pct = round(shock_score / total * 100)
    rt_pct = round(rt_score / total * 100)
    ev_pct = round(ev_score / total * 100)
    base_pct = 100 - (shock_pct + rt_pct + ev_pct)
    
    top_drivers = []
    if sectors:
        top_drivers.append({
            "factor": f"Direct shock to target sectors ({', '.join(sectors[:2])})",
            "contribution": shock_pct,
            "origin": "scenario_input",
        })
    if proof.get("dataMode") == "real_time":
        top_drivers.append({
            "factor": "Real-time news & context modifiers",
            "contribution": rt_pct,
            "origin": "real_time_context",
        })
    if evidence_conf > 0:
        top_drivers.append({
            "factor": "Historical precedent evidence weighting",
            "contribution": ev_pct,
            "origin": "rag_evidence",
        })
    top_drivers.append({
        "factor": "City baseline economic structure",
        "contribution": base_pct,
        "origin": "estimated",
    })

    # Sort drivers by contribution percentage
    top_drivers.sort(key=lambda d: d["contribution"], reverse=True)

    return {
        "summary": _generate_summary(params, metrics),
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



