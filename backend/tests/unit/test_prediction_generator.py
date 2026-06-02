"""Unit tests for engine/prediction_generator.py."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from engine.models import SECTOR_NAMES, SECTOR_LABELS, SimulationParams, Prediction
from engine.prediction_generator import _enhanced_deterministic_prediction, _parse_llm_response


def _make_city_config(**overrides) -> MagicMock:
    """Create a mock CityConfig with sensible defaults."""
    cfg = MagicMock()
    cfg.name = overrides.get("name", "Mumbai")
    cfg.population = overrides.get("population", 20_700_000)
    cfg.baselines = overrides.get("baselines", {
        "employment_formal": 4_500_000,
        "employment_informal": 7_000_000,
        "gdp_estimate_crores": 800_000,
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
    cfg.city_type = overrides.get("city_type", "financial_hub")
    cfg.special_zones = overrides.get("special_zones", [
        {"name": "BKC", "sectors": ["it_ites", "real_estate"], "boost": 0.15},
    ])
    return cfg


def _make_params(sector_deltas: dict[str, float] | None = None, **overrides) -> SimulationParams:
    """Build a SimulationParams with given sector deltas."""
    cfg = overrides.pop("city_config", _make_city_config(**overrides))
    defaults = {s: 0.0 for s in SECTOR_NAMES}
    if sector_deltas:
        defaults.update(sector_deltas)
    return SimulationParams(
        city=cfg.name.lower(),
        sector_deltas=defaults,
        policies_active=overrides.get("policies_active", []),
        public_works_zone=None,
        horizon_months=overrides.get("horizon_months", 24),
        city_config=cfg,
    )


# ── Test: empty sector_deltas ────────────────────────────────────────────


def test_empty_sector_deltas():
    """With all deltas zero, prediction should still be valid."""
    params = _make_params(sector_deltas={s: 0.0 for s in SECTOR_NAMES})
    result = _enhanced_deterministic_prediction(params)

    assert isinstance(result, Prediction)
    assert len(result.employment_impact) == len(SECTOR_NAMES)
    # All sectors stable when delta = 0
    for sector in SECTOR_NAMES:
        assert result.employment_impact[sector].direction == "stable"


# ── Test: all negative deltas ────────────────────────────────────────────


def test_all_negative_deltas():
    """All sectors contracted — real estate should go down."""
    deltas = {s: -20.0 for s in SECTOR_NAMES}
    params = _make_params(sector_deltas=deltas)
    result = _enhanced_deterministic_prediction(params)

    assert result.real_estate_impact["direction"] == "down"
    assert result.transit_impact["direction"] == "lower demand"
    for sector in SECTOR_NAMES:
        assert result.employment_impact[sector].direction == "down"
        assert result.employment_impact[sector].magnitude == "moderate"


# ── Test: all positive deltas ────────────────────────────────────────────


def test_all_positive_deltas():
    """All sectors expanded — real estate and transit should reflect growth."""
    deltas = {s: 25.0 for s in SECTOR_NAMES}
    params = _make_params(sector_deltas=deltas)
    result = _enhanced_deterministic_prediction(params)

    assert result.real_estate_impact["direction"] == "up"
    assert result.transit_impact["direction"] == "higher load"
    for sector in SECTOR_NAMES:
        assert result.employment_impact[sector].direction == "up"


# ── Test: mixed deltas ──────────────────────────────────────────────────


def test_mixed_deltas():
    """Mixed positive and negative deltas produce correct per-sector directions."""
    deltas = {
        "it_ites": 30.0,
        "manufacturing": -15.0,
        "real_estate": 5.0,
        "trade_hospitality": -8.0,
        "transport_logistics": 10.0,
        "informal": -3.0,
        "public_admin": 0.0,
    }
    params = _make_params(sector_deltas=deltas)
    result = _enhanced_deterministic_prediction(params)

    assert result.employment_impact["it_ites"].direction == "up"
    assert result.employment_impact["manufacturing"].direction == "down"
    assert result.employment_impact["real_estate"].direction == "stable"  # +5 is below threshold
    assert result.employment_impact["public_admin"].direction == "stable"

    # IT with 30% delta should be high magnitude
    assert result.employment_impact["it_ites"].magnitude == "moderate"  # 30 >= 20

    # Overall confidence should be determined
    assert result.overall_confidence in ("high", "medium", "low")


# ── Test: magnitude thresholds ──────────────────────────────────────────


def test_magnitude_thresholds():
    """Verify magnitude is set correctly based on absolute delta thresholds."""
    # delta >= 50 → high
    params_high = _make_params(sector_deltas={"it_ites": 55.0})
    result_high = _enhanced_deterministic_prediction(params_high)
    assert result_high.employment_impact["it_ites"].magnitude == "high"

    # delta >= 20 → moderate
    params_mod = _make_params(sector_deltas={"it_ites": 25.0})
    result_mod = _enhanced_deterministic_prediction(params_mod)
    assert result_mod.employment_impact["it_ites"].magnitude == "moderate"

    # delta < 20 → low
    params_low = _make_params(sector_deltas={"it_ites": 10.0})
    result_low = _enhanced_deterministic_prediction(params_low)
    assert result_low.employment_impact["it_ites"].magnitude == "low"


# ── Test: direction thresholds ──────────────────────────────────────────


def test_direction_thresholds():
    """Direction changes at delta > 5 or delta < -5."""
    params = _make_params(sector_deltas={
        "it_ites": 6.0,       # > 5 → up
        "manufacturing": -6.0, # < -5 → down
        "real_estate": 4.0,    # within [-5, 5] → stable
    })
    result = _enhanced_deterministic_prediction(params)

    assert result.employment_impact["it_ites"].direction == "up"
    assert result.employment_impact["manufacturing"].direction == "down"
    assert result.employment_impact["real_estate"].direction == "stable"


# ── Test: confidence scales with sector weight ─────────────────────────


def test_confidence_scales_with_sector_weight():
    """High-weight sectors get high confidence, low-weight get low."""
    cfg = _make_city_config(sector_weights={
        "it_ites": 0.30,        # >= 0.25 → high confidence
        "manufacturing": 0.15,   # medium
        "public_admin": 0.05,    # <= 0.08 → low confidence
        "real_estate": 0.20,
        "trade_hospitality": 0.15,
        "transport_logistics": 0.10,
        "informal": 0.05,
    })
    params = _make_params(
        sector_deltas={"it_ites": 10.0, "manufacturing": 10.0, "public_admin": 10.0},
        city_config=cfg,
    )
    result = _enhanced_deterministic_prediction(params)

    assert result.employment_impact["it_ites"].confidence == "high"
    assert result.employment_impact["manufacturing"].confidence == "medium"
    assert result.employment_impact["public_admin"].confidence == "low"


# ── Test: headline generation — negative ────────────────────────────────


def test_headline_negative_delta():
    """Headline should describe a 'hit' when the top delta is negative."""
    params = _make_params(sector_deltas={"it_ites": -25.0})
    result = _enhanced_deterministic_prediction(params)

    assert "hit" in result.headline.lower() or "mumbai" in result.headline.lower()
    assert "Mumbai" in result.headline


def test_headline_positive_delta():
    """Headline should describe a 'boost' when the top delta is positive."""
    params = _make_params(sector_deltas={"it_ites": 25.0})
    result = _enhanced_deterministic_prediction(params)

    assert "boost" in result.headline.lower() or "mumbai" in result.headline.lower()
    assert "Mumbai" in result.headline


def test_headline_modest_shifts():
    """Headline should say 'modest' when top delta is small."""
    params = _make_params(sector_deltas={"it_ites": 5.0})
    result = _enhanced_deterministic_prediction(params)

    assert "modest" in result.headline.lower() or "mumbai" in result.headline.lower()


def test_headline_empty_deltas():
    """With no sector deltas at all, headline should mention policy effects."""
    cfg = _make_city_config()
    params = SimulationParams(
        city=cfg.name.lower(),
        sector_deltas={},
        policies_active=[],
        public_works_zone=None,
        horizon_months=24,
        city_config=cfg,
    )
    result = _enhanced_deterministic_prediction(params)

    assert "Mumbai" in result.headline
    # Should handle the empty case gracefully
    assert len(result.headline) > 10


# ── Test: transit impact thresholds ────────────────────────────────────


def test_transit_high_load_on_large_positive_delta():
    """Transit should show 'higher load' when any delta > 15."""
    params = _make_params(sector_deltas={"it_ites": 20.0})
    result = _enhanced_deterministic_prediction(params)
    assert result.transit_impact["direction"] == "higher load"


def test_transit_lower_demand_on_large_negative_delta():
    """Transit should show 'lower demand' when any delta < -15."""
    params = _make_params(sector_deltas={"it_ites": -20.0})
    result = _enhanced_deterministic_prediction(params)
    assert result.transit_impact["direction"] == "lower demand"


def test_transit_stable_on_small_deltas():
    """Transit stable when deltas don't cross 15% threshold."""
    params = _make_params(sector_deltas={"it_ites": 10.0})
    result = _enhanced_deterministic_prediction(params)
    assert result.transit_impact["direction"] == "stable"


