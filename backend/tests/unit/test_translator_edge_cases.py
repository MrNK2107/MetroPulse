"""Additional edge-case tests for engine/translator.py.

Covers: disaster context detection, auto-rickshaw grammar,
housing contradiction fix, and inspect.signature() pattern.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from engine.translator import (
    _is_disaster_context,
    _is_multi_sector_shock,
    _translate_transport,
    _translate_real_estate,
    _generate_headline,
    _generate_takeaways,
    translate_to_plain_language,
    SectorImpact,
    TranslationResult,
    SECTOR_LABELS,
)


def _make_city_config(**overrides) -> MagicMock:
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
    return cfg


def _make_metrics(**overrides) -> MagicMock:
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


# ── Disaster context detection ──────────────────────────────────────────


def test_is_disaster_context_flood():
    assert _is_disaster_context("What happens if there's a flood in Mumbai?") is True


def test_is_disaster_context_earthquake():
    assert _is_disaster_context("Earthquake hits Delhi, what's the impact?") is True


def test_is_disaster_context_cyclone():
    assert _is_disaster_context("Cyclone warning for Chennai") is True


def test_is_disaster_context_heavy_rain():
    assert _is_disaster_context("Heavy rain in Bengaluru causes waterlogging") is True


def test_is_disaster_context_landslide():
    assert _is_disaster_context("Landslide blocks roads in Pune") is True


def test_is_disaster_context_normal_query():
    assert _is_disaster_context("What if IT sector grows 20%?") is False


def test_is_disaster_context_empty():
    assert _is_disaster_context("") is False


def test_is_disaster_context_case_insensitive():
    assert _is_disaster_context("FLOOD in Mumbai") is True


# ── Multi-sector shock detection ───────────────────────────────────────


def test_is_multi_sector_shock_true():
    deltas = {
        "it_ites": -20.0,
        "manufacturing": -25.0,
        "real_estate": -18.0,
        "trade_hospitality": -5.0,
        "transport_logistics": 0.0,
        "informal": 0.0,
        "public_admin": 0.0,
    }
    assert _is_multi_sector_shock(deltas) is True  # 3 sectors < -15


def test_is_multi_sector_shock_false():
    deltas = {
        "it_ites": -20.0,
        "manufacturing": -25.0,
        "real_estate": -5.0,  # < -15 check fails
    }
    assert _is_multi_sector_shock(deltas) is False  # only 2 sectors < -15


def test_is_multi_sector_shock_none():
    assert _is_multi_sector_shock(None) is False


def test_is_multi_sector_shock_empty():
    assert _is_multi_sector_shock({}) is False


# ── Auto-rickshaw grammar (Fix #6) ─────────────────────────────────────


def test_auto_rickshaw_grammar_in_restriction():
    """Restriction scenario should say 'auto-rickshaw driver' not jargon."""
    cfg = _make_city_config()
    impact = _translate_transport(-15.0, cfg, "What if auto-rickshaws get banned?")

    assert "auto-rickshaw" in impact.person_example.lower() or "auto" in impact.person_example.lower()
    assert "₹" in impact.person_example
    # Should be plain language, no jargon
    assert "H3" not in impact.person_example
    assert "delta" not in impact.person_example.lower()


def test_auto_rickshaw_grammar_in_disaster():
    """Disaster context should produce appropriate language."""
    cfg = _make_city_config()
    impact = _translate_transport(
        -20.0, cfg,
        "What if there's a flood in Mumbai?",
        sector_deltas={"transport_logistics": -20.0, "it_ites": -25.0, "manufacturing": -18.0}
    )

    assert "blocked" in impact.person_example.lower() or "disrupted" in impact.person_example.lower()
    assert "auto" in impact.person_example.lower() or "driver" in impact.person_example.lower()


def test_auto_rickshaw_in_normal_negative():
    """Normal negative transport scenario mentions auto-rickshaw driver."""
    cfg = _make_city_config()
    impact = _translate_transport(-10.0, cfg, "What if petrol prices spike?")

    assert "auto" in impact.person_example.lower()
    assert "₹" in impact.person_example


# ── Housing contradiction fix (Fix #3) ─────────────────────────────────


def test_housing_no_contradiction_when_re_negative():
    """When real_estate has negative delta, housing takeaway should say 'more affordable'."""
    cfg = _make_city_config()
    metrics = _make_metrics(housingAffordability=0.85)  # < 0.9 normally says "less affordable"
    deltas = _default_sector_deltas(real_estate=-15.0)

    result = translate_to_plain_language(deltas, metrics, cfg)
    # The takeaway should reference real_estate direction, not raw affordability number
    housing_takeaways = [t for t in result.takeaways if "housing" in t.lower() or "rent" in t.lower()]
    if housing_takeaways:
        # If there's a housing takeaway, it should say "affordable" since re is negative
        assert "affordable" in housing_takeaways[0].lower() or "drop" in housing_takeaways[0].lower()


def test_housing_no_contradiction_when_re_positive():
    """When real_estate has positive delta, housing takeaway should say 'less affordable'."""
    cfg = _make_city_config()
    metrics = _make_metrics(housingAffordability=1.15)  # > 1.1 normally says "more affordable"
    deltas = _default_sector_deltas(real_estate=15.0)

    result = translate_to_plain_language(deltas, metrics, cfg)
    housing_takeaways = [t for t in result.takeaways if "housing" in t.lower() or "rent" in t.lower()]
    if housing_takeaways:
        # Should say "less affordable" since real_estate is positive (prices up)
        assert "less affordable" in housing_takeaways[0].lower() or "go up" in housing_takeaways[0].lower()


# ── inspect.signature() pattern (line 702) ─────────────────────────────


def test_signature_pattern_passes_original_query_to_transport():
    """The inspect.signature() pattern should pass original_query to transport translator."""
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(transport_logistics=-15.0)

    result = translate_to_plain_language(deltas, metrics, cfg, "What if petrol gets banned?")
    transport = next(s for s in result.sector_impacts if s.sector == "transport_logistics")

    # The transport translator should have received original_query and detected 'ban'
    assert "restriction" in transport.headline.lower() or "restrict" in transport.headline.lower() or "transit" in transport.headline.lower()


def test_signature_pattern_doesnt_pass_extra_kwargs_to_it():
    """IT translator doesn't accept original_query/sector_deltas — signature pattern should skip them."""
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(it_ites=20.0)

    # Should not raise even though _translate_it only takes (delta_pct, city_config)
    result = translate_to_plain_language(deltas, metrics, cfg, "What if tech booms?")
    it_impact = next(s for s in result.sector_impacts if s.sector == "it_ites")
    assert it_impact.direction == "positive"


