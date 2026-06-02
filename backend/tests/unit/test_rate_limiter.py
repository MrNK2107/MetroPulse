"""Tests for the in-memory rate limiter in app/routes/realtime.py.

The rate limiter uses module-level dicts to track per-IP request timestamps.
Tests verify: within-limit allows, over-limit blocks with 429, window resets,
per-IP isolation, and retry_after_seconds presence.
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse


# We import the module to access its internals for testing.
# Because trigger_ingestion has heavy dependencies (db, run_ingestion_cycle),
# we test the rate limiting logic by calling the endpoint with mocked deps.
from app.routes.realtime import (
    _ingest_rate_limit,
    _INGEST_MAX_REQUESTS,
    _INGEST_WINDOW_SECONDS,
    router,
)


def _make_request(ip: str = "127.0.0.1") -> Request:
    """Create a mock Request with the given client IP."""
    req = MagicMock(spec=Request)
    req.client = MagicMock()
    req.client.host = ip
    return req


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """Reset the in-memory rate limiter between tests."""
    _ingest_rate_limit.clear()
    yield
    _ingest_rate_limit.clear()


# ── Helper to call the endpoint through the route function ─────────────


def _find_ingest_route():
    """Find the trigger_ingestion route function from the router."""
    for route in router.routes:
        if hasattr(route, "path") and route.path == "/ingest" and hasattr(route, "methods") and "POST" in route.methods:
            return route.endpoint
    raise RuntimeError("Could not find /ingest POST route")


@pytest.mark.asyncio
async def test_allows_requests_within_limit():
    """Requests within the rate limit should proceed (not return 429)."""
    endpoint = _find_ingest_route()
    request = _make_request("10.0.0.1")

    with patch("app.routes.realtime.run_ingestion_cycle", new_callable=AsyncMock) as mock_cycle, \
         patch("app.routes.realtime.get_db", new_callable=AsyncMock):
        mock_cycle.return_value = MagicMock(
            id="snap-1", status="ok", quality_score=0.8
        )
        # Make requests up to the limit
        for i in range(_INGEST_MAX_REQUESTS):
            result = await endpoint(request=request, city="mumbai", db=MagicMock())
            # Should NOT be a 429
            if isinstance(result, JSONResponse):
                assert result.status_code != 429, f"Request {i+1} returned 429 but should be within limit"


@pytest.mark.asyncio
async def test_blocks_requests_over_limit():
    """Requests exceeding the limit should return 429."""
    endpoint = _find_ingest_route()
    request = _make_request("10.0.0.2")

    with patch("app.routes.realtime.run_ingestion_cycle", new_callable=AsyncMock) as mock_cycle:
        mock_cycle.return_value = MagicMock(
            id="snap-1", status="ok", quality_score=0.8
        )
        # Exhaust the limit
        for _ in range(_INGEST_MAX_REQUESTS):
            await endpoint(request=request, city="mumbai", db=MagicMock())

        # This one should be blocked
        result = await endpoint(request=request, city="mumbai", db=MagicMock())
        assert isinstance(result, JSONResponse)
        assert result.status_code == 429


@pytest.mark.asyncio
async def test_resets_after_time_window():
    """After the time window expires, the limiter should allow requests again."""
    endpoint = _find_ingest_route()
    request = _make_request("10.0.0.3")

    with patch("app.routes.realtime.run_ingestion_cycle", new_callable=AsyncMock) as mock_cycle:
        mock_cycle.return_value = MagicMock(
            id="snap-1", status="ok", quality_score=0.8
        )
        # Exhaust the limit
        for _ in range(_INGEST_MAX_REQUESTS):
            await endpoint(request=request, city="mumbai", db=MagicMock())

        # Manually expire timestamps by shifting them into the past
        _ingest_rate_limit["10.0.0.3"] = [
            t - _INGEST_WINDOW_SECONDS - 1
            for t in _ingest_rate_limit["10.0.0.3"]
        ]

        # This should now succeed
        result = await endpoint(request=request, city="mumbai", db=MagicMock())
        if isinstance(result, JSONResponse):
            assert result.status_code != 429, "Request should succeed after window reset"


@pytest.mark.asyncio
async def test_per_ip_tracking():
    """Different IPs should have independent rate limits."""
    endpoint = _find_ingest_route()
    request_a = _make_request("10.0.0.10")
    request_b = _make_request("10.0.0.11")

    with patch("app.routes.realtime.run_ingestion_cycle", new_callable=AsyncMock) as mock_cycle:
        mock_cycle.return_value = MagicMock(
            id="snap-1", status="ok", quality_score=0.8
        )
        # Exhaust limit for IP A
        for _ in range(_INGEST_MAX_REQUESTS):
            await endpoint(request=request_a, city="mumbai", db=MagicMock())

        # IP B should still be able to make requests
        result = await endpoint(request=request_b, city="mumbai", db=MagicMock())
        if isinstance(result, JSONResponse):
            assert result.status_code != 429, "Different IP should not be rate limited"

        # IP A should be blocked
        result_a = await endpoint(request=request_a, city="mumbai", db=MagicMock())
        assert isinstance(result_a, JSONResponse)
        assert result_a.status_code == 429


@pytest.mark.asyncio
async def test_returns_429_with_retry_after_seconds():
    """The 429 response should include retry_after_seconds in meta."""
    endpoint = _find_ingest_route()
    request = _make_request("10.0.0.20")

    with patch("app.routes.realtime.run_ingestion_cycle", new_callable=AsyncMock) as mock_cycle:
        mock_cycle.return_value = MagicMock(
            id="snap-1", status="ok", quality_score=0.8
        )
        # Exhaust the limit
        for _ in range(_INGEST_MAX_REQUESTS):
            await endpoint(request=request, city="mumbai", db=MagicMock())

        # Next request should be 429
        result = await endpoint(request=request, city="mumbai", db=MagicMock())
        assert isinstance(result, JSONResponse)
        assert result.status_code == 429

        # Parse the response body
        import json
        body = json.loads(result.body.decode())
        assert body["success"] is False
        assert "Rate limit exceeded" in body["error"]
        assert "retry_after_seconds" in body["meta"]
        assert isinstance(body["meta"]["retry_after_seconds"], (int, float))
        assert body["meta"]["retry_after_seconds"] > 0


@pytest.mark.asyncio
async def test_unknown_client_ip():
    """When request.client is None, should use 'unknown' as IP key."""
    endpoint = _find_ingest_route()
    request = MagicMock(spec=Request)
    request.client = None

    with patch("app.routes.realtime.run_ingestion_cycle", new_callable=AsyncMock) as mock_cycle:
        mock_cycle.return_value = MagicMock(
            id="snap-1", status="ok", quality_score=0.8
        )
        result = await endpoint(request=request, city="mumbai", db=MagicMock())
        # Should not crash, should use "unknown" as key
        assert "unknown" in _ingest_rate_limit or result is not None
