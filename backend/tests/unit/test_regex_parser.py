import pytest
from engine.nl_engine.regex_parser import RegexParser


@pytest.fixture
def parser():
    return RegexParser()


def test_parse_explicit_percentage(parser):
    result = parser.parse("Manufacturing drops 40% in Mumbai")
    assert result.city == "mumbai"
    assert result.sector_deltas["manufacturing"] == -40.0
    assert parser.last_confidence >= 0.8


def test_parse_positive_delta(parser):
    result = parser.parse("IT sector grows 25% in Bengaluru")
    assert result.city == "bengaluru"
    assert result.sector_deltas["it_ites"] == 25.0


def test_parse_synonym_petrol(parser):
    result = parser.parse("Petrol prices spike in Chennai")
    assert result.city == "chennai"
    assert result.sector_deltas["transport_logistics"] != 0.0


def test_parse_cause_effect(parser):
    result = parser.parse("Heavy rainfall devastates Mumbai")
    assert result.city == "mumbai"
    assert result.sector_deltas["informal"] < 0


def test_parse_no_city_returns_low_confidence(parser):
    result = parser.parse("Manufacturing drops 40%")
    assert parser.last_confidence <= 0.5


def test_parse_neighborhood_alias(parser):
    result = parser.parse("Tech boom in Koramangala")
    assert result.city == "bengaluru"


def test_parse_horizon_explicit(parser):
    result = parser.parse("IT grows 20% in Hyderabad for 12 months")
    assert result.city == "hyderabad"
    assert result.horizon_months == 12


def test_parse_horizon_default(parser):
    result = parser.parse("Manufacturing drops in Mumbai")
    assert result.horizon_months == 24


def test_parse_policy_detection(parser):
    result = parser.parse("SEZ policy applied in Chennai with manufacturing +15%")
    assert "SEZ Notification" in result.policies_active


def test_parse_vague_growth(parser):
    result = parser.parse("Tech boom in Bangalore")
    assert result.city == "bengaluru"
    assert result.sector_deltas["it_ites"] > 0


def test_parse_increased_by_format(parser):
    result = parser.parse("Fuel increased by 15% in Delhi")
    assert result.city == "delhi_ncr"
    assert result.sector_deltas["transport_logistics"] == 15.0
