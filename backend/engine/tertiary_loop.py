from __future__ import annotations

import json
from typing import Any

from engine.grid import GridState
from engine.models import SimulationParams


def build_query(params: SimulationParams, final_metrics: dict[str, Any]) -> str:
    parts = []
    if params.fdi.tech != 0:
        parts.append(f"Tech FDI {params.fdi.tech:+.0f}%")
    if params.fdi.manufacturing != 0:
        parts.append(f"Manufacturing FDI {params.fdi.manufacturing:+.0f}%")
    if params.fdi.realEstate != 0:
        parts.append(f"Real Estate FDI {params.fdi.realEstate:+.0f}%")
    if params.publicWorksZone is not None:
        zone_type = params.publicWorksZone.get("type", "zone")
        parts.append(f"Public works in {zone_type.lower()}")
    parts.append(f"{params.horizonMonths}-month horizon")

    query = ", ".join(parts)
    return query


def build_prompt(
    params: SimulationParams,
    final_metrics: dict[str, Any],
    case_studies: list[dict[str, Any]],
) -> str:
    params_json = json.dumps(params.model_dump(), indent=2)
    metrics_json = json.dumps(final_metrics, indent=2)

    precedents_text = "No historical precedents found."
    if case_studies:
        excerpts = []
        for cs in case_studies:
            excerpts.append(
                f"- **{cs.get('title', 'Untitled')}** ({cs.get('city', 'Unknown')}, {cs.get('year', 'N/A')}): "
                f"{cs.get('description', '')[:300]}"
            )
        precedents_text = "\n".join(excerpts)

    prompt = f"""You are an urban economics analyst. A simulation has been run with the following parameters:
<params>{params_json}</params>

The simulation produced these outcomes after {params.horizonMonths} months:
<outcome>{metrics_json}</outcome>

Historical precedents from similar urban interventions:
<precedents>
{precedents_text}
</precedents>

Provide a concise analysis in 5-7 markdown bullet points covering:
- Key risks identified from the historical precedents
- Sectors most vulnerable given the parameters
- Any counter-intuitive outcomes to watch for
- One recommended policy adjustment based on the data"""

    return prompt


FALLBACK_INSIGHT = """## AI Analysis

The simulation completed successfully. Key observations:

- **GDP impact**: Review the aggregate metrics for overall economic effect
- **Sector vulnerability**: Check FDI-specific sector deltas in the map view
- **Geographic spread**: Higher color intensity indicates greater impact areas

*Detailed AI-powered case synthesis requires an LLM API key to be configured.*"""


async def synthesize(
    params: SimulationParams,
    state: GridState,
    db: Any = None,
) -> str:
    from secondary_loop import compute_aggregate_metrics

    final_metrics = compute_aggregate_metrics(state)
    case_studies: list[dict[str, Any]] = []
    if db is not None:
        try:
            case_studies = await db.search_case_studies([0.0] * 1536)
        except Exception:
            case_studies = []

    prompt = build_prompt(params, final_metrics, case_studies)

    try:
        return await _call_llm(prompt)
    except Exception:
        return FALLBACK_INSIGHT


async def _call_llm(prompt: str) -> str:
    api_key = __import__("os").environ.get("OPENAI_API_KEY")
    if not api_key:
        return FALLBACK_INSIGHT

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.7,
    )

    return response.choices[0].message.content or FALLBACK_INSIGHT
