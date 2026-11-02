from __future__ import annotations

import json
import logging
from typing import Any, Callable, Coroutine

from engine.models import Prediction, SectorPrediction, SECTOR_LABELS, SECTOR_NAMES, SimulationParams

logger = logging.getLogger(__name__)


def _build_enriched_prompt(params: SimulationParams) -> str:
    """Build a context-rich prompt with city data, zones, baselines, and case studies."""
    cfg = params.city_config

    # --- Section A: City context ---
    weights = cfg.sector_weights if hasattr(cfg, "sector_weights") and cfg.sector_weights else {}
    weight_str = ", ".join(
        f"{SECTOR_LABELS.get(s, s)}={w * 100:.0f}%" for s, w in sorted(weights.items(), key=lambda x: -x[1]) if w > 0
    )
    city_type = getattr(cfg, "city_type", "generic").replace("_", " ")
    baselines = cfg.baselines if hasattr(cfg, "baselines") and cfg.baselines else {}
    pop = getattr(cfg, "population", 0)
    gdp = baselines.get("gdp_estimate_crores", 0)
    unemployment = baselines.get("unemployment_rate", 0)

    city_context = (
        f"City: {cfg.name} ({city_type}), {getattr(cfg, 'state', '')}\n"
        f"Population: {pop:,} | GDP: {gdp:,.0f} crores | Unemployment: {unemployment:.1%}\n"
        f"Sector weights: {weight_str}"
    )

    # --- Section B: Special zones ---
    zones = cfg.special_zones if hasattr(cfg, "special_zones") and cfg.special_zones else []
    zone_lines = []
    for z in zones[:4]:
        zname = z.get("name", "zone")
        zsectors = ", ".join(SECTOR_LABELS.get(s, s) for s in z.get("sectors", []))
        zboost = z.get("boost", 0)
        zone_lines.append(f"  - {zname} ({zsectors}, boost +{zboost:.0%})")
    zone_section = ""
    if zone_lines:
        zone_section = f"\nSpecial zones:\n" + "\n".join(zone_lines)

    # --- Section C: Real-time signal quality ---
    snap = params.realtime_snapshot
    signal_section = ""
    if snap and hasattr(snap, "quality_score"):
        mode = "real-time" if getattr(snap, "is_realtime", False) else "demo/baseline"
        signal_section = f"\nData mode: {mode} | Signal quality: {snap.quality_score:.2f}"

    # --- Section D: Sector changes ---
    changes = []
    for sector, delta in params.sector_deltas.items():
        if abs(delta) > 0:
            changes.append(f"  - {SECTOR_LABELS[sector]}: {delta:+.0f}%")
    if not changes:
        changes = ["  - No explicit sector changes; policy effects only"]

    # --- Section E: Policies ---
    policies = ", ".join(params.policies_active) if params.policies_active else "none"

    # --- Section F: Case study examples from evidence pack ---
    evidence_section = ""
    ep = params.evidence_pack
    if ep and isinstance(ep, dict):
        items = ep.get("items", [])
        if items:
            top_items = sorted(items, key=lambda x: x.get("relevance", 0), reverse=True)[:3]
            examples = []
            for item in top_items:
                title = item.get("title", "Unknown")
                summary = item.get("summary", item.get("citation", ""))
                if summary:
                    examples.append(f"  - \"{title}\": {summary}")
            if examples:
                evidence_section = f"\nRelevant historical precedents:\n" + "\n".join(examples)

    # --- Assemble ---
    prompt = f"""You are an urban economics analyst specializing in Indian cities.
Given this scenario for {cfg.name} over {params.horizon_months} months:

{city_context}{zone_section}{signal_section}

Sector changes:
{chr(10).join(changes)}

Active policies: {policies}{evidence_section}

Predict the impact on employment per sector, real estate, transit, most affected areas, and counter-intuitive effects.
Consider the city's sector composition and special zones when making predictions.

Respond ONLY with valid JSON matching this exact schema:
{{
  "employment_impact": {{
    "<sector_name>": {{
      "direction": "up"|"down"|"stable",
      "magnitude": "low"|"moderate"|"high",
      "confidence": "low"|"medium"|"high",
      "rationale": "<one sentence>"
    }}
  }},
  "real_estate_impact": {{
    "direction": "<up|down|stable|mixed>",
    "confidence": "<low|medium|high>",
    "rationale": "<one sentence>"
  }},
  "transit_impact": {{
    "direction": "<higher load|lower demand|stable>",
    "confidence": "<low|medium|high>",
    "rationale": "<one sentence>"
  }},
  "most_affected_areas": ["<area 1>", "<area 2>", "<area 3>"],
  "counter_intuitive": ["<insight 1>", "<insight 2>"],
  "overall_confidence": "<low|medium|high>",
  "reasoning": "<2-3 sentence summary>"
}}

Sector names must be exactly: {', '.join(SECTOR_NAMES)}"""
    return prompt


