"""Tests for the plain-language translation engine."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from engine.translator import (
    SectorImpact,
    TranslationResult,
    translate_to_plain_language,
    _generate_headline,
    _generate_takeaways,
    _find_user_keyword,
    _compute_jobs_at_risk,
)


def _make_city_config(**overrides) -> MagicMock:
    """Create a mock CityConfig with sensible defaults."""
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
    return cfg


def _make_metrics(**overrides) -> MagicMock:
    """Create a mock AggregateMetrics with defaults."""
    m = MagicMock()
    m.gdpDelta = overrides.get("gdpDelta", -0.015)
    m.unemploymentRate = overrides.get("unemploymentRate", 0.05)
    m.realEstateIndex = overrides.get("realEstateIndex", 0.95)
    m.transitCongestion = overrides.get("transitCongestion", 0.65)
    m.informalEmployment = overrides.get("informalEmployment", 0.35)
    m.housingAffordability = overrides.get("housingAffordability", 0.92)
    m.floodDisruption = overrides.get("floodDisruption", 0.0)
    m.migrationBalance = overrides.get("migrationBalance", 0.0)
    return m


def _default_sector_deltas(**overrides) -> dict[str, float]:
    defaults = {s: 0.0 for s in [
        "it_ites", "manufacturing", "real_estate", "trade_hospitality",
        "transport_logistics", "informal", "public_admin",
    ]}
    defaults.update(overrides)
    return defaults


# ── Test: transport negative delta ────────────────────────────────────────

def test_translate_transport_negative_delta():
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(transport_logistics=-15.0)

    result = translate_to_plain_language(deltas, metrics, cfg, "What if petrol prices spike?")

    assert len(result.sector_impacts) >= 1
    transport = next(s for s in result.sector_impacts if s.sector == "transport_logistics")
    assert "\u20b9" in transport.person_example  # contains ₹
    assert "jobs" in transport.city_wide.lower() or "workers" in transport.city_wide.lower()
    assert transport.delta_pct == -15.0
    assert transport.numbers["jobs_affected"] > 0


# ── Test: IT positive delta ───────────────────────────────────────────────

def test_translate_it_positive_delta():
    cfg = _make_city_config(name="Hyderabad", baselines={
        "employment_formal": 2_400_000,
        "gdp_estimate_crores": 320_000,
        "unemployment_rate": 0.04,
    })
    metrics = _make_metrics(gdpDelta=0.02, unemploymentRate=0.03)
    deltas = _default_sector_deltas(it_ites=25.0)

    result = translate_to_plain_language(deltas, metrics, cfg, "What if there's a tech boom?")

    it_impact = next(s for s in result.sector_impacts if s.sector == "it_ites")
    assert "\u20b9" in it_impact.person_example
    assert it_impact.numbers["new_jobs"] > 0
    assert it_impact.delta_pct == 25.0


# ── Test: headline references original query ──────────────────────────────

def test_headline_references_original_query():
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(transport_logistics=-15.0)

    result = translate_to_plain_language(deltas, metrics, cfg, "What if petrol prices spike?")
    # The headline should mention "petrol" or "fuel" since the user asked about petrol
    headline_lower = result.headline.lower()
    assert "petrol" in headline_lower or "fuel" in headline_lower or "transport" in headline_lower


def test_headline_works_without_query():
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(manufacturing=-20.0)

    result = translate_to_plain_language(deltas, metrics, cfg, "")
    assert "Mumbai" in result.headline
    assert "manufacturing" in result.headline.lower() or "factory" in result.headline.lower()


# ── Test: all 7 sectors translatable ──────────────────────────────────────

def test_all_seven_sectors_translatable():
    cfg = _make_city_config()
    metrics = _make_metrics()

    sectors = [
        "transport_logistics", "it_ites", "manufacturing",
        "real_estate", "trade_hospitality", "informal", "public_admin",
    ]
    for sector in sectors:
        deltas = _default_sector_deltas(**{sector: -15.0})
        result = translate_to_plain_language(deltas, metrics, cfg)
        assert len(result.sector_impacts) >= 1, f"No impact for {sector}"
        impact = result.sector_impacts[0]
        assert impact.sector == sector
        assert len(impact.person_example) > 10
        assert len(impact.city_wide) > 10


# ── Test: different cities produce different amounts ──────────────────────

def test_numbers_differ_by_city():
    mumbai = _make_city_config(name="Mumbai", population=20_700_000, baselines={
        "employment_formal": 4_500_000,
        "gdp_estimate_crores": 800_000,
        "unemployment_rate": 0.04,
    })
    lucknow = _make_city_config(name="Lucknow", population=3_500_000, baselines={
        "employment_formal": 800_000,
        "gdp_estimate_crores": 90_000,
        "unemployment_rate": 0.06,
    })
    metrics = _make_metrics()
    deltas = _default_sector_deltas(transport_logistics=-15.0)

    mumbai_result = translate_to_plain_language(deltas, metrics, mumbai)
    lucknow_result = translate_to_plain_language(deltas, metrics, lucknow)

    mumbai_jobs = mumbai_result.sector_impacts[0].numbers["jobs_affected"]
    lucknow_jobs = lucknow_result.sector_impacts[0].numbers["jobs_affected"]
    assert mumbai_jobs != lucknow_jobs
    assert mumbai_jobs > lucknow_jobs  # Mumbai has more workers


# ── Test: zero delta produces no impact ───────────────────────────────────

def test_zero_delta_produces_no_impact():
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas()  # all zeros

    result = translate_to_plain_language(deltas, metrics, cfg)
    assert len(result.sector_impacts) == 0


# ── Test: GDP summary format ─────────────────────────────────────────────

def test_gdp_summary_format():
    cfg = _make_city_config()
    metrics = _make_metrics(gdpDelta=-0.02)
    deltas = _default_sector_deltas(transport_logistics=-15.0)

    result = translate_to_plain_language(deltas, metrics, cfg)
    assert "\u20b9" in result.gdp_summary  # contains ₹
    assert "crore" in result.gdp_summary.lower()


# ── Test: takeaways exist and are plain language ─────────────────────────

def test_takeaways_are_plain_language():
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(transport_logistics=-15.0, informal=-10.0)

    result = translate_to_plain_language(deltas, metrics, cfg, "What if petrol prices spike?")
    assert len(result.takeaways) >= 2
    for takeaway in result.takeaways:
        assert len(takeaway) > 10  # not empty or trivial
        # Should not contain jargon
        assert "H3" not in takeaway
        assert "delta" not in takeaway.lower()


# ── Test: _find_user_keyword helper ──────────────────────────────────────

def test_find_user_keyword():
    assert _find_user_keyword("What if petrol prices spike?", "transport_logistics") == "petrol"
    assert _find_user_keyword("Tech boom in Hyderabad", "it_ites") == "tech"  # "tech" is a keyword for IT
    assert _find_user_keyword("What if rent goes up?", "real_estate") == "rent"
    assert _find_user_keyword("", "transport_logistics") is None


# ── Test: _compute_jobs_at_risk helper ───────────────────────────────────

def test_compute_jobs_at_risk():
    cfg = _make_city_config(baselines={"employment_formal": 4_500_000}, sector_weights={
        "transport_logistics": 0.12,
    })
    jobs = _compute_jobs_at_risk(cfg, "transport_logistics", 15.0)
    # 4,500,000 * 0.12 * 15/100 = 81,000
    assert jobs > 0
    assert jobs == 81_000


# ── Test: overall verdict ─────────────────────────────────────────────────

def test_overall_verdict():
    cfg = _make_city_config()
    # Negative scenario
    metrics_neg = _make_metrics(gdpDelta=-0.03, unemploymentRate=0.07, housingAffordability=0.8)
    deltas = _default_sector_deltas(transport_logistics=-15.0)
    result_neg = translate_to_plain_language(deltas, metrics_neg, cfg)
    assert "negative" in result_neg.overall_verdict.lower()

    # Positive scenario
    metrics_pos = _make_metrics(gdpDelta=0.03, unemploymentRate=0.03, housingAffordability=1.1)
    deltas_pos = _default_sector_deltas(it_ites=25.0)
    result_pos = translate_to_plain_language(deltas_pos, metrics_pos, cfg)
    assert "positive" in result_pos.overall_verdict.lower() or "growth" in result_pos.overall_verdict.lower()
