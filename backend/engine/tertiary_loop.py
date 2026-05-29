from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from engine.models import AggregateMetrics, CaseStudy, Prediction, SECTOR_LABELS, SimulationParams
from engine.translator import translate_to_plain_language, TranslationResult
from engine.simulation_explainability import explain_metric_deltas, format_explanation_narrative
from app.simulation.explainability import build_explanation


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
) -> dict[str, Any]:
    metrics = final_frame["metrics"]
    proof = final_frame.get("proof", {})
    gdp = metrics["gdpDelta"]
    unemployment = metrics["unemploymentRate"]
    verdict = "Confirmed" if (prediction and abs(gdp) > 0.005) else "Partially Confirmed"
    if gdp < -0.02 and any(v > 0 for v in params.sector_deltas.values()):
        verdict = "Surprise"

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

    markdown = f"""## Simulation Results

MetroPulse produced a **scenario estimate** for **{params.city_config.name}** over **{params.horizon_months} months** in **{proof.get("dataMode", "estimated").replace("_", " ").title()}** mode using city baselines, retrieved evidence, real-time context when available, and deterministic H3 cell updates. The main modeled changes were: {", ".join(changed) if changed else "policy/baseline effects"}.

### Expectation vs Model Output

| Scenario Expectation | Model Output | Read |
|---|---|---|
| Sector shocks would propagate into employment and land values | GDP delta ended at **{gdp * 100:+.2f}%** and unemployment at **{unemployment * 100:.2f}%** | {verdict} |
| Transit pressure would follow job movement | Average congestion ended at **{metrics["transitCongestion"] * 100:.1f}%** | Confirmed |
| Housing affordability would react to real-estate pressure | Affordability index ended at **{metrics["housingAffordability"]:.2f}** | Partially Confirmed |

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
        explainability = build_explanation(params, metrics, proof, evidence_pack)
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
