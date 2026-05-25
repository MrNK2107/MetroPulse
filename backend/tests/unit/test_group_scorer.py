import pytest
from engine.nl_engine.group_scorer import GroupImpact, score_groups, classify_severity, compute_satisfaction
from engine.models import AggregateMetrics


def make_metrics(**overrides) -> AggregateMetrics:
    defaults = {
        "gdpDelta": 0.0,
        "unemploymentRate": 0.0,
        "realEstateIndex": 1.0,
        "transitCongestion": 0.5,
        "informalEmployment": 0.3,
        "housingAffordability": 1.0,
        "floodDisruption": 0.0,
        "migrationBalance": 0.0,
    }
    defaults.update(overrides)
    return AggregateMetrics(**defaults)


def make_sector_deltas(**overrides) -> dict[str, float]:
    defaults = {
        "it_ites": 0.0,
        "manufacturing": 0.0,
        "real_estate": 0.0,
        "trade_hospitality": 0.0,
        "transport_logistics": 0.0,
        "informal": 0.0,
        "public_admin": 0.0,
    }
    defaults.update(overrides)
    return defaults


def test_score_groups_returns_all_groups():
    metrics = make_metrics()
    deltas = make_sector_deltas()
    groups = score_groups(deltas, metrics)
    group_names = [g.name for g in groups]
    assert "farmers" in group_names
    assert "students" in group_names
    assert "small_businesses" in group_names
    assert len(groups) == 7


def test_farmers_hurt_by_fuel_hike():
    metrics = make_metrics(unemploymentRate=5.0)
    deltas = make_sector_deltas(transport_logistics=20.0, informal=-10.0)
    groups = score_groups(deltas, metrics)
    farmers = next(g for g in groups if g.name == "farmers")
    assert farmers.purchasing_power < 0


def test_it_sector_benefits_from_boom():
    metrics = make_metrics(unemploymentRate=-2.0)
    deltas = make_sector_deltas(it_ites=30.0, real_estate=15.0)
    groups = score_groups(deltas, metrics)
    students = next(g for g in groups if g.name == "students")
    assert students.purchasing_power > 0


def test_classify_severity():
    assert classify_severity(-20.0, 10.0) == "high"
    assert classify_severity(-8.0, 3.0) == "moderate"
    assert classify_severity(-2.0, 1.0) == "low"
    assert classify_severity(5.0, -1.0) == "low"


def test_citizen_satisfaction_bounded():
    metrics = make_metrics()
    deltas = make_sector_deltas(informal=-50.0, transport_logistics=-50.0)
    groups = score_groups(deltas, metrics)
    score = compute_satisfaction(groups)
    assert 0 <= score <= 100
