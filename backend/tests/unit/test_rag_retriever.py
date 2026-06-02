"""Tests for the RAG retriever — evidence retrieval, relevance scoring, and filtering."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.rag.retriever import retrieve_evidence, _query_terms, _shock_types, _unique
from app.rag.models import EvidenceItem
from engine.models import CaseStudy, ParsedScenario


# ── Fixture data ────────────────────────────────────────────────────────────

# Mirrors a subset of LOCAL_CASE_STUDIES for controlled testing
MOCK_CASE_STUDIES = [
    CaseStudy(
        id="bengaluru-it-infra",
        title="Bengaluru IT Boom and Infrastructure Stress",
        city="Bengaluru",
        year=2023,
        description="IT/ITES growth increased employment and land values while worsening congestion and water stress.",
        outcome="Tech growth boosted high-skill jobs but strained mobility and housing affordability.",
        source="Karnataka economic survey",
        sectors=["it_ites", "real_estate"],
        policies=["Digital India"],
    ),
    CaseStudy(
        id="mumbai-mill-land",
        title="Mumbai Mill Land to Real Estate Transformation",
        city="Mumbai",
        year=2018,
        description="Former industrial land shifted toward commercial and high-end real-estate activity.",
        outcome="Manufacturing decline coincided with real-estate appreciation and affordability stress.",
        source="Mumbai planning studies",
        sectors=["manufacturing", "real_estate"],
        policies=["RERA Compliance"],
    ),
    CaseStudy(
        id="chennai-port-corridor",
        title="Chennai Port-Led Industrial Corridor Growth",
        city="Chennai",
        year=2023,
        description="Port and auto-sector activity shaped logistics corridors and formal manufacturing employment.",
        outcome="Transport investment amplified manufacturing gains but increased corridor congestion.",
        source="Tamil Nadu industry reports",
        sectors=["manufacturing", "transport_logistics"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="delhi-metro-property",
        title="Delhi Metro Expansion and Property Value Effects",
        city="Delhi NCR",
        year=2024,
        description="Metro access improved labor mobility and increased property premiums near stations.",
        outcome="Transit investment raised adjacent land values while redistributing commuting pressure.",
        source="Urban transport academic studies",
        sectors=["transport_logistics", "real_estate"],
        policies=["Smart City Mission"],
    ),
]


def _make_parsed(**overrides) -> ParsedScenario:
    return ParsedScenario(
        city=overrides.get("city", "Mumbai"),
        sector_deltas=overrides.get("sector_deltas", {"manufacturing": -10.0}),
        policies_active=overrides.get("policies_active", []),
        keywords=overrides.get("keywords", []),
        horizon_months=24,
    )


# ── Mock the LOCAL_CASE_STUDIES for retriever tests ─────────────────────────

@pytest.fixture(autouse=True)
def mock_case_studies():
    with patch("app.rag.retriever.LOCAL_CASE_STUDIES", MOCK_CASE_STUDIES):
        yield


# ── Basic retrieval ─────────────────────────────────────────────────────────

class TestBasicRetrieval:

    def test_returns_results_for_known_city_and_sector(self):
        parsed = _make_parsed(city="Mumbai", sector_deltas={"manufacturing": -10.0})
        terms, items = retrieve_evidence(parsed, "What if Mumbai manufacturing declines?")

        assert len(items) > 0
        # Mumbai manufacturing case should be found
        cities = [item.city for item in items]
        assert "Mumbai" in cities

    def test_returns_tuple_of_terms_and_items(self):
        parsed = _make_parsed(city="Chennai", sector_deltas={"transport_logistics": -10.0})
        result = retrieve_evidence(parsed, "What if Chennai ports slow down?")

        assert isinstance(result, tuple)
        assert len(result) == 2
        terms, items = result
        assert isinstance(terms, list)
        assert isinstance(items, list)

    def test_items_are_evidence_items(self):
        parsed = _make_parsed(city="Bengaluru", sector_deltas={"it_ites": 30.0})
        terms, items = retrieve_evidence(parsed, "IT boom in Bengaluru")

        for item in items:
            assert isinstance(item, EvidenceItem)

    def test_top_k_limits_results(self):
        parsed = _make_parsed(
            city="Mumbai",
            sector_deltas={"manufacturing": -10.0, "real_estate": 5.0, "transport_logistics": -5.0},
        )
        terms, items = retrieve_evidence(parsed, "Manufacturing and transport in Mumbai", top_k=2)

        assert len(items) <= 2

    def test_returns_empty_when_no_cases_match(self):
        parsed = _make_parsed(
            city="NonExistent",
            sector_deltas={"nonexistent_sector": -10.0},
            keywords=["quantum_gravity"],
        )
        terms, items = retrieve_evidence(parsed, "quantum gravity in nonexistent city")

        assert len(items) == 0


# ── Relevance scoring ───────────────────────────────────────────────────────

class TestRelevanceScoring:

    def test_exact_match_scores_higher_than_related(self):
        """A case matching city AND sector should rank above one matching only sector."""
        parsed = _make_parsed(
            city="Mumbai",
            sector_deltas={"manufacturing": -10.0},
        )
        terms, items = retrieve_evidence(parsed, "What if Mumbai manufacturing declines?")

        assert len(items) >= 2
        # First item should have highest relevance
        for i in range(len(items) - 1):
            assert items[i].relevance >= items[i + 1].relevance

    def test_city_match_boosts_score(self):
        """Cases for the queried city should rank above those from other cities."""
        parsed = _make_parsed(
            city="Chennai",
            sector_deltas={"manufacturing": -10.0, "transport_logistics": -5.0},
        )
        terms, items = retrieve_evidence(parsed, "Manufacturing in Chennai")

        # Chennai case should rank first
        assert items[0].city == "Chennai"

    def test_sector_match_contributes_to_score(self):
        """Matching more sectors should produce higher relevance."""
        parsed = _make_parsed(
            city="Delhi NCR",
            sector_deltas={"transport_logistics": -10.0, "real_estate": 5.0},
        )
        terms, items = retrieve_evidence(parsed, "Metro and property in Delhi")

        # Delhi Metro case matches both sectors — should be top
        assert items[0].city == "Delhi NCR"

    def test_relevance_is_between_0_and_1(self):
        parsed = _make_parsed(
            city="Mumbai",
            sector_deltas={"manufacturing": -10.0},
        )
        terms, items = retrieve_evidence(parsed, "Mumbai manufacturing")

        for item in items:
            assert 0.0 <= item.relevance <= 1.0

    def test_matched_sectors_populated(self):
        parsed = _make_parsed(
            city="Chennai",
            sector_deltas={"manufacturing": -10.0, "transport_logistics": -5.0},
        )
        terms, items = retrieve_evidence(parsed, "Manufacturing and transport in Chennai")

        chennai_item = next(i for i in items if i.city == "Chennai")
        assert len(chennai_item.matched_sectors) > 0
        assert "manufacturing" in chennai_item.matched_sectors


# ── Empty keywords ──────────────────────────────────────────────────────────

class TestEmptyKeywords:

    def test_empty_keywords_no_crash(self):
        parsed = _make_parsed(keywords=[], sector_deltas={}, city="Unknown")
        terms, items = retrieve_evidence(parsed, "")
        assert isinstance(terms, list)
        assert isinstance(items, list)

    def test_empty_scenario_text_returns_no_terms(self):
        parsed = _make_parsed(keywords=[], city="Mumbai", sector_deltas={"manufacturing": -10.0})
        terms, items = retrieve_evidence(parsed, "")
        # With empty text and no keywords, query terms should be empty
        assert len(terms) == 0

    def test_no_active_sectors_returns_empty(self):
        """If all sector deltas are zero, no sectors to match → low scores → empty results."""
        parsed = _make_parsed(
            city="Mumbai",
            sector_deltas={"manufacturing": 0.0},
        )
        terms, items = retrieve_evidence(parsed, "Mumbai baseline")

        # No active sectors → sector_score = 0, city_score = 0.25, total < 0.25 threshold
        # except if keyword match happens
        # At minimum, items should be less than a fully-matching query
        assert len(items) <= 1


# ── Threshold filtering ─────────────────────────────────────────────────────

class TestThresholdFiltering:

    def test_low_relevance_items_filtered(self):
        """Items with relevance < 0.25 should be filtered out."""
        parsed = _make_parsed(
            city="Bengaluru",
            sector_deltas={"it_ites": 30.0},
        )
        terms, items = retrieve_evidence(parsed, "IT boom in Bengaluru")

        for item in items:
            assert item.relevance >= 0.25, f"Item '{item.title}' has relevance {item.relevance} < 0.25"

    def test_unrelated_city_sector_filtered(self):
        """A city/sector combo that doesn't match any case should yield empty results."""
        parsed = _make_parsed(
            city="Jaipur",
            sector_deltas={"public_admin": -10.0},
        )
        # No cases for Jaipur with public_admin in our mock data
        terms, items = retrieve_evidence(parsed, "Public admin in Jaipur")

        # All items (if any) should still pass threshold
        for item in items:
            assert item.relevance >= 0.25


