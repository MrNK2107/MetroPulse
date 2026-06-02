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
    city = params.city_config.name
    gdp_pct = metrics.get("gdpDelta", 0.0) * 100
    unemp_pct = metrics.get("unemploymentRate", 0.0) * 100
    re_index = metrics.get("realEstateIndex", 1.0)
    congestion = metrics.get("transitCongestion", 0.0)
    
    # Identify shocks
    shocks = []
    for sector, delta in params.sector_deltas.items():
        if abs(delta) > 0:
            label = SECTOR_LABELS.get(sector, sector)
            dir_str = "contraction" if delta < 0 else "expansion"
            shocks.append(f"a {abs(delta):.0f}% {dir_str} in the {label} sector")
    
    shock_desc = " and ".join(shocks) if shocks else "general parameter adjustments"
    
    # 1. Economic impact
    if gdp_pct < -0.5:
        econ = f"The initial shock of {shock_desc} triggers a contraction in {city}'s economy, driving GDP down by {abs(gdp_pct):.2f}%."
    elif gdp_pct > 0.5:
        econ = f"The stimulus of {shock_desc} boosts {city}'s economy, causing GDP to rise by {gdp_pct:.2f}%."
    else:
        econ = f"The scenario results in a relatively stable economic output for {city}, with GDP changing by {gdp_pct:+.2f}%."
        
    # 2. Employment
    baseline_unemp = params.city_config.baselines.get("unemployment_rate", 0.04) * 100
    if unemp_pct > baseline_unemp + 0.1:
        jobs = f"This contraction leads directly to job losses, pushing the city's unemployment rate up from {baseline_unemp:.1f}% to {unemp_pct:.1f}%."
    elif unemp_pct < baseline_unemp - 0.1:
        jobs = f"This expansion stimulates job creation, bringing the city's unemployment rate down from {baseline_unemp:.1f}% to {unemp_pct:.1f}%."
    else:
        jobs = f"Employment levels remain steady, with unemployment hovering near the baseline of {baseline_unemp:.1f}%."
        
    # 3. Real Estate
    re_change = (re_index - 1.0) * 100
    if re_change < -0.5:
        housing = f"Reduced economic confidence and job losses soften the housing market, leading to a {abs(re_change):.1f}% drop in property and rental values across the city."
    elif re_change > 0.5:
        housing = f"Increased wages and tech worker migration fuel housing demand, driving property and rental values up by {re_change:.1f}%."
    else:
        housing = "Real estate prices and rental rates remain stable, showing no major fluctuations."
        
    # 4. Transit
    if congestion > 0.55:
        transit = f"Increased economic activity intensifies commuting patterns, causing average transit congestion to rise to {congestion*100:.1f}%."
    elif congestion < 0.35:
        transit = f"Slowed business operations and reduced labor commuting ease traffic, lowering average transit congestion to {congestion*100:.1f}%."
    else:
        transit = f"Traffic patterns remain normal, with average city congestion at {congestion*100:.1f}%."
        
    # 5. Policy context
    if params.policies_active:
        policies = f"Active interventions like {', '.join(params.policies_active)} help shape these outcomes by modifying local demand and dampening negative shocks."
    else:
        policies = "The absence of active policy interventions means the shock propagates directly through baseline market mechanisms."
        
    return f"{econ} {jobs} {housing} {transit} {policies}"