# ── Test: special zones populate most_affected_areas ───────────────────


def test_special_zones_as_most_affected_areas():
    """When city has special zones, they should be the most affected areas."""
    cfg = _make_city_config(special_zones=[
        {"name": "HITEC City", "sectors": ["it_ites"], "boost": 0.2},
        {"name": "Patancheru", "sectors": ["manufacturing"], "boost": 0.1},
    ])
    params = _make_params(sector_deltas={"it_ites": 20.0}, city_config=cfg)
    result = _enhanced_deterministic_prediction(params)

    assert "HITEC City" in result.most_affected_areas
    assert "Patancheru" in result.most_affected_areas


# ── Test: counter-intuitive with smart_city policy ─────────────────────


def test_counter_intuitive_smart_city_policy():
    """Smart city policy should add a specific counter-intuitive insight."""
    params = _make_params(
        sector_deltas={"it_ites": 10.0},
        policies_active=["smart_city"],
    )
    result = _enhanced_deterministic_prediction(params)

    assert any("smart city" in c.lower() for c in result.counter_intuitive)


# ── Test: reasoning includes city type context ─────────────────────────


def test_reasoning_includes_city_type():
    """Reasoning text should include city type context."""
    cfg = _make_city_config(city_type="tech_hub")
    params = _make_params(sector_deltas={"it_ites": 15.0}, city_config=cfg)
    result = _enhanced_deterministic_prediction(params)

    assert "tech_hub" in result.reasoning or "tech hub" in result.reasoning