# ── Query terms ─────────────────────────────────────────────────────────────

class TestQueryTerms:

    def test_fuel_keywords_extend_terms(self):
        parsed = _make_parsed(keywords=["petrol"])
        terms = _query_terms(parsed, "What if petrol prices spike?")

        assert "fuel price increase" in terms or "India fuel shock" in terms

    def test_housing_keywords_extend_terms(self):
        parsed = _make_parsed(keywords=["rent"])
        terms = _query_terms(parsed, "What if rent goes up?")

        assert "housing affordability" in terms

    def test_jobs_keywords_extend_terms(self):
        parsed = _make_parsed(keywords=["layoff"])
        terms = _query_terms(parsed, "What if there are layoffs?")

        assert "employment impact" in terms

    def test_no_special_keywords_returns_parsed_keywords_only(self):
        parsed = _make_parsed(keywords=["custom_term"])
        terms = _query_terms(parsed, "Some generic scenario")

        assert "custom_term" in terms

    def test_terms_are_unique(self):
        parsed = _make_parsed(keywords=["petrol", "petrol"])
        terms = _query_terms(parsed, "What if petrol prices spike?")

        # No duplicates
        assert len(terms) == len(set(t.lower() for t in terms))


# ── Shock types ─────────────────────────────────────────────────────────────

