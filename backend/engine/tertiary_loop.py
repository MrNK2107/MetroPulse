from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from engine.models import AggregateMetrics, CaseStudy, Prediction, SECTOR_LABELS, SimulationParams
from engine.translator import translate_to_plain_language, TranslationResult
from engine.simulation_explainability import explain_metric_deltas, format_explanation_narrative


def synthesize_evidence(
    params: SimulationParams,
    prediction: Prediction | None,
    final_frame: dict[str, Any],
    case_studies: list[CaseStudy],
    original_query: str = "",
    group_impacts: list[Any] | None = None,
    case_retrieval: dict[str, Any] | None = None,
    evidence_pack: dict[str, Any] | None = None,
    grid_state: Any | None = None,
    explainability_fn=None,
) -> dict[str, Any]:
    metrics = final_frame["metrics"]
    proof = final_frame.get("proof", {})
    gdp = metrics["gdpDelta"]
    unemployment = metrics["unemploymentRate"]

    # ── Nuanced verdict with sector and policy context ──────────────────────
    positive_shocks = {s: v for s, v in params.sector_deltas.items() if v > 0}
    negative_shocks = {s: v for s, v in params.sector_deltas.items() if v < 0}
    has_prediction = prediction is not None
    gdp_positive = gdp > 0.005
    gdp_negative = gdp < -0.005
    gdp_neutral = abs(gdp) <= 0.005

    # Identify which sectors drove the result
    weights = params.city_config.sector_weights or {}
    driving_sectors = sorted(
        params.sector_deltas.items(),
        key=lambda item: abs(item[1]) * weights.get(item[0], 0.1),
        reverse=True,
    )[:3]
    driving_labels = [f"{SECTOR_LABELS[s]} ({v:+.0f}%)" for s, v in driving_sectors if abs(v) > 0]
    driver_text = ", ".join(driving_labels) if driving_labels else "policy and baseline effects"

    # Identify policy impacts
    active_policies = params.policies_active or []
    policy_text = ", ".join(active_policies) if active_policies else "no explicit policies"

    # Determine verdict
    if has_prediction and positive_shocks and gdp_positive:
        verdict = "Confirmed"
        verdict_detail = (
            f"Positive sector shocks in {driver_text} produced the expected GDP uplift. "
            f"Active policies ({policy_text}) reinforced the growth trajectory."
        )
    elif has_prediction and negative_shocks and gdp_negative:
        verdict = "Confirmed"
        verdict_detail = (
            f"Negative shocks in {driver_text} produced the expected contraction. "
            f"Active policies ({policy_text}) partially mitigated the decline."
        )
    elif has_prediction and gdp_neutral:
        verdict = "Partially Confirmed"
        verdict_detail = (
            f"Sector changes in {driver_text} had limited aggregate GDP impact, "
            f"suggesting policy offsets ({policy_text}) absorbed much of the shock. "
            f"Check sector-level and cell-level views for localized effects."
        )
    elif gdp_negative and positive_shocks:
        verdict = "Surprise — Counter-Intuitive"
        verdict_detail = (
            f"Despite positive shocks in {driver_text}, GDP declined, "
            f"indicating second-order effects (congestion, affordability, informal displacement) "
            f"may be dominating. Active policies ({policy_text}) were insufficient to offset."
        )
    elif gdp_positive and negative_shocks:
        verdict = "Surprise — Resilience"
        verdict_detail = (
            f"Despite negative shocks in {driver_text}, GDP held up or improved, "
            f"suggesting policy buffers ({policy_text}) or informal sector absorption compensated."
        )
    elif has_prediction:
        verdict = "Partially Confirmed"
        verdict_detail = (
            f"Scenario effects from {driver_text} were partially reflected in model outputs. "
            f"Policy context ({policy_text}) shaped the magnitude."
        )
    else:
        verdict = "Baseline Estimate"
        verdict_detail = (
            f"No LLM prediction was available; model output reflects deterministic simulation "
            f"with {driver_text} and policy context ({policy_text})."
        )

    changed = [
        f"{SECTOR_LABELS.get(sector, sector)} {value:+.0f}%"
        for sector, value in params.sector_deltas.items()
        if abs(value) > 0
    ]
    close_cases = [case for case in case_studies if case.relevance_tier in {"exact", "related"}]
    case_lines = "\n".join(
        f"- **{case.title} ({case.year})**: {case.outcome or case.description[:180]}"
        for case in close_cases[:4]
    ) or "- No close historical precedent found for this scenario; evidence relies on simulation outputs."

    # Sector breakdown for markdown
    sector_breakdown = "\n".join(
        f"- **{SECTOR_LABELS[s]}**: {v:+.0f}% shock × {weights.get(s, 0.1):.0%} city weight"
        for s, v in driving_sectors if abs(v) > 0
    ) or "- No explicit sector shocks; policy-only scenario."

    markdown = f"""## What this means for {params.city_config.name}

**{verdict}** — {verdict_detail}

We ran a {params.horizon_months}-month simulation for {params.city_config.name} using city economic data, real-time signals when available, and neighborhood-level analysis. Here's what we found.

### What changed and why

{chr(10).join(
    f"- **{SECTOR_LABELS[s]}** {'grew' if v > 0 else 'contracted'} by {abs(v):.0f}% — it makes up about {int(weights.get(s, 0.1) * 100)}% of {params.city_config.name}'s economy"
    for s, v in driving_sectors if abs(v) > 0
) if driving_sectors else "- No major sector changes were modeled in this scenario."}

### The big picture

The city's economy {'grew' if gdp > 0 else 'contracted'} by about **{abs(gdp * 100):.1f}%**. About **{unemployment * 100:.1f}%** of people are looking for work. Traffic {'got heavier' if metrics['transitCongestion'] > 0.5 else 'stayed manageable'} — about {int(metrics['transitCongestion'] * 10)} in 10 roads are congested. Housing is {'under pressure' if metrics['housingAffordability'] < 1.0 else 'relatively stable'}, and about {metrics['informalEmployment'] * 100:.0f}% of jobs are in the informal sector.

### Did we expect this?

{"The numbers match what we expected — the economy moved in line with the scenario." if "Confirmed" in verdict else "The results surprised us somewhat — the model found some effects we didn't fully anticipate."} {verdict_detail}

### What stood out

1. The changes are not spread evenly across the city — some neighborhoods feel the impact much more than others.
2. About {metrics['informalEmployment'] * 100:.0f}% of the city's workers are in the informal economy, so official numbers may not capture the full picture.
3. Weather patterns and active government policies can amplify or soften the effects over time.

### Historical Precedents

{case_lines}

### How we calculated this

We used city economic data, satellite and mapping information, and historical patterns from similar cities. The analysis covers **{final_frame['proof']['cellCount']}** neighborhoods across {params.city_config.name}. Data quality score: **{proof.get('qualityScore', 0):.0%}**.

### What could help

Consider investing in public transport and affordable housing in the areas most affected. Government programs like **AMRUT**, **PM Awas Yojana**, or **Smart City Mission** could make a real difference if targeted at these neighborhoods.
"""

    # ── Plain-language translation ──────────────────────────────────────────
    translation = translate_to_plain_language(
        params.sector_deltas,
        AggregateMetrics(**metrics) if isinstance(metrics, dict) else metrics,
        params.city_config,
        original_query,
    )

    # Build simple markdown from translation
    simple_lines: list[str] = []
    simple_lines.append(f"## {translation.headline}")
    simple_lines.append("")

    for impact in translation.sector_impacts[:3]:
        icon = "\u2b06\ufe0f" if impact.direction == "positive" else "\u2b07\ufe0f"
        simple_lines.append(f"### {icon} {impact.headline}")
        simple_lines.append("")
        simple_lines.append(f"**{impact.person_example}**")
        simple_lines.append("")
        simple_lines.append(impact.city_wide)
        simple_lines.append("")

    if translation.takeaways:
        simple_lines.append("### What this means for you")
        simple_lines.append("")
        for i, takeaway in enumerate(translation.takeaways, 1):
            simple_lines.append(f"{i}. {takeaway}")
        simple_lines.append("")

    simple_lines.append(f"**{translation.gdp_summary}**")
    simple_lines.append(f"**{translation.unemployment_summary}**")
    simple_lines.append("")
    simple_lines.append(f"*Overall: {translation.overall_verdict}*")

    simple_markdown = "\n".join(simple_lines)

    # ── Driver explanations ────────────────────────────────────────────────
    driver_explanations: dict[str, Any] = {}
    explanation_narrative = ""
    explainability: dict[str, Any] = {}
    try:
        driver_explanations = explain_metric_deltas(params, metrics, proof)
        explanation_narrative = format_explanation_narrative(driver_explanations)
        if explainability_fn is not None:
            explainability = explainability_fn(params, metrics, proof, evidence_pack)
    except Exception as e:
        logger.warning("Explainability generation failed: %s", e)

    assumptions = list(params.assumptions)
    if prediction and prediction.counter_intuitive:
        assumptions.extend(prediction.counter_intuitive)

    return {
        "simple_markdown": simple_markdown,
        "markdown": markdown,
        "translation": {
            "headline": translation.headline,
            "sector_impacts": [
                {
                    "sector": si.sector,
                    "sector_label": si.sector_label,
                    "delta_pct": si.delta_pct,
                    "direction": si.direction,
                    "headline": si.headline,
                    "person_example": si.person_example,
                    "city_wide": si.city_wide,
                    "numbers": si.numbers,
                }
                for si in translation.sector_impacts
            ],
            "takeaways": translation.takeaways,
            "gdp_summary": translation.gdp_summary,
            "unemployment_summary": translation.unemployment_summary,
            "overall_verdict": translation.overall_verdict,
        },
        "verdict": verdict,
        "metrics": metrics,
        "proof": final_frame.get("proof", {}),
        "assumptions": assumptions,
        "driver_explanations": driver_explanations,
        "explanation_narrative": explanation_narrative,
        "explainability": explainability,
        "evidence_pack": evidence_pack or params.evidence_pack,
        "metric_metadata": final_frame.get("metric_metadata", {}),
        "case_retrieval": case_retrieval or {
            "query_city": params.city,
            "query_sectors": [sector for sector, value in params.sector_deltas.items() if abs(value) > 0],
            "query_policies": params.policies_active,
            "returned_count": len(close_cases),
            "omitted_weak_count": 0,
            "retrieval_mode": "strict",
        },
    }
