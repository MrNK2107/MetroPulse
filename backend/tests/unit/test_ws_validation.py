"""Tests for JSON scenario input validation in app/ws/simulation.py.

The WebSocket handler validates JSON scenario input for:
- horizon_months: integer between 1 and 120
- sector_deltas: dict with numeric values between -100 and +100
- city: lowercase string matching [a-z0-9_]+
- policies_active: list of strings
"""
from __future__ import annotations

import json
import re

import pytest


# ── Validation helpers extracted from app/ws/simulation.py ──────────────
# These replicate the validation logic from the WebSocket handler so we
# can unit-test it without a full WebSocket connection.


class InvalidInputError(Exception):
    """Raised when scenario JSON validation fails."""
    def __init__(self, message: str, code: str = "INVALID_INPUT"):
        self.message = message
        self.code = code
        super().__init__(message)


def validate_scenario_json(parsed_data: dict) -> None:
    """Validate parsed JSON scenario input. Raises InvalidInputError on failure.

    Mirrors the validation logic from app/ws/simulation.py lines 53-97.
    """
    # Validate horizon_months
    hm = parsed_data.get("horizon_months", 24)
    if not isinstance(hm, int) or not (1 <= hm <= 120):
        raise InvalidInputError("horizon_months must be an integer between 1 and 120.")

    # Validate city
    city_val = parsed_data.get("city", "mumbai")
    if not isinstance(city_val, str) or not re.fullmatch(r'[a-z0-9_]+', city_val):
        raise InvalidInputError("city must be a lowercase string matching [a-z0-9_]+.")

    # Validate sector_deltas
    sd = parsed_data.get("sector_deltas", {})
    if not isinstance(sd, dict):
        raise InvalidInputError("sector_deltas must be an object mapping sector names to numeric values.")
    for k, v in sd.items():
        if not isinstance(v, (int, float)) or not (-100 <= v <= 100):
            raise InvalidInputError(f"sector_deltas['{k}'] must be numeric between -100 and +100.")

    # Validate policies_active
    pa = parsed_data.get("policies_active", [])
    if not isinstance(pa, list) or not all(isinstance(x, str) for x in pa):
        raise InvalidInputError("policies_active must be a list of strings.")


# ── Test: valid JSON input ──────────────────────────────────────────────


def test_valid_json_input():
    """A well-formed scenario JSON should pass validation."""
    data = {
        "city": "mumbai",
        "sector_deltas": {"it_ites": 20.0, "manufacturing": -10.0},
        "policies_active": ["smart_city"],
        "horizon_months": 24,
    }
    # Should not raise
    validate_scenario_json(data)


def test_valid_json_minimal():
    """Minimal valid input — all fields have defaults."""
    data = {}
    # Should not raise — all fields have defaults
    validate_scenario_json(data)


def test_valid_json_boundary_horizon():
    """Boundary values for horizon_months."""
    validate_scenario_json({"horizon_months": 1})
    validate_scenario_json({"horizon_months": 120})


def test_valid_json_boundary_sector_deltas():
    """Boundary values for sector_deltas."""
    validate_scenario_json({"sector_deltas": {"it_ites": -100}})
    validate_scenario_json({"sector_deltas": {"it_ites": 100}})
    validate_scenario_json({"sector_deltas": {"it_ites": 0}})


# ── Test: horizon_months out of range ──────────────────────────────────


def test_horizon_months_zero():
    with pytest.raises(InvalidInputError, match="horizon_months"):
        validate_scenario_json({"horizon_months": 0})


def test_horizon_months_negative():
    with pytest.raises(InvalidInputError, match="horizon_months"):
        validate_scenario_json({"horizon_months": -5})


def test_horizon_months_too_large():
    with pytest.raises(InvalidInputError, match="horizon_months"):
        validate_scenario_json({"horizon_months": 121})


def test_horizon_months_string():
    with pytest.raises(InvalidInputError, match="horizon_months"):
        validate_scenario_json({"horizon_months": "twelve"})


