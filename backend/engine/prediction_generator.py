from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from engine.models import Prediction, SectorPrediction, SECTOR_LABELS, SECTOR_NAMES, SimulationParams

logger = logging.getLogger(__name__)

_PREDICTION_PROMPT = """You are an urban economics analyst specializing in Indian cities.
Given this scenario for {city_name} over {horizon_months} months:

Sector changes:
{sector_changes}

Active policies: {policies}

Predict the impact on employment per sector, real estate, transit, most affected areas, and counter-intuitive effects.

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

Sector names must be exactly: {sector_list}"""


def _build_prompt(params: SimulationParams) -> str:
    changes = []
    for sector, delta in params.sector_deltas.items():
        if abs(delta) > 0:
            changes.append(f"  - {SECTOR_LABELS[sector]}: {delta:+.0f}%")
    if not changes:
        changes = ["  - No explicit sector changes; policy effects only"]

    return _PREDICTION_PROMPT.format(
        city_name=params.city_config.name,
        horizon_months=params.horizon_months,
        sector_changes="\n".join(changes),
        policies=", ".join(params.policies_active) if params.policies_active else "none",
        sector_list=", ".join(SECTOR_NAMES),
    )


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


async def _call_gemini(prompt: str, timeout_ms: int) -> str:
    from google import genai
    from app.config import settings

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await asyncio.wait_for(
        asyncio.to_thread(
            client.models.generate_content,
            model=settings.resolved_llm_model or "gemini-2.0-flash",
            contents=prompt,
        ),
        timeout=timeout_ms / 1000.0,
    )
    return response.text


async def _call_openai(prompt: str, timeout_ms: int) -> str:
    from openai import AsyncOpenAI
    from app.config import settings

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=settings.resolved_llm_model or "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        ),
        timeout=timeout_ms / 1000.0,
    )
    return response.choices[0].message.content


def _deterministic_prediction(params: SimulationParams) -> Prediction:
    """Existing rule-based fallback."""
    impacts: dict[str, SectorPrediction] = {}
    for sector in SECTOR_NAMES:
        delta = float(params.sector_deltas.get(sector, 0.0))
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
        impacts[sector] = SectorPrediction(
            direction=direction,
            magnitude=magnitude,
            confidence="medium",
            rationale=f"{SECTOR_LABELS[sector]} receives a {delta:+.0f}% scenario shock.",
        )

    active = [SECTOR_LABELS[s] for s, v in params.sector_deltas.items() if abs(v) > 0]
    policy_text = ", ".join(params.policies_active) if params.policies_active else "no explicit policy offset"
    return Prediction(
        employment_impact=impacts,
        real_estate_impact={
            "direction": "up" if any(v > 0 for v in params.sector_deltas.values()) else "mixed",
            "confidence": "medium",
            "rationale": "Capital changes propagate into land values through neighbor distance decay.",
        },
        transit_impact={
            "direction": "higher load" if any(v > 0 for v in params.sector_deltas.values()) else "lower demand",
            "confidence": "medium",
            "rationale": "Employment shifts change commuter pressure; monsoon months can add congestion.",
        },
        most_affected_areas=[
            "central high-activity H3 cells",
            "special economic zones near configured city corridors",
            "outer cells with higher informal and migration pressure",
        ],
        counter_intuitive=[
            "A positive investment shock can still reduce affordability near growth cells.",
            "Smart City or AMRUT policies can reduce congestion even while jobs rise.",
        ],
        overall_confidence="medium",
        reasoning=(
            f"Expected effects are driven by {', '.join(active) if active else 'policy and baseline'} "
            f"changes in {params.city_config.name}; policy context: {policy_text}."
        ),
    )


async def generate_prediction(params: SimulationParams) -> Prediction:
    """Generate prediction via LLM with deterministic fallback."""
    from app.config import settings

    provider = settings.llm_provider.lower()
    has_key = (
        (provider == "gemini" and settings.gemini_api_key)
        or (provider == "openai" and settings.openai_api_key)
        or (provider == "ollama")
    )

    if not has_key:
        logger.info("No LLM key configured for %s, using deterministic prediction", provider)
        return _deterministic_prediction(params)

    prompt = _build_prompt(params)

    try:
        if provider == "gemini":
            text = await _call_gemini(prompt, settings.llm_timeout_ms)
        elif provider == "openai":
            text = await _call_openai(prompt, settings.llm_timeout_ms)
        else:
            logger.warning("Unsupported LLM provider %s, using deterministic prediction", provider)
            return _deterministic_prediction(params)

        prediction = _parse_llm_response(text, params)
        logger.info("LLM prediction generated for %s via %s", params.city_config.name, provider)
        return prediction

    except Exception as e:
        logger.warning("LLM prediction failed (%s), falling back to deterministic: %s", provider, e)
        return _deterministic_prediction(params)
