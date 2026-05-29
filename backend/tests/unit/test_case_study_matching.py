import pytest

from app.db import DatabaseClient, build_case_study_context
from engine.config import CityConfig
from engine.nl_engine.router import IntentRouter


CITY_PROMPTS = {
    "ahmedabad": "Manufacturing grows 10% in Ahmedabad",
    "bengaluru": "IT grows 10% in Bengaluru",
    "bhubaneswar": "Government services grow 10% in Bhubaneswar",
    "chandigarh": "Real estate grows 10% in Chandigarh",
    "chennai": "Transport logistics grows 10% in Chennai",
    "delhi_ncr": "Transport logistics grows 10% in Delhi NCR",
    "hyderabad": "Manufacturing grows 10% in Hyderabad",
    "jaipur": "Tourism grows 10% in Jaipur",
    "kolkata": "Transport logistics grows 10% in Kolkata",
    "lucknow": "Street vendor activity drops 10% in Lucknow",
    "mumbai": "Real estate drops 10% in Mumbai",
    "pune": "IT grows 10% in Pune",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("city_id,prompt", CITY_PROMPTS.items())
async def test_all_supported_cities_parse_and_load(city_id, prompt):
    parsed, _ = await IntentRouter().route(prompt)
    assert parsed.city == city_id
    assert CityConfig.load(parsed.city).name


@pytest.mark.asyncio
async def test_hyderabad_pharma_search_excludes_unrelated_housing():
    router = IntentRouter()
    parsed, _ = await router.route("What happens to Hyderabad if pharma FDI drops 40% for 24 months?")
    db = DatabaseClient()
    studies = await db.search_case_studies(
        parsed.keywords,
        city=parsed.city,
        context=build_case_study_context(parsed, original_query=parsed.causal_chain),
    )

    ids = [study.id for study in studies]
    assert ids[0] == "hyderabad-pharma-sez"
    assert "pmay-national-housing" not in ids
    assert all(study.relevance_tier in {"exact", "related"} for study in studies)


@pytest.mark.asyncio
async def test_same_city_sector_ranks_above_cross_city_related_cases():
    db = DatabaseClient()
    context = build_case_study_context(
        city="hyderabad",
        sectors=["manufacturing"],
        keywords=["hyderabad", "manufacturing", "pharma"],
    )
    studies = await db.search_case_studies([], city="hyderabad", sector="manufacturing", context=context)

    assert studies[0].id == "hyderabad-pharma-sez"
    assert studies[0].relevance_tier == "exact"
    assert all(study.id != "pmay-national-housing" for study in studies)


@pytest.mark.asyncio
async def test_bengaluru_tech_boom_does_not_drift_to_secondary_real_estate_cases():
    parsed, _ = await IntentRouter().route("Bengaluru tech boom with Digital India")
    db = DatabaseClient()
    studies = await db.search_case_studies(
        parsed.keywords,
        city=parsed.city,
        context=build_case_study_context(parsed, original_query=parsed.causal_chain),
    )

    ids = [study.id for study in studies]
    assert "bengaluru-it-infra" in ids
    assert "pune-it-corridor" in ids
    assert "jaipur-tourism-heritage" not in ids


@pytest.mark.asyncio
async def test_cross_city_related_cases_appear_without_same_city_topic_match():
    db = DatabaseClient()
    context = build_case_study_context(
        city="mumbai",
        sectors=["transport_logistics"],
        keywords=["mumbai", "transport", "logistics"],
    )
    studies = await db.search_case_studies([], city="mumbai", sector="transport_logistics", context=context)

    assert studies
    assert all(study.relevance_tier == "related" for study in studies)
    assert all("transport_logistics" in study.matched_sectors for study in studies)
    assert all(study.id != "mumbai-mill-land" for study in studies)
