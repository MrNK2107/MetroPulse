"""Tests for RequestLoggingMiddleware in app/main.py.

Tests cover: logging request method/path/status/time, skipping health checks,
and graceful exception handling.
"""
from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.main import app
from app.middleware import CorrelationIdMiddleware, RateLimitMiddleware, RequestLoggingMiddleware


def _make_starlette_request(method: str = "GET", path: str = "/api/regions") -> Request:
    """Create a minimal Starlette Request for middleware testing."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
    }
    return Request(scope)


async def _run_middleware(request: Request, response_status: int = 200) -> Response:
    """Run the middleware with a mock call_next that returns the given status."""
    middleware = RequestLoggingMiddleware(app=MagicMock())

    mock_response = Response(content="ok", status_code=response_status)
    call_next = AsyncMock(return_value=mock_response)

    return await middleware.dispatch(request, call_next)


# ── Logs request method, path, status, time ─────────────────────────────


@pytest.mark.asyncio
async def test_logs_request_method_path_status(caplog):
    """Non-health requests should be logged with method, path, and status."""
    request = _make_starlette_request("GET", "/api/regions")

    with caplog.at_level(logging.INFO):
        response = await _run_middleware(request, response_status=200)

    # Should have logged a JSON entry
    json_logs = []
    for record in caplog.records:
        try:
            json_logs.append(json.loads(record.message))
        except (json.JSONDecodeError, TypeError):
            pass

    assert len(json_logs) >= 1, f"Expected JSON log, got: {[r.message for r in caplog.records]}"
    log = json_logs[0]
    assert log["method"] == "GET"
    assert log["path"] == "/api/regions"
    assert log["status"] == 200
    assert "response_time_ms" in log
    assert isinstance(log["response_time_ms"], (int, float))


@pytest.mark.asyncio
async def test_logs_post_request(caplog):
    """POST requests should also be logged."""
    request = _make_starlette_request("POST", "/api/ingest")

    with caplog.at_level(logging.INFO):
        await _run_middleware(request, response_status=200)

    json_logs = [json.loads(r.message) for r in caplog.records if r.message.startswith("{")]
    assert any(log["method"] == "POST" for log in json_logs)


# ── Skips health check logging ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_health_endpoint_logging(caplog):
    """/api/health should not be logged."""
    request = _make_starlette_request("GET", "/api/health")

    with caplog.at_level(logging.INFO):
        await _run_middleware(request, response_status=200)

    json_logs = [r for r in caplog.records if r.message.startswith("{")]
    assert len(json_logs) == 0, "Health endpoint should not be logged"


@pytest.mark.asyncio
async def test_skips_health_data_endpoint_logging(caplog):
    """/api/health/data should not be logged."""
    request = _make_starlette_request("GET", "/api/health/data")

    with caplog.at_level(logging.INFO):
        await _run_middleware(request, response_status=200)

    json_logs = [r for r in caplog.records if r.message.startswith("{")]
    assert len(json_logs) == 0


@pytest.mark.asyncio
async def test_skips_root_health_endpoint_logging(caplog):
    """/health should not be logged."""
    request = _make_starlette_request("GET", "/health")

    with caplog.at_level(logging.INFO):
        await _run_middleware(request, response_status=200)

    json_logs = [r for r in caplog.records if r.message.startswith("{")]
    assert len(json_logs) == 0


@pytest.mark.asyncio
async def test_does_log_non_health_endpoints(caplog):
    """Non-health endpoints should still be logged."""
    request = _make_starlette_request("GET", "/api/regions")

    with caplog.at_level(logging.INFO):
        await _run_middleware(request, response_status=200)

    json_logs = [r for r in caplog.records if r.message.startswith("{")]
    assert len(json_logs) >= 1


# ── Handles exceptions gracefully ──────────────────────────────────────


@pytest.mark.asyncio
async def test_handles_call_next_exception():
    """If call_next raises, the middleware should propagate the exception."""
    request = _make_starlette_request("GET", "/api/error")

    middleware = RequestLoggingMiddleware(app=MagicMock())
    call_next = AsyncMock(side_effect=RuntimeError("Internal error"))

    with pytest.raises(RuntimeError, match="Internal error"):
        await middleware.dispatch(request, call_next)


@pytest.mark.asyncio
async def test_response_time_is_positive():
    """Response time should be a non-negative number."""
    request = _make_starlette_request("GET", "/api/twin/places")

    with patch("app.middleware.logger") as mock_logger:
        await _run_middleware(request, response_status=200)

        # Find the info call
        info_calls = [c for c in mock_logger.info.call_args_list]
        assert len(info_calls) >= 1
        log_data = json.loads(info_calls[0][0][0])
        assert log_data["response_time_ms"] >= 0


# ── CorrelationIdMiddleware tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_correlation_id_header_present():
    """Every response should have an X-Request-ID header."""
    request = _make_starlette_request("GET", "/api/regions")

    middleware = CorrelationIdMiddleware(app=MagicMock())
    mock_response = Response(content="ok", status_code=200)
    call_next = AsyncMock(return_value=mock_response)

    response = await middleware.dispatch(request, call_next)
    assert "X-Request-ID" in response.headers
    # Should be a valid UUID
    import uuid
    uuid.UUID(response.headers["X-Request-ID"])


@pytest.mark.asyncio
async def test_correlation_id_passthrough():
    """If the client sends X-Request-ID, it should be echoed back."""
    client_request_id = "my-custom-trace-id-123"
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/regions",
        "query_string": b"",
        "headers": [(b"x-request-id", client_request_id.encode())],
        "server": ("testserver", 80),
    }
    request = Request(scope)

    middleware = CorrelationIdMiddleware(app=MagicMock())
    mock_response = Response(content="ok", status_code=200)
    call_next = AsyncMock(return_value=mock_response)

    response = await middleware.dispatch(request, call_next)
    assert response.headers["X-Request-ID"] == client_request_id


@pytest.mark.asyncio
async def test_correlation_id_stashed_on_request_state():
    """The middleware should stash the request_id on request.state."""
    request = _make_starlette_request("GET", "/api/regions")

    middleware = CorrelationIdMiddleware(app=MagicMock())
    mock_response = Response(content="ok", status_code=200)
    call_next = AsyncMock(return_value=mock_response)

    response = await middleware.dispatch(request, call_next)
    assert hasattr(request.state, "request_id")
    assert request.state.request_id == response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_request_logging_includes_correlation_id(caplog):
    """The JSON log entry should include request_id when correlation middleware runs."""
    request = _make_starlette_request("GET", "/api/regions")
    # Simulate what CorrelationIdMiddleware would do
    request.state.request_id = "test-req-id-abc"
    with caplog.at_level(logging.INFO):
        response = await _run_middleware(request, response_status=200)
    json_logs = []
    for record in caplog.records:
        try:
            json_logs.append(json.loads(record.message))
        except (json.JSONDecodeError, TypeError):
            pass

    assert len(json_logs) >= 1
    assert json_logs[0].get("request_id") == "test-req-id-abc"


@pytest.mark.asyncio
async def test_correlation_id_rejects_malformed_client_value():
    """A client X-Request-ID with spaces or control characters is replaced by a UUID."""
    scope = {
        "type": "http", "method": "GET", "path": "/api/regions", "query_string": b"",
        "headers": [(b"x-request-id", b"bad id; drop table")], "server": ("testserver", 80),
    }
    middleware = CorrelationIdMiddleware(app=MagicMock())
    response = await middleware.dispatch(Request(scope), AsyncMock(return_value=Response("ok")))
    import uuid
    uuid.UUID(response.headers["X-Request-ID"])


def _req_from(ip: str, path: str = "/api/regions") -> Request:
    return Request({
        "type": "http", "method": "GET", "path": path, "query_string": b"",
        "headers": [], "server": ("testserver", 80), "client": (ip, 1234),
    })


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_limit_per_ip():
    middleware = RateLimitMiddleware(app=MagicMock(), limit=3)
    call_next = AsyncMock(return_value=Response("ok"))
    for _ in range(3):
        assert (await middleware.dispatch(_req_from("10.0.0.1"), call_next)).status_code == 200
    blocked = await middleware.dispatch(_req_from("10.0.0.1"), call_next)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    # Another IP is unaffected; health checks are exempt.
    assert (await middleware.dispatch(_req_from("10.0.0.2"), call_next)).status_code == 200
    assert (await middleware.dispatch(_req_from("10.0.0.1", "/api/health"), call_next)).status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_zero_disables():
    middleware = RateLimitMiddleware(app=MagicMock(), limit=0)
    call_next = AsyncMock(return_value=Response("ok"))
    for _ in range(50):
        assert (await middleware.dispatch(_req_from("10.0.0.3"), call_next)).status_code == 200


@pytest.mark.asyncio
async def test_app_responses_carry_request_id():
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health", headers={"X-Request-ID": "desk-trace-1"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "desk-trace-1"