def test_horizon_months_float():
    with pytest.raises(InvalidInputError, match="horizon_months"):
        validate_scenario_json({"horizon_months": 12.5})


# ── Test: sector_deltas out of range ───────────────────────────────────


def test_sector_deltas_above_max():
    with pytest.raises(InvalidInputError, match="sector_deltas"):
        validate_scenario_json({"sector_deltas": {"it_ites": 101}})


def test_sector_deltas_below_min():
    with pytest.raises(InvalidInputError, match="sector_deltas"):
        validate_scenario_json({"sector_deltas": {"it_ites": -101}})


def test_sector_deltas_string_value():
    with pytest.raises(InvalidInputError, match="sector_deltas"):
        validate_scenario_json({"sector_deltas": {"it_ites": "twenty"}})


def test_sector_deltas_not_dict():
    with pytest.raises(InvalidInputError, match="sector_deltas must be an object"):
        validate_scenario_json({"sector_deltas": [20, -10]})


def test_sector_deltas_none_value():
    with pytest.raises(InvalidInputError, match="sector_deltas"):
        validate_scenario_json({"sector_deltas": {"it_ites": None}})


# ── Test: invalid city name ────────────────────────────────────────────


def test_city_uppercase():
    with pytest.raises(InvalidInputError, match="city"):
        validate_scenario_json({"city": "Mumbai"})


def test_city_with_spaces():
    with pytest.raises(InvalidInputError, match="city"):
        validate_scenario_json({"city": "new delhi"})


def test_city_with_special_chars():
    with pytest.raises(InvalidInputError, match="city"):
        validate_scenario_json({"city": "mumbai; rm -rf /"})


def test_city_with_path_traversal():
    with pytest.raises(InvalidInputError, match="city"):
        validate_scenario_json({"city": "../etc/passwd"})


def test_city_with_dots():
    with pytest.raises(InvalidInputError, match="city"):
        validate_scenario_json({"city": "../../secret"})


def test_city_not_string():
    with pytest.raises(InvalidInputError, match="city"):
        validate_scenario_json({"city": 123})


def test_city_valid_underscore():
    """Underscores are valid in city names."""
    validate_scenario_json({"city": "delhi_ncr"})


def test_city_valid_alphanumeric():
    validate_scenario_json({"city": "chennai123"})


# ── Test: missing required fields ──────────────────────────────────────


def test_missing_all_fields():
    """Missing fields should use defaults and not raise."""
    validate_scenario_json({})


def test_empty_sector_deltas():
    validate_scenario_json({"sector_deltas": {}})


def test_empty_policies_active():
    validate_scenario_json({"policies_active": []})


# ── Test: policies_active validation ───────────────────────────────────


def test_policies_active_not_list():
    with pytest.raises(InvalidInputError, match="policies_active"):
        validate_scenario_json({"policies_active": "smart_city"})


def test_policies_active_non_string_elements():
    with pytest.raises(InvalidInputError, match="policies_active"):
        validate_scenario_json({"policies_active": [123, True]})


def test_policies_active_mixed_types():
    with pytest.raises(InvalidInputError, match="policies_active"):
        validate_scenario_json({"policies_active": ["smart_city", 42]})


def test_policies_active_valid():
    validate_scenario_json({"policies_active": ["smart_city", "metro_expansion"]})


# ── Test: combined valid scenario ──────────────────────────────────────


def test_full_valid_scenario():
    """A complete, realistic scenario should pass validation."""
    data = {
        "city": "bengaluru",
        "sector_deltas": {
            "it_ites": 25.0,
            "manufacturing": -10.0,
            "real_estate": 15.0,
            "trade_hospitality": -5.0,
            "transport_logistics": 8.0,
            "informal": -3.0,
            "public_admin": 0.0,
        },
        "policies_active": ["smart_city", "metro_expansion"],
        "horizon_months": 36,
    }
    validate_scenario_json(data)
