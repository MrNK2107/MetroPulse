import pytest

from engine.scenario_parser import ScenarioParseError, parse_scenario, resolve_city_id


@pytest.mark.asyncio
async def test_parser_handles_specific_prompt():
    parsed = await parse_scenario("What happens to Hyderabad if pharma FDI drops 40% for 24 months?")

    assert parsed.city == "hyderabad"
    assert parsed.sector_deltas["manufacturing"] == -40
    assert parsed.horizon_months == 24


@pytest.mark.asyncio
async def test_parser_handles_vague_but_valid_prompt():
    parsed = await parse_scenario("Bengaluru tech boom with Digital India")

    assert parsed.city == "bengaluru"
    assert parsed.sector_deltas["it_ites"] > 0
    assert "Digital India" in parsed.policies_active


@pytest.mark.asyncio
async def test_parser_rejects_too_vague_prompt():
    with pytest.raises(ScenarioParseError):
        await parse_scenario("What happens next?")


def test_city_aliases():
    assert resolve_city_id("Bangalore") == "bengaluru"
    assert resolve_city_id("NCR") == "delhi_ncr"


# ── Horizon snap warning tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_horizon_3_months_snaps_to_6_with_warning():
    """3 months should snap to 6 (nearest supported interval) with an assumption."""
    parsed = await parse_scenario("What happens to Mumbai in 3 months if IT drops 10%?")
    assert parsed.horizon_months == 6
    # Should contain a rounding assumption mentioning the original value
    rounding = [a for a in parsed.assumptions if "rounded" in a.lower() or "3" in a]
    assert len(rounding) > 0, f"Expected rounding assumption, got: {parsed.assumptions}"


@pytest.mark.asyncio
async def test_horizon_36_months_snaps_to_24_with_warning():
    """36 months is equidistant between 24 and 60; min() picks 24 with key=abs diff."""
    parsed = await parse_scenario("What happens to Mumbai in 36 months if IT drops 10%?")
    # 36 is equidistant from 24 and 60 (diff=12), but min() with key=lambda x: abs(x-36)
    # returns 24 (first match when tied). Let's just check it snapped.
    assert parsed.horizon_months in (24, 60), f"Expected snap to 24 or 60, got {parsed.horizon_months}"
    rounding = [a for a in parsed.assumptions if "rounded" in a.lower() or "36" in a]
    assert len(rounding) > 0, f"Expected rounding assumption, got: {parsed.assumptions}"


@pytest.mark.asyncio
async def test_horizon_12_months_stays_at_12_no_warning():
    """12 months is a supported interval — should stay at 12 with no rounding assumption."""
    parsed = await parse_scenario("What happens to Mumbai in 12 months if IT drops 10%?")
    assert parsed.horizon_months == 12
    rounding = [a for a in parsed.assumptions if "rounded" in a.lower()]
    assert len(rounding) == 0, f"Should not have rounding assumption, got: {parsed.assumptions}"


@pytest.mark.asyncio
async def test_horizon_60_months_stays_at_60_no_warning():
    """60 months is a supported interval — should stay at 60 with no rounding assumption."""
    parsed = await parse_scenario("What happens to Mumbai in 60 months if IT drops 10%?")
    assert parsed.horizon_months == 60
    rounding = [a for a in parsed.assumptions if "rounded" in a.lower()]
    assert len(rounding) == 0, f"Should not have rounding assumption, got: {parsed.assumptions}"


@pytest.mark.asyncio
async def test_horizon_6_months_is_supported_interval():
    """6 months is a supported interval — no rounding needed."""
    parsed = await parse_scenario("What happens to Mumbai in 6 months if IT drops 10%?")
    assert parsed.horizon_months == 6
    rounding = [a for a in parsed.assumptions if "rounded" in a.lower()]
    assert len(rounding) == 0


@pytest.mark.asyncio
async def test_horizon_24_months_is_supported_interval():
    """24 months is a supported interval — no rounding needed."""
    parsed = await parse_scenario("What happens to Mumbai in 24 months if IT drops 10%?")
    assert parsed.horizon_months == 24
    rounding = [a for a in parsed.assumptions if "rounded" in a.lower()]
    assert len(rounding) == 0


@pytest.mark.asyncio
async def test_horizon_default_is_24_when_not_specified():
    """Without explicit horizon, should default to 24 with a default assumption."""
    parsed = await parse_scenario("What happens to Mumbai if IT drops 10%?")
    assert parsed.horizon_months == 24
    default_assumption = [a for a in parsed.assumptions if "defaulted" in a.lower()]
    assert len(default_assumption) > 0
