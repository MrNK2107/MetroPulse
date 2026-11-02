"""Checks on the deploy files: the Dockerfile CMD must be a command uvicorn accepts,
and fly.toml must health-check a route that exists."""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

import click
import pytest
from uvicorn.main import main as uvicorn_cli

BACKEND = Path(__file__).resolve().parents[2]


def _dockerfile_cmd() -> list[str]:
    lines = (BACKEND / "Dockerfile").read_text(encoding="utf-8").splitlines()
    cmd_lines = [ln for ln in lines if ln.startswith("CMD ")]
    assert len(cmd_lines) == 1, "expected exactly one exec-form CMD"
    return json.loads(cmd_lines[0][len("CMD "):])


def test_dockerfile_cmd_parses_as_uvicorn_arguments():
    cmd = _dockerfile_cmd()
    assert cmd[0] == "uvicorn"
    # make_context parses the options without starting a server; a bad option
    # (e.g. a bare --ws-per-message-deflate, which needs a value) raises here,
    # where the real container would exit with status 2.
    try:
        ctx = uvicorn_cli.make_context("uvicorn", cmd[1:])
    except click.ClickException as exc:  # pragma: no cover - failure path
        pytest.fail(f"uvicorn rejects the Dockerfile CMD: {exc.format_message()}")
    assert ctx.params["app"] == "app.main:app"
    assert ctx.params["port"] == 8000


def test_dockerfile_trusts_fly_proxy_headers():
    cmd = _dockerfile_cmd()
    ctx = uvicorn_cli.make_context("uvicorn", cmd[1:])
    assert ctx.params["proxy_headers"] is True
    assert ctx.params["forwarded_allow_ips"] == "*"
    text = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    assert "Fly" in text.split("CMD ")[0], "the wildcard trust needs a comment explaining it is Fly-only"


def test_bare_deflate_flag_is_rejected_by_uvicorn():
    # Documents why the flag was removed: it takes a boolean value.
    with pytest.raises(click.UsageError):
        uvicorn_cli.make_context("uvicorn", ["app.main:app", "--ws-per-message-deflate"])


def test_fly_health_check_targets_a_real_route():
    from app.main import app

    fly = tomllib.loads((BACKEND / "fly.toml").read_text(encoding="utf-8"))
    checks = fly["http_service"]["checks"]
    assert checks, "fly.toml needs an [[http_service.checks]] entry"
    from tests.route_walk import route_paths

    paths = route_paths(app)
    for check in checks:
        assert check["path"] == "/api/health"
        assert check["path"] in paths
        assert check.get("method", "GET").upper() == "GET"


def test_fastapi_pin_matches_between_pyproject_and_requirements():
    import re

    req = (BACKEND / "requirements.txt").read_text(encoding="utf-8")
    req_pin = re.search(r"^fastapi([^\s#]*)", req, re.M).group(1)
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    py_pin = next(d[len("fastapi"):] for d in project["dependencies"] if d.startswith("fastapi"))
    assert req_pin == py_pin