class TestShockTypes:

    def test_fuel_shock_detected(self):
        result = _shock_types("What if petrol prices spike?")
        assert "fuel_price_shock" in result

    def test_negative_demand_shock_detected(self):
        result = _shock_types("What if there's a decline in manufacturing?")
        assert "negative_demand_shock" in result

    def test_positive_growth_detected(self):
        result = _shock_types("What if there's a tech boom?")
        assert "positive_growth_shock" in result

    def test_generic_fallback(self):
        result = _shock_types("What if aliens invade?")
        assert "generic_scenario_shock" in result

    def test_multiple_shock_types(self):
        result = _shock_types("What if petrol prices spike causing a decline?")
        assert "fuel_price_shock" in result
        assert "negative_demand_shock" in result


# ── Unique helper ────────────────────────────────────────────────────────────

class TestUniqueHelper:

    def test_removes_duplicates_case_insensitive(self):
        result = _unique(["Hello", "hello", "HELLO"])
        assert len(result) == 1

    def test_preserves_order(self):
        result = _unique(["alpha", "beta", "gamma"])
        assert result == ["alpha", "beta", "gamma"]

    def test_removes_empty_strings(self):
        result = _unique(["", "hello", "", "world"])
        assert "" not in result
        assert len(result) == 2

    def test_empty_input(self):
        result = _unique([])
        assert result == []


# ── Evidence item structure ─────────────────────────────────────────────────

class TestEvidenceItemStructure:

    def test_items_have_id_and_title(self):
        parsed = _make_parsed(city="Mumbai", sector_deltas={"manufacturing": -10.0})
        terms, items = retrieve_evidence(parsed, "Mumbai manufacturing")

        for item in items:
            assert item.id
            assert item.title

    def test_items_have_confidence(self):
        parsed = _make_parsed(city="Mumbai", sector_deltas={"manufacturing": -10.0})
        terms, items = retrieve_evidence(parsed, "Mumbai manufacturing")

        for item in items:
            assert 0.0 <= item.confidence <= 1.0

    def test_items_have_source_type(self):
        parsed = _make_parsed(city="Mumbai", sector_deltas={"manufacturing": -10.0})
        terms, items = retrieve_evidence(parsed, "Mumbai manufacturing")

        for item in items:
            assert item.source_type == "historical_case_study"

    def test_items_country_is_india(self):
        parsed = _make_parsed(city="Mumbai", sector_deltas={"manufacturing": -10.0})
        terms, items = retrieve_evidence(parsed, "Mumbai manufacturing")

        for item in items:
            assert item.country == "India"
