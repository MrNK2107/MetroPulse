"""Tests for the tertiary-loop evidence synthesis engine."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from engine.models import (
    AggregateMetrics,
    CaseStudy,
    Prediction,
    SectorPrediction,
    SimulationParams,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_city_config(**overrides) -> MagicMock:
    cfg = MagicMock()
    cfg.name = overrides.get("name", "Mumbai")
    cfg.population = overrides.get("population", 20_700_000)
    cfg.baselines = overrides.get("baselines", {
        "employment_formal": 4_500_000,
        "employment_informal": 7_000_000,
        "gdp_estimate_crores": 800_000,
        "slum_population_pct": 0.42,
        "unemployment_rate": 0.04,
    })
    cfg.sector_weights = overrides.get("sector_weights", {
        "it_ites": 0.12,
        "manufacturing": 0.18,
        "real_estate": 0.22,
        "trade_hospitality": 0.18,
        "transport_logistics": 0.12,
        "informal": 0.12,
        "public_admin": 0.06,
    })
    cfg.center = [19.0760, 72.8777]
    cfg.city_type = "financial"
    cfg.metro_system = True
    cfg.monsoon_season = [6, 7, 8, 9]
    return cfg


def _make_params(**overrides) -> SimulationParams:
    cfg = overrides.get("city_config", _make_city_config())
    return SimulationParams(
        city=overrides.get("city", "mumbai"),
        sector_deltas=overrides.get("sector_deltas", {"transport_logistics": -15.0}),
        policies_active=overrides.get("policies_active", []),
        public_works_zone=None,
        horizon_months=overrides.get("horizon_months", 12),
        city_config=cfg,
        assumptions=overrides.get("assumptions", ["Fuel prices remain elevated"]),
        evidence_pack=overrides.get("evidence_pack", None),
    )


def _make_metrics(**overrides) -> dict:
    return {
        "gdpDelta": overrides.get("gdpDelta", -0.015),
        "unemploymentRate": overrides.get("unemploymentRate", 0.05),
        "realEstateIndex": overrides.get("realEstateIndex", 0.95),
        "transitCongestion": overrides.get("transitCongestion", 0.65),
        "informalEmployment": overrides.get("informalEmployment", 0.35),
        "housingAffordability": overrides.get("housingAffordability", 0.92),
        "floodDisruption": overrides.get("floodDisruption", 0.0),
        "migrationBalance": overrides.get("migrationBalance", 0.0),
    }


def _make_prediction(**overrides) -> Prediction:
    return Prediction(
        employment_impact={
            "transport_logistics": SectorPrediction(
                direction="down",
                magnitude="high",
                confidence="medium",
                rationale="Fuel shock reduces transport activity",
            )
        },
        counter_intuitive=overrides.get("counter_intuitive", []),
        overall_confidence=overrides.get("overall_confidence", "medium"),
        reasoning="Transport shock propagates through logistics corridors",
    )


def _make_case_study(**overrides) -> CaseStudy:
    return CaseStudy(
        id=overrides.get("id", "test-case-1"),
        title=overrides.get("title", "Chennai Port-Led Industrial Corridor Growth"),
        city=overrides.get("city", "Chennai"),
        year=overrides.get("year", 2023),
        description=overrides.get("description", "Port and auto-sector activity shaped logistics corridors."),
        outcome=overrides.get("outcome", "Transport investment amplified manufacturing gains."),
        source="Tamil Nadu industry reports",
        sectors=overrides.get("sectors", ["manufacturing", "transport_logistics"]),
        policies=overrides.get("policies", ["Make in India"]),
        relevance_tier=overrides.get("relevance_tier", "exact"),
    )


def _make_final_frame(**overrides) -> dict:
    return {
        "metrics": overrides.get("metrics", _make_metrics()),
        "proof": overrides.get("proof", {
            "dataMode": "estimated",
            "cellCount": 42,
            "snapshotId": "baseline",
            "qualityScore": 0.55,
            "overallConfidence": 0.55,
            "activeEffects": ["fuel_shock"],
        }),
        "metric_metadata": overrides.get("metric_metadata", {}),
    }


def _make_translation_result():
    tr = MagicMock()
    tr.headline = "Mumbai transport jobs at risk from fuel price spike"
    tr.sector_impacts = [
        MagicMock(
            sector="transport_logistics",
            direction="negative",
            headline="Transport jobs declining",
            person_example="A delivery driver in Mumbai could see ₹8,000 less per month",
            city_wide="About 81,000 transport workers across Mumbai feel the pressure",
            numbers={"jobs_affected": 81000},
        ),
    ]
    tr.takeaways = ["Transport costs rise for daily commuters", "Logistics sector sees reduced margins"]
    tr.gdp_summary = "Mumbai's GDP could shrink by ₹12,000 crore"
    tr.unemployment_summary = "Unemployment could rise to 5.2%"
    tr.overall_verdict = "Negative impact on transport sector"
    return tr


# ── Verdict logic ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("gdp_delta,expected", [
    (-0.008, "Confirmed"),   # |gdp| > 0.005 (0.5%)
    (0.008, "Confirmed"),
    (-0.003, "Partially Confirmed"),  # |gdp| <= 0.005
    (0.003, "Partially Confirmed"),
])
@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_verdict_confirmed_when_gdp_above_threshold(
    mock_translate, mock_explain, mock_format, mock_build,
    gdp_delta, expected,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame(metrics=_make_metrics(gdpDelta=gdp_delta))
    case_studies = [_make_case_study()]

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, case_studies)

    assert result["verdict"] == expected


@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_verdict_surprise_when_gdp_drops_but_sectors_positive(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    # GDP drops below -2% AND some sector deltas are positive
    params = _make_params(sector_deltas={"transport_logistics": -15.0, "it_ites": 5.0})
    prediction = _make_prediction()
    frame = _make_final_frame(metrics=_make_metrics(gdpDelta=-0.03))
    case_studies = [_make_case_study()]

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, case_studies)

    assert result["verdict"] == "Surprise"


@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_verdict_partially_confirmed_when_no_prediction(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    frame = _make_final_frame(metrics=_make_metrics(gdpDelta=0.008))  # > 0.005 but no prediction

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, None, frame, [])

    assert result["verdict"] == "Partially Confirmed"


# ── Markdown output ─────────────────────────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_markdown_contains_expected_sections(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()
    case_studies = [_make_case_study()]

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, case_studies)

    md = result["markdown"]
    assert "## Simulation Results" in md
    assert "### Expectation vs Model Output" in md
    assert "### Key Findings" in md
    assert "### Historical Precedents" in md
    assert "### Math & Data Proof" in md
    assert "### Policy Recommendation" in md
    # City name should appear
    assert "Mumbai" in md


@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_simple_markdown_contains_headline_and_takeaways(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()
    case_studies = [_make_case_study()]

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, case_studies)

    simple = result["simple_markdown"]
    assert "## " in simple  # headline
    assert "What this means for you" in simple  # takeaways section
    assert "Overall:" in simple  # verdict


# ── Empty case studies ───────────────────────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_empty_case_studies_produces_no_precedent_message(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, [])

    md = result["markdown"]
    assert "No close historical precedent" in md


# ── Missing prediction (None) ───────────────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_missing_prediction_produces_partially_confirmed(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    frame = _make_final_frame(metrics=_make_metrics(gdpDelta=-0.015))

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, None, frame, [])

    assert result["verdict"] == "Partially Confirmed"
    assert result["translation"] is not None
    assert "headline" in result["translation"]


# ── Evidence pack with low vs high confidence ────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_evidence_pack_high_confidence(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()
    evidence_pack = {"overall_evidence_confidence": 0.85, "items": [{"title": "strong evidence"}]}

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(
        params, prediction, frame, [], evidence_pack=evidence_pack,
    )

    assert result["evidence_pack"] is not None
    assert result["evidence_pack"]["overall_evidence_confidence"] == 0.85


@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_evidence_pack_low_confidence(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()
    evidence_pack = {"overall_evidence_confidence": 0.25, "items": []}

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(
        params, prediction, frame, [], evidence_pack=evidence_pack,
    )

    assert result["evidence_pack"]["overall_evidence_confidence"] == 0.25


# ── Return structure completeness ───────────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_result_has_all_required_keys(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()
    case_studies = [_make_case_study()]

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, case_studies)

    required_keys = [
        "simple_markdown", "markdown", "translation", "verdict",
        "metrics", "proof", "assumptions", "driver_explanations",
        "explanation_narrative", "explainability", "evidence_pack",
        "metric_metadata", "case_retrieval",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"


# ── Translation sub-structure ───────────────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_translation_sub_structure(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, [])

    translation = result["translation"]
    assert "headline" in translation
    assert "sector_impacts" in translation
    assert "takeaways" in translation
    assert "gdp_summary" in translation
    assert "unemployment_summary" in translation
    assert "overall_verdict" in translation
    assert isinstance(translation["sector_impacts"], list)


# ── Case retrieval defaults ─────────────────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_case_retrieval_populated_from_params_when_not_supplied(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params(sector_deltas={"transport_logistics": -15.0})
    prediction = _make_prediction()
    frame = _make_final_frame()

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, [])

    cr = result["case_retrieval"]
    assert cr["query_city"] == "mumbai"
    assert "transport_logistics" in cr["query_sectors"]
    assert cr["retrieval_mode"] == "strict"


# ── Case retrieval override ─────────────────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_case_retrieval_override(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()
    override_cr = {"query_city": "custom", "returned_count": 10}

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(
        params, prediction, frame, [], case_retrieval=override_cr,
    )

    assert result["case_retrieval"]["query_city"] == "custom"


# ── Assumptions include counter-intuitive from prediction ───────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_counter_intuitive_in_assumptions(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params(assumptions=["Base assumption"])
    prediction = _make_prediction(counter_intuitive=["IT might boom despite transport shock"])
    frame = _make_final_frame()

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, [])

    assert "Base assumption" in result["assumptions"]
    assert "IT might boom despite transport shock" in result["assumptions"]


# ── Weak relevance tier cases filtered ───────────────────────────────────────

@patch("engine.tertiary_loop.build_explanation", return_value={})
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_weak_cases_excluded_from_markdown(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()
    # Only weak cases — should show fallback message
    weak_cases = [_make_case_study(relevance_tier="weak", title="Weak Case")]

    from engine.tertiary_loop import synthesize_evidence
    result = synthesize_evidence(params, prediction, frame, weak_cases)

    assert "No close historical precedent" in result["markdown"]


# ── Explainability failure is handled gracefully ─────────────────────────────

@patch("engine.tertiary_loop.build_explanation", side_effect=Exception("boom"))
@patch("engine.tertiary_loop.format_explanation_narrative", return_value="")
@patch("engine.tertiary_loop.explain_metric_deltas", return_value={})
@patch("engine.tertiary_loop.translate_to_plain_language")
def test_explainability_failure_handled_gracefully(
    mock_translate, mock_explain, mock_format, mock_build,
):
    mock_translate.return_value = _make_translation_result()
    params = _make_params()
    prediction = _make_prediction()
    frame = _make_final_frame()

    from engine.tertiary_loop import synthesize_evidence
    # Should not raise
    result = synthesize_evidence(params, prediction, frame, [])

    assert result["verdict"] is not None
    assert result["explainability"] == {}
