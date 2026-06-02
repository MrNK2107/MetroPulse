"""Tests for CORS and Settings validation in app/config.py.

Tests cover: wildcard CORS warning in production, invalid URL format warning,
valid origins acceptance, and localhost acceptance in dev mode.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from app.config import Settings, _validate_settings, _url_pattern


# ── Helper to build Settings with overrides ─────────────────────────────


def _make_settings(**overrides) -> Settings:
    """Create a Settings instance using env aliases."""
    # Settings uses alias-based construction (CORS_ORIGINS, ENVIRONMENT, etc.)
    env_map = {
        "cors_origins": "CORS_ORIGINS",
        "environment": "ENVIRONMENT",
    }
    kwargs = {
        env_map.get(k, k): v
        for k, v in overrides.items()
    }
    defaults = {
        "CORS_ORIGINS": "http://localhost:3000",
        "ENVIRONMENT": "development",
    }
    defaults.update(kwargs)
    return Settings(**defaults)


# ── Wildcard CORS in production ─────────────────────────────────────────


def test_warns_on_wildcard_cors_in_production(caplog):
    """Using '*' in CORS_ORIGINS in production should emit a warning."""
    s = _make_settings(cors_origins="*", environment="production")
    with caplog.at_level(logging.WARNING):
        result = _validate_settings(s)
    assert any("*" in record.message for record in caplog.records)
    assert result is s  # should pass through


def test_warns_on_wildcard_cors_in_staging(caplog):
    """Using '*' in CORS_ORIGINS in staging should also warn."""
    s = _make_settings(cors_origins="*", environment="staging")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    assert any("*" in record.message for record in caplog.records)


def test_no_warning_on_wildcard_cors_in_development(caplog):
    """Using '*' in development should NOT warn."""
    s = _make_settings(cors_origins="*", environment="development")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    wildcard_warnings = [r for r in caplog.records if "*" in r.message and "CORS" in r.message]
    assert len(wildcard_warnings) == 0


def test_no_warning_on_wildcard_cors_in_dev(caplog):
    """Using '*' in 'dev' environment should NOT warn."""
    s = _make_settings(cors_origins="*", environment="dev")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    wildcard_warnings = [r for r in caplog.records if "*" in r.message and "CORS" in r.message]
    assert len(wildcard_warnings) == 0


def test_no_warning_on_wildcard_cors_in_local(caplog):
    """Using '*' in 'local' environment should NOT warn."""
    s = _make_settings(cors_origins="*", environment="local")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    wildcard_warnings = [r for r in caplog.records if "*" in r.message and "CORS" in r.message]
    assert len(wildcard_warnings) == 0


# ── Invalid URL format ──────────────────────────────────────────────────


def test_warns_on_invalid_url_format(caplog):
    """A non-URL string in CORS_ORIGINS should emit a warning."""
    s = _make_settings(cors_origins="not-a-valid-url", environment="production")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    assert any("invalid url" in record.message.lower() for record in caplog.records)


def test_warns_on_bare_hostname(caplog):
    """A bare hostname like 'example.com' should warn (missing scheme)."""
    s = _make_settings(cors_origins="example.com", environment="production")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    assert any("invalid url" in record.message.lower() for record in caplog.records)


# ── Valid origins ───────────────────────────────────────────────────────


def test_accepts_valid_https_origin(caplog):
    """A valid https:// origin should not warn."""
    s = _make_settings(cors_origins="https://app.metropulse.in", environment="production")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    url_warnings = [r for r in caplog.records if "invalid url" in r.message.lower()]
    assert len(url_warnings) == 0


def test_accepts_valid_http_origin_with_port(caplog):
    """A valid http://host:port origin should not warn."""
    s = _make_settings(cors_origins="http://localhost:3000", environment="development")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    url_warnings = [r for r in caplog.records if "invalid url" in r.message.lower()]
    assert len(url_warnings) == 0


def test_accepts_multiple_valid_origins(caplog):
    """Comma-separated valid origins should not warn."""
    s = _make_settings(
        cors_origins="https://app.metropulse.in,http://localhost:3000",
        environment="production",
    )
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    url_warnings = [r for r in caplog.records if "invalid url" in r.message.lower()]
    assert len(url_warnings) == 0


# ── Localhost in dev mode ──────────────────────────────────────────────


def test_accepts_localhost_in_dev_mode(caplog):
    """Localhost origins in development mode should not warn."""
    s = _make_settings(cors_origins="http://localhost:3000", environment="development")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    assert len(caplog.records) == 0


def test_accepts_localhost_with_different_port(caplog):
    """Localhost on any port should be accepted without warning."""
    s = _make_settings(cors_origins="http://localhost:8080", environment="development")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    assert len(caplog.records) == 0


def test_accepts_127_0_0_1_in_dev_mode(caplog):
    """127.0.0.1 origins in development should not warn."""
    s = _make_settings(cors_origins="http://127.0.0.1:3000", environment="development")
    with caplog.at_level(logging.WARNING):
        _validate_settings(s)
    assert len(caplog.records) == 0


# ── URL pattern regex ──────────────────────────────────────────────────


def test_url_pattern_accepts_http():
    assert _url_pattern.match("http://localhost:3000") is not None


def test_url_pattern_accepts_https():
    assert _url_pattern.match("https://example.com") is not None


def test_url_pattern_rejects_bare():
    assert _url_pattern.match("example.com") is None


def test_url_pattern_rejects_empty():
    assert _url_pattern.match("") is None


# ── Settings property tests ────────────────────────────────────────────


def test_cors_origin_list_splits_commas():
    s = _make_settings(cors_origins="http://a.com,http://b.com")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_cors_origin_list_strips_whitespace():
    s = _make_settings(cors_origins="http://a.com , http://b.com")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_cors_origin_list_single():
    s = _make_settings(cors_origins="http://localhost:3000")
    assert s.cors_origin_list == ["http://localhost:3000"]
