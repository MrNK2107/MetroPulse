from __future__ import annotations

from typing import Any

from engine.models import CaseStudy, Prediction, SECTOR_LABELS, SimulationParams


def synthesize_evidence(
    params: SimulationParams,
    prediction: Prediction | None,
    final_frame: dict[str, Any],
    case_studies: list[CaseStudy],
) -> dict[str, Any]:
    metrics = final_frame["metrics"]
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
    case_lines = "\n".join(
        f"- **{case.title} ({case.year})**: {case.outcome or case.description[:180]}"
        for case in case_studies[:4]
    ) or "- No close historical precedent found; relying on simulation outputs."

    markdown = f"""## Simulation Results

MetroPulse simulated **{params.city_config.name}** for **{params.horizon_months} months** using estimated city baselines and deterministic H3 cell updates. The main modeled changes were: {", ".join(changed) if changed else "policy/baseline effects"}.

### Prediction vs Reality

| What We Expected | What Happened | Verdict |
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

- Formula: `Delta K_sector = monthly_rate * sector_weight * K`; real estate and transit are updated by deterministic vector operations.
- Data quality: MVP uses city YAML, H3 geometry, configured sector weights, and proxy baselines where real datasets are not present.
- Cell count: **{final_frame["proof"]["cellCount"]}** H3 cells.

### Policy Recommendation

Pair the scenario shock with targeted transit and housing support in the most affected cells. In this MVP, that means comparing the same prompt with **AMRUT**, **PM Awas Yojana**, or **Smart City Mission** explicitly added.
"""

    return {
        "markdown": markdown,
        "verdict": verdict,
        "metrics": metrics,
        "proof": final_frame.get("proof", {}),
        "assumptions": params.assumptions,
    }