def _parse_llm_response(text: str, params: SimulationParams) -> Prediction:
    """Parse LLM JSON response into Prediction model. Raises on failure."""
    # Extract JSON from possible markdown code fences
    cleaned = text.strip()
    if "```" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]

    data = json.loads(cleaned)

    impacts: dict[str, SectorPrediction] = {}
    raw_impact = data.get("employment_impact", {})
    for sector in SECTOR_NAMES:
        entry = raw_impact.get(sector, {})
        impacts[sector] = SectorPrediction(
            direction=entry.get("direction", "stable"),
            magnitude=entry.get("magnitude", "low"),
            confidence=entry.get("confidence", "medium"),
            rationale=entry.get("rationale", f"{SECTOR_LABELS[sector]} impact from scenario."),
        )

    return Prediction(
        employment_impact=impacts,
        real_estate_impact=data.get("real_estate_impact", {
            "direction": "mixed",
            "confidence": "medium",
            "rationale": "Capital changes propagate into land values.",
        }),
        transit_impact=data.get("transit_impact", {
            "direction": "stable",
            "confidence": "medium",
            "rationale": "Employment shifts change commuter pressure.",
        }),
        most_affected_areas=data.get("most_affected_areas", ["central cells", "peripheral growth zones"]),
        counter_intuitive=data.get("counter_intuitive", ["Policy effects may lag sector shocks by months."]),
        overall_confidence=data.get("overall_confidence", "medium"),
        reasoning=data.get("reasoning", f"LLM prediction for {params.city_config.name}."),
    )


_CITY_TYPE_CONTEXT: dict[str, str] = {
    "tech_hub": "tech employment spillovers and housing demand near IT corridors",
    "financial_hub": "financial services concentration and CBD real estate pressure",
    "port_city": "logistics throughput and export-oriented manufacturing",
    "industrial": "factory employment and supply-chain linkages",
    "heritage_tourism": "seasonal tourism revenue and informal service jobs",
    "government": "public-sector employment and administrative spending",
    "generic": "mixed economic activity and balanced sector contributions",
}


