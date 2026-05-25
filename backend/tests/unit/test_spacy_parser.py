import pytest
from engine.nl_engine.spacy_parser import SpacyParser


@pytest.fixture
def parser():
    return SpacyParser()


def test_extract_city_gpe(parser):
    result = parser.parse("What if there is a tech boom in Mumbai?")
    assert result.city == "mumbai"


def test_extract_sector_from_noun_phrase(parser):
    result = parser.parse("Petrol prices are skyrocketing in Delhi")
    assert result.sector_deltas["transport_logistics"] != 0.0


def test_extract_percentage(parser):
    result = parser.parse("Manufacturing increased by 20% in Chennai")
    assert result.sector_deltas["manufacturing"] == 20.0


def test_magnitude_inference_strong_negative(parser):
    result = parser.parse("The devastating flood destroyed Mumbai's economy")
    assert result.city == "mumbai"
    total_delta = sum(result.sector_deltas.values())
    assert total_delta < 0


def test_confidence_with_city_and_sectors(parser):
    result = parser.parse("IT sector grows in Bengaluru")
    assert result.confidence in ("medium", "high")


def test_confidence_low_without_city(parser):
    result = parser.parse("Things are getting worse")
    assert result.confidence == "low"


def test_fuzzy_city_match(parser):
    result = parser.parse("What if it floods in Bombai?")  # typo
    assert result.city == "mumbai"
