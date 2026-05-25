import pytest
from engine.nl_engine.router import IntentRouter


@pytest.fixture
def router():
    return IntentRouter()


@pytest.mark.asyncio
async def test_regex_path_for_explicit_input(router):
    result, confidence = await router.route("Manufacturing drops 40% in Mumbai")
    assert result.city == "mumbai"
    assert confidence >= 0.8


@pytest.mark.asyncio
async def test_spacy_path_for_natural_language(router):
    result, confidence = await router.route("What if petrol prices spike in Delhi?")
    assert result.city == "delhi_ncr"
    assert result.sector_deltas["transport_logistics"] != 0.0


@pytest.mark.asyncio
async def test_router_returns_parsed_scenario(router):
    result, confidence = await router.route("Tech boom in Bengaluru")
    assert result.city == "bengaluru"
    assert confidence > 0.0