def _enhanced_deterministic_prediction(params: SimulationParams) -> Prediction:
    """City-aware rule-based prediction using city_config data."""
    cfg = params.city_config
    weights = cfg.sector_weights if hasattr(cfg, "sector_weights") and cfg.sector_weights else {}
    zones = cfg.special_zones if hasattr(cfg, "special_zones") and cfg.special_zones else []
    city_type = getattr(cfg, "city_type", "generic")
    baselines = cfg.baselines if hasattr(cfg, "baselines") and cfg.baselines else {}

    # --- Employment impact per sector ---
    impacts: dict[str, SectorPrediction] = {}
    for sector in SECTOR_NAMES:
        delta = float(params.sector_deltas.get(sector, 0.0))
        weight = weights.get(sector, 0.1)

        direction = "stable"
        if delta > 5:
            direction = "up"
        elif delta < -5:
            direction = "down"

        magnitude = "low"
        if abs(delta) >= 50:
            magnitude = "high"
        elif abs(delta) >= 20:
            magnitude = "moderate"

        # Confidence scales with how important this sector is to the city
        if weight >= 0.25:
            confidence = "high"
        elif weight <= 0.08:
            confidence = "low"
        else:
            confidence = "medium"

        weight_pct = f"{weight * 100:.0f}%"
        rationale = (
            f"{cfg.name}'s {SECTOR_LABELS[sector]} sector ({weight_pct} of city economy) "
            f"receives a {delta:+.0f}% shock."
        )
        if weight >= 0.2:
            rationale += f" This is a dominant sector — effects will cascade to housing and transport."

        impacts[sector] = SectorPrediction(
            direction=direction,
            magnitude=magnitude,
            confidence=confidence,
            rationale=rationale,
        )

    # --- Most affected areas from real zone data ---
    zone_names = [z.get("name", "Unnamed zone") for z in zones[:3]] if zones else []
    if not zone_names:
        zone_names = [
            f"{cfg.name} CBD and high-density corridors",
            f"outer wards with higher informal employment",
            f"areas near major transport junctions",
        ]

    # --- Contextual reasoning ---
    active = [SECTOR_LABELS[s] for s, v in params.sector_deltas.items() if abs(v) > 0]
    policy_text = ", ".join(params.policies_active) if params.policies_active else "no explicit policy offset"
    type_context = _CITY_TYPE_CONTEXT.get(city_type, _CITY_TYPE_CONTEXT["generic"])

    top_sector = max(params.sector_deltas.items(), key=lambda x: abs(x[1])) if params.sector_deltas else None
    top_label = SECTOR_LABELS[top_sector[0]] if top_sector else "the economy"
    top_delta = top_sector[1] if top_sector else 0

    reasoning = (
        f"{cfg.name} is a {city_type.replace('_', ' ')} — {type_context}. "
        f"The largest shock is {top_label} at {top_delta:+.0f}%. "
        f"Policy context: {policy_text}."
    )

    # --- Real estate ---
    re_direction = "mixed"
    re_rationale = "Sector shifts create mixed pressure on land values."
    positive_sectors = [s for s, v in params.sector_deltas.items() if v > 10]
    if positive_sectors:
        dominant = positive_sectors[0]
        re_direction = "up"
        re_rationale = (
            f"{SECTOR_LABELS[dominant]} growth drives demand for commercial and residential space, "
            f"especially near {zone_names[0] if zone_names else 'activity centers'}."
        )
    elif all(v < -5 for v in params.sector_deltas.values()):
        re_direction = "down"
        re_rationale = "Broad sector contraction reduces demand for commercial and residential space."

    # --- Transit ---
    transit_dir = "stable"
    transit_rationale = "No major shift in commuter pressure expected."
    if any(v > 15 for v in params.sector_deltas.values()):
        transit_dir = "higher load"
        transit_rationale = f"Job growth increases commuter pressure on corridors serving {zone_names[0] if zone_names else 'activity centers'}."
    elif any(v < -15 for v in params.sector_deltas.values()):
        transit_dir = "lower demand"
        transit_rationale = "Sector contraction reduces commuter volume."

    # --- Confidence ---
    overall = "medium"
    if baselines.get("unemployment_rate", 0.05) < 0.04 and any(abs(v) > 30 for v in params.sector_deltas.values()):
        overall = "high"
    elif baselines.get("unemployment_rate", 0.05) > 0.08:
        overall = "low"

    # --- Counter-intuitive ---
    counter = []
    if any(v > 20 for v in params.sector_deltas.values()):
        counter.append(
            f"Rapid growth in {top_label} can strain housing affordability near {zone_names[0] if zone_names else 'growth zones'}, "
            f"displacing informal workers even as formal jobs increase."
        )
    if "smart_city" in [p.lower().replace(" ", "_") for p in params.policies_active]:
        counter.append("Smart City infrastructure investments can reduce congestion even while employment rises.")
    if not counter:
        counter.append("Policy effects often lag sector shocks by 6-12 months.")

    # Fix #8: generate a headline for the prediction
    top_sector = max(params.sector_deltas.items(), key=lambda x: abs(x[1])) if params.sector_deltas else None
    if top_sector:
        top_label = SECTOR_LABELS[top_sector[0]]
        top_delta = top_sector[1]
        if top_delta < -10:
            pred_headline = f"{cfg.name} faces a {abs(top_delta):.0f}% hit to {top_label.lower()} \u2014 expect ripple effects across the city."
        elif top_delta > 10:
            pred_headline = f"{cfg.name} sees a {top_delta:.0f}% boost in {top_label.lower()} \u2014 growth expected across the city."
        else:
            pred_headline = f"{cfg.name} sees modest shifts across sectors."
    else:
        pred_headline = f"{cfg.name}: policy effects under analysis."

    return Prediction(
        headline=pred_headline,
        employment_impact=impacts,
        real_estate_impact={
            "direction": re_direction,
            "confidence": "medium",
            "rationale": re_rationale,
        },
        transit_impact={
            "direction": transit_dir,
            "confidence": "medium",
            "rationale": transit_rationale,
        },
        most_affected_areas=zone_names,
        counter_intuitive=counter,
        overall_confidence=overall,
        reasoning=reasoning,
    )


async def generate_prediction(
    params: SimulationParams,
    mode: str = "deep",
    llm_fn: Callable[[str], Coroutine[Any, Any, str]] | None = None,
) -> Prediction:
    """Generate prediction.

    Quick mode = enhanced deterministic (no LLM).
    Deep mode = LLM with enriched context.
    The ``llm_fn`` callback receives a prompt string and returns the LLM response text.
    When ``llm_fn`` is ``None``, always falls back to deterministic.
    """
    if mode == "quick" or llm_fn is None:
        logger.info(
            "%s mode: using enhanced deterministic prediction for %s",
            "Quick" if mode == "quick" else "No LLM callback",
            params.city_config.name,
        )
        return _enhanced_deterministic_prediction(params)

    prompt = _build_enriched_prompt(params)

    try:
        text = await llm_fn(prompt)
        prediction = _parse_llm_response(text, params)
        logger.info("LLM prediction generated for %s", params.city_config.name)
        return prediction
    except Exception as e:
        error_detail = str(e).strip() or f"{type(e).__name__} (no message)"
        logger.warning("LLM prediction failed, falling back to enhanced deterministic: %s", error_detail)
        return _enhanced_deterministic_prediction(params)
