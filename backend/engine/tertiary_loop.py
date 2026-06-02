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

    markdown = f"""## Simulation Results — {params.city_config.name}

**Verdict: {verdict}**

{verdict_detail}

MetroPulse produced a **scenario estimate** for **{params.city_config.name}** over **{params.horizon_months} months** in **{proof.get("dataMode", "estimated").replace("_", " ").title()}** mode using city baselines, retrieved evidence, real-time context when available, and deterministic H3 cell updates.

### Sector Drivers

{sector_breakdown}

### Key Metrics

- **GDP delta**: {gdp * 100:+.2f}%
- **Unemployment**: {unemployment * 100:.2f}%
- **Transit congestion**: {metrics["transitCongestion"] * 100:.1f}%
- **Housing affordability index**: {metrics["housingAffordability"]:.2f}
- **Informal employment share**: {metrics["informalEmployment"] * 100:.1f}%

### Expectation vs Model Output

- **Sector shocks → employment & land values**: GDP delta {gdp * 100:+.2f}%, unemployment {unemployment * 100:.2f}% — **{verdict}**
- **Transit pressure → commuter load**: Congestion at {metrics["transitCongestion"] * 100:.1f}% — {"increased" if metrics["transitCongestion"] > 0.5 else "managed"}
- **Housing affordability → real-estate pressure**: Index at {metrics["housingAffordability"]:.2f} — {"strained" if metrics["housingAffordability"] < 1.0 else "stable"}

### Key Findings

1. **Spatial effects are uneven.** The heatmap cells with taller columns combine capital movement, job pressure, and distance-decay spillovers.
2. **Informal employment matters.** The final informal employment share is **{metrics["informalEmployment"] * 100:.1f}%**, so the platform visualizes both formal and informal job density.
3. **Climate and policy modifiers are visible in the playback.** Monsoon months add flood pressure, while active policies dampen or redirect effects.

### Historical Precedents

{case_lines}

### Math & Data Proof

- Formula: `\\Delta K_sector = monthly_rate * sector_weight * K`; real estate and transit are updated by deterministic vector operations.
- Data quality: City YAML baselines, H3 geometry, configured sector weights, and proxy estimates where real datasets are not present.
- Cell count: **{final_frame["proof"]["cellCount"]}** H3 cells.
- Snapshot: **{proof.get("snapshotId") or "city baseline"}**, quality score **{proof.get("qualityScore", 0):.2f}**.

### Policy Recommendation

Pair the scenario shock with targeted transit and housing support in the most affected cells. Try comparing the same prompt with **AMRUT**, **PM Awas Yojana**, or **Smart City Mission** explicitly added.
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
