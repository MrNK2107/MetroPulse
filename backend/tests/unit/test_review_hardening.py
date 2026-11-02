"""Rate-limit keying behind Fly, health-path exemptions, JSON request logs, and
redaction of the agent token / search text from uvicorn's logs."""
from __future__ import annotations

import io
import json
import logging

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app import logging_setup
from app.middleware import HEALTH_PATHS, RateLimitMiddleware, RequestLoggingMiddleware, client_ip
from tests.route_walk import route_paths


# ── rate limit key ──────────────────────────────────────────────────────


def _limited_app(limit: int) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limit=limit)

    @app.get("/x")
    async def x():
        return {"ok": True}

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    return app


def test_rate_limit_keys_on_fly_client_ip():
    client = TestClient(_limited_app(limit=1))
    # Same socket peer (testclient), two different real clients behind Fly's proxy.
    assert client.get("/x", headers={"Fly-Client-IP": "203.0.113.1"}).status_code == 200
    assert client.get("/x", headers={"Fly-Client-IP": "203.0.113.2"}).status_code == 200
    assert client.get("/x", headers={"Fly-Client-IP": "203.0.113.1"}).status_code == 429


def test_rate_limit_falls_back_to_socket_peer():
    client = TestClient(_limited_app(limit=1))
    assert client.get("/x").status_code == 200
    assert client.get("/x").status_code == 429


def test_health_check_is_exempt_from_rate_limit():
    client = TestClient(_limited_app(limit=1))
    for _ in range(3):
        assert client.get("/api/health").status_code == 200


def test_client_ip_helper():
    from starlette.requests import Request

    def req(headers, client=("10.0.0.9", 1234)):
        return Request({"type": "http", "headers": headers, "client": client})

    assert client_ip(req([(b"fly-client-ip", b"198.51.100.7")])) == "198.51.100.7"
    assert client_ip(req([])) == "10.0.0.9"
    assert client_ip(req([(b"fly-client-ip", b"  ")])) == "10.0.0.9"
    assert client_ip(req([], client=None)) == "unknown"


def test_health_paths_are_real_routes():
    from app.main import app

    served = route_paths(app)
    assert HEALTH_PATHS <= served, HEALTH_PATHS - served
    assert {p for p in served if p.startswith("/api/health")} <= HEALTH_PATHS
    assert "/health" not in HEALTH_PATHS


# ── JSON request logs ───────────────────────────────────────────────────


@pytest.fixture
def restore_app_logger():
    log = logging.getLogger("app")
    saved = (log.level, list(log.handlers), log.propagate)
    yield
    log.setLevel(saved[0])
    log.handlers[:] = saved[1]
    log.propagate = saved[2]


def test_request_log_is_printed_as_json(restore_app_logger):
    buf = io.StringIO()
    logging_setup.configure_app_logging("INFO", stream=buf)

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/api/regions")
    async def regions():
        return []

    TestClient(app).get("/api/regions")
    lines = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
    entries = [e for e in lines if e.get("path") == "/api/regions"]
    assert entries, buf.getvalue()
    entry = entries[0]
    assert entry["level"] == "INFO"
    assert entry["logger"] == "app.main"
    assert entry["method"] == "GET" and entry["status"] == 200
    assert "response_time_ms" in entry and "ts" in entry


def test_app_logging_honours_level_and_is_idempotent(restore_app_logger):
    buf = io.StringIO()
    logging_setup.configure_app_logging("WARNING", stream=buf)
    logging_setup.configure_app_logging("WARNING", stream=buf)
    log = logging.getLogger("app.something")
    log.info("hidden")
    log.warning("shown %s", 1)
    lines = [json.loads(line) for line in buf.getvalue().splitlines()]
    assert [line["message"] for line in lines] == ["shown 1"]


def test_main_configures_app_logger_from_settings():
    import app.main  # noqa: F401  (import configures logging)
    from app.config import settings

    log = logging.getLogger("app")
    assert log.level == logging.getLevelName(settings.log_level.upper())
    assert any(isinstance(h.formatter, logging_setup.JsonFormatter) for h in log.handlers)


# ── uvicorn log redaction ───────────────────────────────────────────────


def _capture(logger_name: str, msg: str, *args) -> str:
    log = logging.getLogger(logger_name)
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    log.addHandler(handler)
    try:
        log.warning(msg, *args)
    finally:
        log.removeHandler(handler)
    return buf.getvalue()


def test_error_log_redacts_ws_token():
    logging_setup.install_uvicorn_redaction()
    out = _capture("uvicorn.error", '%s - "WebSocket %s" [accepted]', "1.2.3.4:5", "/ws/agent?token=s3cret&x=1")
    assert "s3cret" not in out
    assert "token=[REDACTED]" in out and "x=1" in out


def test_access_log_redacts_token_and_query_text():
    logging_setup.install_uvicorn_redaction()
    out = _capture(
        "uvicorn.access", '%s - "%s %s HTTP/%s" %d',
        "1.2.3.4:5", "GET", "/api/twin/places/resolve?q=my+house&limit=5&token=abc", "1.1", 200,
    )
    assert "my+house" not in out and "abc" not in out
    assert "q=[REDACTED]" in out and "limit=5" in out and "token=[REDACTED]" in out


def test_access_log_args_keep_their_shape():
    # uvicorn's AccessFormatter unpacks exactly five args; redaction must not change that.
    logging_setup.install_uvicorn_redaction()
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4:5", "GET", "/ws/agent?token=abc", "1.1", 101), None,
    )
    for f in logging.getLogger("uvicorn.access").filters:
        f.filter(record)
    assert len(record.args) == 5 and record.args[4] == 101
    assert record.args[2] == "/ws/agent?token=[REDACTED]"


def test_error_log_keeps_other_q_params():
    # q= is only scrubbed on the access log; the error log only drops tokens.
    logging_setup.install_uvicorn_redaction()
    out = _capture("uvicorn.error", "path %s", "/x?q=keep")
    assert "q=keep" in out


def test_redaction_installed_once():
    logging_setup.install_uvicorn_redaction()
    logging_setup.install_uvicorn_redaction()
    for name in ("uvicorn.error", "uvicorn.access"):
        filters = [f for f in logging.getLogger(name).filters if isinstance(f, logging_setup.RedactingFilter)]
        assert len(filters) == 1
