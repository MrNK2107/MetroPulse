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
