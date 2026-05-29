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
                    {"factor": "transport disruption", "contribution": 48},
                    {"factor": "employment decline", "contribution": 31},
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
            "contribution": min(round(contribution), 100),
        })

    # Policy effects
    if params.policies_active:
        drivers.append({
            "factor": f"Policy effects ({', '.join(params.policies_active[:2])})",
            "contribution": min(len(params.policies_active) * 8, 25),
        })

    # Active effects from simulation
    for effect in active_effects[:2]:
        if "monsoon" in effect.lower() or "flood" in effect.lower():
            drivers.append({"factor": "Monsoon/flood effects", "contribution": 15})
        elif "cascade" in effect.lower() or "spillover" in effect.lower():
            drivers.append({"factor": "Spatial spillover", "contribution": 12})

    if not drivers:
        drivers.append({"factor": "Baseline effects", "contribution": 100})

    # Normalize to 100%
    total = sum(d["contribution"] for d in drivers) or 1
    for d in drivers:
        d["contribution"] = round(d["contribution"] / total * 100)

    return drivers[:5]


def _decompose_unemployment_drivers(
    params: SimulationParams, unemp: float, active_effects: list[str]
) -> list[dict[str, Any]]:
    baseline = params.city_config.baselines.get("unemployment_rate", 0.04)
    drivers = []

    if unemp > baseline + 0.005:
        drivers.append({"factor": "Job losses from sector shocks", "contribution": 55})
        drivers.append({"factor": "Informal economy contraction", "contribution": 25})
        if any("monsoon" in e.lower() for e in active_effects):
            drivers.append({"factor": "Seasonal disruption", "contribution": 20})
    elif unemp < baseline - 0.005:
        drivers.append({"factor": "Job creation from growth sectors", "contribution": 60})
        drivers.append({"factor": "Policy-driven employment", "contribution": 25})
        drivers.append({"factor": "Informal economy expansion", "contribution": 15})
    else:
        drivers.append({"factor": "Minimal change from baseline", "contribution": 100})

    return drivers[:4]


def _decompose_realestate_drivers(
    params: SimulationParams, re_index: float
) -> list[dict[str, Any]]:
    re_delta = re_index - 1.0
    if abs(re_delta) < 0.01:
        return [{"factor": "Stable — near baseline", "contribution": 100}]

    drivers = [
        {"factor": "Economic activity spillover", "contribution": 45},
        {"factor": "Employment-driven demand", "contribution": 30},
    ]
    if "RERA" in str(params.policies_active):
        drivers.append({"factor": "RERA volatility dampening", "contribution": 15})
    if "PM Awas Yojana" in str(params.policies_active):
        drivers.append({"factor": "PMAY housing program", "contribution": 10})

    return drivers[:4]


def _decompose_congestion_drivers(
    params: SimulationParams, congestion: float
) -> list[dict[str, Any]]:
    if congestion > 0.7:
        drivers = [
            {"factor": "High employment density", "contribution": 50},
            {"factor": "Economic activity concentration", "contribution": 30},
        ]
        if params.city_config.metro_system:
            drivers.append({"factor": "Metro capacity limits", "contribution": 20})
        return drivers[:4]
    elif congestion > 0.4:
        return [
            {"factor": "Moderate urban density", "contribution": 60},
            {"factor": "Employment distribution", "contribution": 40},
        ]
    else:
        return [{"factor": "Low density / distributed activity", "contribution": 100}]


def _generate_summary(
    params: SimulationParams, metrics: dict[str, float], confidence: float
) -> str:
    """Generate a one-line summary of the simulation outcome."""
    gdp = metrics.get("gdpDelta", 0.0)
    city = params.city_config.name
    changed = [SECTOR_LABELS.get(s, s) for s, v in params.sector_deltas.items() if abs(v) > 1]
    sectors = ", ".join(changed[:2]) if changed else "economic activity"

    if abs(gdp) < 0.005:
        return f"Minimal economic change projected for {city}."
    direction = "growth" if gdp > 0 else "contraction"
    return f"{city} shows estimated {direction} of {abs(gdp)*100:.1f}% driven by {sectors}."


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
            lines.append(f"- {d['factor']} ({d['contribution']}%)")
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