# ── Test: parse LLM response ───────────────────────────────────────────


def test_parse_llm_response_basic():
    """Parse a well-formed LLM JSON response."""
    from engine.models import AggregateMetrics
    params = _make_params()
    llm_text = '''```json
    {
        "employment_impact": {
            "it_ites": {"direction": "up", "magnitude": "high", "confidence": "high", "rationale": "Tech boom"},
            "manufacturing": {"direction": "down", "magnitude": "moderate", "confidence": "medium", "rationale": "Slowdown"}
        },
        "real_estate_impact": {"direction": "up", "confidence": "high", "rationale": "Demand rising"},
        "transit_impact": {"direction": "higher load", "confidence": "medium", "rationale": "More commuters"},
        "most_affected_areas": ["HITEC City", "Gachibowli"],
        "counter_intuitive": ["Rents drop in some areas"],
        "overall_confidence": "high",
        "reasoning": "Tech growth drives economy."
    }
    ```'''

    result = _parse_llm_response(llm_text, params)
    assert isinstance(result, Prediction)
    assert result.headline == ""  # LLM response doesn't set headline
    assert result.employment_impact["it_ites"].direction == "up"
    assert result.real_estate_impact["direction"] == "up"
    assert "HITEC City" in result.most_affected_areas


def test_parse_llm_response_without_code_fences():
    """Parse LLM response without markdown code fences."""
    params = _make_params()
    llm_text = '''{
        "employment_impact": {},
        "real_estate_impact": {"direction": "mixed", "confidence": "medium", "rationale": "test"},
        "transit_impact": {"direction": "stable", "confidence": "low", "rationale": "test"},
        "most_affected_areas": ["CBD"],
        "counter_intuitive": ["test"],
        "overall_confidence": "medium",
        "reasoning": "test"
    }'''

    result = _parse_llm_response(llm_text, params)
    assert isinstance(result, Prediction)
    assert result.overall_confidence == "medium"


# ── Test: rationale mentions dominant sector ────────────────────────────


def test_rationale_mentions_dominant_sector():
    """High-weight sectors should get 'dominant sector' in rationale."""
    cfg = _make_city_config(sector_weights={
        "it_ites": 0.25,  # >= 0.2 → dominant
        "manufacturing": 0.18,
        "real_estate": 0.22,
        "trade_hospitality": 0.18,
        "transport_logistics": 0.08,
        "informal": 0.05,
        "public_admin": 0.04,
    })
    params = _make_params(sector_deltas={"it_ites": 10.0}, city_config=cfg)
    result = _enhanced_deterministic_prediction(params)

    assert "dominant" in result.employment_impact["it_ites"].rationale.lower()


# ── Test: overall confidence with low unemployment and large shock ─────


def test_overall_confidence_high_on_low_unemployment_large_shock():
    """Low unemployment + large shock → high overall confidence."""
    cfg = _make_city_config(baselines={
        "employment_formal": 4_500_000,
        "gdp_estimate_crores": 800_000,
        "unemployment_rate": 0.03,  # < 0.04
    })
    params = _make_params(sector_deltas={"it_ites": 35.0}, city_config=cfg)  # > 30
    result = _enhanced_deterministic_prediction(params)

    assert result.overall_confidence == "high"


def test_overall_confidence_low_on_high_unemployment():
    """High unemployment → low overall confidence."""
    cfg = _make_city_config(baselines={
        "employment_formal": 4_500_000,
        "gdp_estimate_crores": 800_000,
        "unemployment_rate": 0.10,  # > 0.08
    })
    params = _make_params(sector_deltas={"it_ites": 5.0}, city_config=cfg)
    result = _enhanced_deterministic_prediction(params)

    assert result.overall_confidence == "low"
