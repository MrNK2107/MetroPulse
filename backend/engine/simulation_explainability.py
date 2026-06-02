"""Simulation explainability — driver breakdown for aggregate metrics.

Produces human-readable explanations of what drove each metric change,
with percentage contribution from each factor.
"""

from __future__ import annotations

from typing import Any

from engine.models import SimulationParams, SECTOR_LABELS


def explain_metric_deltas(
    params: SimulationParams,
    metrics: dict[str, float],
    proof: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Produce driver breakdown for each aggregate metric.

    Returns dict like:
        {
            "gdp_delta": {
                "value": -0.042,
                "confidence": 0.63,
                "drivers": [
                    {"factor": "transport disruption", "contribution_pct": 48},
                    {"factor": "employment decline", "contribution_pct": 31},
                ]
            },
            ...
        }
    """
    gdp_delta = metrics.get("gdpDelta", 0.0)
    overall_confidence = proof.get("overallConfidence", 0.35)
    active_effects = proof.get("activeEffects", [])

    results = {}

    # GDP drivers
    results["gdp_delta"] = {
        "value": gdp_delta,
        "confidence": overall_confidence,
        "drivers": _decompose_gdp_drivers(params, gdp_delta, active_effects),
    }

    # Unemployment drivers
    unemp = metrics.get("unemploymentRate", 0.0)
    results["unemployment_rate"] = {
        "value": unemp,
        "confidence": overall_confidence,
        "drivers": _decompose_unemployment_drivers(params, unemp, active_effects),
    }

    # Real estate drivers
    re_index = metrics.get("realEstateIndex", 1.0)
    results["real_estate_index"] = {
        "value": re_index,
        "confidence": overall_confidence,
        "drivers": _decompose_realestate_drivers(params, re_index),
    }

    # Congestion drivers
    congestion = metrics.get("transitCongestion", 0.0)
    results["transit_congestion"] = {
        "value": congestion,
        "confidence": overall_confidence,
        "drivers": _decompose_congestion_drivers(params, congestion),
    }

    # Add summary and limitations
    results["_meta"] = {
        "summary": _generate_summary(params, metrics, overall_confidence),
        "limitations": [
            "This is a model estimate, not a prediction.",
            "City-level employment values are estimated from census data.",
            "Real-time news affects confidence and modifiers, not direct measurement.",
            "Simulation coefficients are tuned, not from published econometric research.",
        ],
        "confidence_label": "High" if overall_confidence >= 0.7 else "Medium" if overall_confidence >= 0.4 else "Low",
    }

    return results


def _decompose_gdp_drivers(
    params: SimulationParams, gdp_delta: float, active_effects: list[str]
) -> list[dict[str, Any]]:
    """Attribute GDP change to sector shocks, policies, and cascade effects."""
    drivers = []

    # Sector contributions (proportional to |delta * weight|)
    total_abs = sum(
        abs(v) * params.city_config.sector_weights.get(s, 0.1)
        for s, v in params.sector_deltas.items()
    ) or 1.0

    for sector, delta in sorted(
        params.sector_deltas.items(), key=lambda x: abs(x[1]), reverse=True
    ):
        if abs(delta) < 0.5:
            continue
        weight = params.city_config.sector_weights.get(sector, 0.1)
        contribution = abs(delta * weight) / total_abs * 100
        label = SECTOR_LABELS.get(sector, sector)
        direction = "boost" if delta > 0 else "disruption"
        drivers.append({
            "factor": f"{label} {direction}",
            "contribution_pct": min(round(contribution), 100),
        })

    # Policy effects
    if params.policies_active:
        drivers.append({
            "factor": f"Policy effects ({', '.join(params.policies_active[:2])})",
            "contribution_pct": min(len(params.policies_active) * 8, 25),
        })

    # Active effects from simulation
    for effect in active_effects[:2]:
        if "monsoon" in effect.lower() or "flood" in effect.lower():
            drivers.append({"factor": "Monsoon/flood effects", "contribution_pct": 15})
        elif "cascade" in effect.lower() or "spillover" in effect.lower():
            drivers.append({"factor": "Spatial spillover", "contribution_pct": 12})

    if not drivers:
        drivers.append({"factor": "Baseline effects", "contribution_pct": 100})

    # Normalize to 100%
    total = sum(d["contribution_pct"] for d in drivers) or 1
    for d in drivers:
        d["contribution_pct"] = round(d["contribution_pct"] / total * 100)

    return drivers[:5]


def _decompose_unemployment_drivers(
    params: SimulationParams, unemp: float, active_effects: list[str]
) -> list[dict[str, Any]]:
    baseline = params.city_config.baselines.get("unemployment_rate", 0.04)
    drivers = []

    if unemp > baseline + 0.005:
        drivers.append({"factor": "Job losses from sector shocks", "contribution_pct": 55})
        drivers.append({"factor": "Informal economy contraction", "contribution_pct": 25})
        if any("monsoon" in e.lower() for e in active_effects):
            drivers.append({"factor": "Seasonal disruption", "contribution_pct": 20})
    elif unemp < baseline - 0.005:
        has_positive_shocks = any(v > 0.0 for v in params.sector_deltas.values())
        if has_positive_shocks:
            drivers.append({"factor": "Job creation from growth sectors", "contribution_pct": 60})
            drivers.append({"factor": "Policy-driven employment", "contribution_pct": 25})
            drivers.append({"factor": "Informal economy expansion", "contribution_pct": 15})
        else:
            drivers.append({"factor": "Baseline informal sector growth", "contribution_pct": 60})
            drivers.append({"factor": "Baseline migration patterns", "contribution_pct": 25})
            drivers.append({"factor": "Informal economy expansion", "contribution_pct": 15})
    else:
        drivers.append({"factor": "Minimal change from baseline", "contribution_pct": 100})

    return drivers[:4]


def _decompose_realestate_drivers(
    params: SimulationParams, re_index: float
) -> list[dict[str, Any]]:
    re_delta = re_index - 1.0
    if abs(re_delta) < 0.01:
        return [{"factor": "Stable — near baseline", "contribution_pct": 100}]

    # Compute raw signal weights from actual scenario data
    # Activity spillover: proportional to weighted sector shocks (capital flow)
    activity_raw = sum(
        abs(d) * params.city_config.sector_weights.get(s, 0.1)
        for s, d in params.sector_deltas.items()
        if abs(d) > 0
    ) or 0.1

    # Employment demand: proportional to employment-heavy sector deltas
    employment_sectors = {"it_ites", "manufacturing", "trade_hospitality", "informal"}
    employment_raw = sum(
        abs(d) for s, d in params.sector_deltas.items()
        if s in employment_sectors and abs(d) > 0
    ) or 0.05

    # Policy effects
    policy_raw = 0.0
    has_rera = "RERA" in str(params.policies_active)
    has_pmay = "PM Awas Yojana" in str(params.policies_active)
    if has_rera:
        policy_raw += 0.15
    if has_pmay:
        policy_raw += 0.10

    total_raw = activity_raw + employment_raw + policy_raw
    if total_raw <= 0:
        total_raw = 1.0

    drivers = [
        {"factor": "Economic activity spillover", "contribution_pct": round(activity_raw / total_raw * 100)},
        {"factor": "Employment-driven demand", "contribution_pct": round(employment_raw / total_raw * 100)},
    ]
    if has_rera:
        drivers.append({"factor": "RERA volatility dampening", "contribution_pct": round(0.15 / total_raw * 100)})
    if has_pmay:
        drivers.append({"factor": "PMAY housing program", "contribution_pct": round(0.10 / total_raw * 100)})

    # Baseline gets the remainder to ensure we sum to 100 %
    used = sum(d["contribution_pct"] for d in drivers)
    if used < 100:
        drivers.append({"factor": "Other market forces", "contribution_pct": 100 - used})

    return drivers[:4]


def _decompose_congestion_drivers(
    params: SimulationParams, congestion: float
) -> list[dict[str, Any]]:
    if congestion > 0.7:
        drivers = [
            {"factor": "High employment density", "contribution_pct": 50},
            {"factor": "Economic activity concentration", "contribution_pct": 30},
        ]
        if params.city_config.metro_system:
            drivers.append({"factor": "Metro capacity limits", "contribution_pct": 20})
        return drivers[:4]
    elif congestion > 0.4:
        return [
            {"factor": "Moderate urban density", "contribution_pct": 60},
            {"factor": "Employment distribution", "contribution_pct": 40},
        ]
    else:
        return [{"factor": "Low density / distributed activity", "contribution_pct": 100}]


def _generate_summary(
    params: SimulationParams, metrics: dict[str, float], confidence: float = 0.0
) -> str:
    """Generate a cohesive narrative summary of the simulation outcome."""
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


def format_explanation_narrative(explanations: dict[str, dict[str, Any]]) -> str:
    """Format explanations as user-facing narrative text."""
    lines = []

    for metric_key, data in explanations.items():
        if metric_key.startswith("_"):
            continue  # skip _meta
        value = data["value"]
        confidence = data["confidence"]
        drivers = data["drivers"]

        conf_label = (
            "High" if confidence >= 0.8
            else "Medium" if confidence >= 0.6
            else "Low"
        )

        if metric_key == "gdp_delta":
            lines.append(f"**Estimated GDP change: {value * 100:+.1f}%**")
        elif metric_key == "unemployment_rate":
            lines.append(f"**Unemployment: {value * 100:.1f}%**")
        else:
            metric_name = metric_key.replace("_", " ").title()
            lines.append(f"**{metric_name}: {value:.2f}**")

        lines.append(f"Confidence: {conf_label} ({confidence * 100:.0f}%)")
        lines.append("")
        lines.append("Main drivers:")
        for d in drivers[:3]:
            lines.append(f"- {d['factor']} ({d['contribution_pct']}%)")
        lines.append("")

    # Add summary if available
    meta = explanations.get("_meta", {})
    if meta.get("summary"):
        lines.insert(0, meta["summary"])
        lines.insert(1, "")

    # Add limitations
    limitations = meta.get("limitations", [
        "This result is model-generated and should be interpreted as directional guidance rather than prediction.",
    ])
    lines.append("*Limitations:*")
    for lim in limitations:
        lines.append(f"- {lim}")

    return "\n".join(lines)
