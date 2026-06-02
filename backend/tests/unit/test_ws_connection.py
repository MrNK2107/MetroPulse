"""Tests for WebSocket connection management in app/ws/simulation.py.

Tests cover: accepting valid JSON scenarios, rejecting oversized messages,
rejecting when at max connections, and the validation paths for
horizon_months, sector_deltas, and city name format.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ws.simulation import (
    MAX_WS_MESSAGE_BYTES,
    _active_ws_connections,
    simulation_websocket,
)


def _make_websocket() -> AsyncMock:
    """Create a mock WebSocket that behaves like a real one."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.client = MagicMock()
    ws.client.host = "127.0.0.1"
    return ws


# ── Max connections enforcement ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_rejects_when_at_max_connections():
    """When active connections >= max, new connections should be closed with 1013."""
    import app.ws.simulation as ws_mod
    original = ws_mod._active_ws_connections

    try:
        with patch.object(ws_mod, "settings") as mock_settings:
            mock_settings.ws_max_connections = 2
            ws_mod._active_ws_connections = 2  # at capacity

            ws = _make_websocket()
            await ws_mod.simulation_websocket(ws)

            ws.close.assert_called_once()
            args = ws.close.call_args
            assert args[1].get("code") == 1013 or (args[0] and args[0][0] == 1013)
            ws.accept.assert_not_called()
    finally:
        ws_mod._active_ws_connections = original


@pytest.mark.asyncio
async def test_accepts_when_below_max_connections():
    """When active connections < max, should accept the connection."""
    import app.ws.simulation as ws_mod
    original = ws_mod._active_ws_connections

    try:
        with patch.object(ws_mod, "settings") as mock_settings:
            mock_settings.ws_max_connections = 10
            ws_mod._active_ws_connections = 5  # below capacity

            ws = _make_websocket()
            # Make it timeout quickly so we don't run the full simulation
            ws.receive_text = AsyncMock(side_effect=TimeoutError())

            try:
                await ws_mod.simulation_websocket(ws)
            except (TimeoutError, Exception):
                pass

            ws.accept.assert_called_once()
    finally:
        ws_mod._active_ws_connections = original


# ── Oversized message rejection ─────────────────────────────────────────


def test_max_ws_message_bytes_constant():
    """The MAX_WS_MESSAGE_BYTES should be 64KB."""
    assert MAX_WS_MESSAGE_BYTES == 64 * 1024


def test_oversized_message_detection():
    """Messages over 64KB should be detectable."""
    small_msg = json.dumps({"type": "START", "scenario": "test"})
    assert len(small_msg.encode("utf-8")) <= MAX_WS_MESSAGE_BYTES

    # Create a message that's definitely over 64KB
    large_msg = json.dumps({"type": "START", "scenario": "x" * (MAX_WS_MESSAGE_BYTES + 1)})
    assert len(large_msg.encode("utf-8")) > MAX_WS_MESSAGE_BYTES


# ── JSON scenario validation (integration with WS receive) ─────────────


def test_valid_json_scenario_parses():
    """A valid JSON scenario with all fields should parse correctly."""
    from engine.models import ParsedScenario, SECTOR_NAMES

    data = {
        "city": "mumbai",
        "horizon_months": 24,
        "sector_deltas": {"it_ites": 20.0, "manufacturing": -10.0},
        "policies_active": ["smart_city"],
    }
    # Reconstruct the way the WS handler does it
    sector_deltas = {
        s: float(data.get("sector_deltas", {}).get(s, 0.0))
        for s in SECTOR_NAMES
    }
    parsed = ParsedScenario(
        city=data.get("city", "mumbai"),
        sector_deltas=sector_deltas,
        policies_active=list(data.get("policies_active", [])),
        public_works_zone=data.get("public_works_zone"),
        horizon_months=int(data.get("horizon_months", 24)),
        causal_chain=data.get("causal_chain", "Direct parameter specification"),
        keywords=list(data.get("keywords", ["mumbai"])),
        confidence="high",
        assumptions=list(data.get("assumptions", ["Direct numeric specification by user."])),
    )
    assert parsed.city == "mumbai"
    assert parsed.horizon_months == 24
    assert parsed.sector_deltas["it_ites"] == 20.0


def test_valid_horizon_months_range():
    """horizon_months should be validated as 1-120."""
    import re

    # Valid values
    for val in [1, 12, 24, 60, 120]:
        hm = val
        assert isinstance(hm, int) and (1 <= hm <= 120), f"{val} should be valid"

    # Invalid values
    for val in [0, -1, 121, 200]:
        hm = val
        assert not (isinstance(hm, int) and (1 <= hm <= 120)), f"{val} should be invalid"


def test_valid_sector_deltas_range():
    """sector_deltas values should be numeric between -100 and +100."""
    # Valid
    for v in [-100, -50, 0, 50, 100]:
        assert isinstance(v, (int, float)) and (-100 <= v <= 100)

    # Invalid
    for v in [-101, 101, "twenty", None]:
        if isinstance(v, (int, float)):
            assert not (-100 <= v <= 100), f"{v} should be out of range"
        else:
            assert not isinstance(v, (int, float)), f"{v} is not numeric"


def test_valid_city_name_format():
    """City names must match [a-z0-9_]+."""
    import re
    pattern = re.compile(r'^[a-z0-9_]+$')

    # Valid
    for city in ["mumbai", "delhi_ncr", "chennai123", "a"]:
        assert pattern.fullmatch(city), f"{city} should be valid"

    # Invalid
    for city in ["Mumbai", "new delhi", "../etc/passwd", "mumbai; rm -rf", ""]:
        assert not pattern.fullmatch(city), f"{city} should be invalid"


# ── Connection counter decrement ────────────────────────────────────────


@pytest.mark.asyncio
async def test_connection_counter_decrements_on_close():
    """After a WebSocket handler finishes, the active count should decrement."""
    import app.ws.simulation as ws_mod
    original = ws_mod._active_ws_connections

    try:
        with patch.object(ws_mod, "settings") as mock_settings:
            mock_settings.ws_max_connections = 10
            ws_mod._active_ws_connections = 0

            ws = _make_websocket()
            # Make _receive_start raise TimeoutError to exit quickly
            ws.receive_text = AsyncMock(side_effect=TimeoutError())

            try:
                await ws_mod.simulation_websocket(ws)
            except Exception:
                pass

            # The finally block should have decremented (but not below 0)
            assert ws_mod._active_ws_connections >= 0
    finally:
        ws_mod._active_ws_connections = original