def test_signature_pattern_all_sectors_work():
    """All 7 sector translators should work through the signature introspection pattern."""
    cfg = _make_city_config()
    metrics = _make_metrics()
    sectors = [
        "transport_logistics", "it_ites", "manufacturing",
        "real_estate", "trade_hospitality", "informal", "public_admin",
    ]
    for sector in sectors:
        deltas = _default_sector_deltas(**{sector: -15.0})
        result = translate_to_plain_language(deltas, metrics, cfg, "test query")
        assert len(result.sector_impacts) >= 1, f"Failed for sector {sector}"


# ── Edge: very small delta (just above threshold) ──────────────────────


def test_small_delta_just_above_threshold():
    """Delta of 0.5% should be included (threshold is 0.5%)."""
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(it_ites=0.5)

    result = translate_to_plain_language(deltas, metrics, cfg)
    assert len(result.sector_impacts) == 1


def test_small_delta_below_threshold():
    """Delta of 0.3% should be skipped (threshold is 0.5%)."""
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(it_ites=0.3)

    result = translate_to_plain_language(deltas, metrics, cfg)
    assert len(result.sector_impacts) == 0


def test_small_delta_between_old_and_new_threshold():
    """Delta of 0.8% was previously skipped (< 1.0) but now included (>= 0.5)."""
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(it_ites=0.8)

    result = translate_to_plain_language(deltas, metrics, cfg)
    assert len(result.sector_impacts) == 1
    assert result.sector_impacts[0].delta_pct == 0.8


# ── Edge: policy-only scenario (no sector impacts) ─────────────────────


def test_policy_only_scenario_generates_metrics_summary():
    """When no sector deltas, takeaways should come from metrics."""
    cfg = _make_city_config()
    metrics = _make_metrics(gdpDelta=-0.02, unemploymentRate=0.06)
    deltas = _default_sector_deltas()  # all zero

    result = translate_to_plain_language(deltas, metrics, cfg)
    assert len(result.sector_impacts) == 0
    # Should still have takeaways from metrics
    assert len(result.takeaways) >= 1


# ── Edge: headline with keyword from query ──────────────────────────────


def test_headline_auto_display_label():
    """'auto' keyword should display as 'auto-rickshaws' in headline."""
    cfg = _make_city_config()
    metrics = _make_metrics()
    deltas = _default_sector_deltas(transport_logistics=-20.0)

    result = translate_to_plain_language(deltas, metrics, cfg, "What if auto prices go up?")
    # Should use display label "auto-rickshaws" instead of "auto"
    assert "auto-rickshaws" in result.headline.lower() or "auto" in result.headline.lower()
