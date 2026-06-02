"""Tests for simulation DELETE, export, and summary endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app


# ── Helpers ──────────────────────────────────────────────────────────────

MOCK_SIMULATION = {
    "id": "00000000-0000-0000-0000-000000000001",
    "region_id": "bengaluru",
    "params": {"city": "bengaluru", "scenario": "IT boom +20%"},
    "horizon_months": 12,
    "result_summary": {
        "verdict": "Positive growth expected",
        "key_metrics": {"gdp_change": 0.15, "unemployment_change": -0.02},
    },
    "cell_states": [
        {
            "month": 1,
            "cells": {
                "8860a2589ffffff": {"gdp": 1.02, "unemployment": 0.048, "realEstateIdx": 1.01, "transitLoad": 0.55},
                "8860a258affffff": {"gdp": 0.98, "unemployment": 0.052, "realEstateIdx": 0.99, "transitLoad": 0.60},
            },
        },
        {
            "month": 2,
            "cells": {
                "8860a2589ffffff": {"gdp": 1.04, "unemployment": 0.046, "realEstateIdx": 1.02, "transitLoad": 0.54},
                "8860a258affffff": {"gdp": 0.97, "unemployment": 0.053, "realEstateIdx": 0.98, "transitLoad": 0.62},
            },
        },
    ],
    "created_at": "2025-01-15T10:00:00Z",
}


def _mock_db(simulation=None, delete_ok=True):
    """Build a mock DatabaseClient that returns the given simulation."""
    db = AsyncMock()
    db.get_simulation = AsyncMock(return_value=simulation)
    db.delete_simulation = AsyncMock(return_value=delete_ok)
    db.list_simulations = AsyncMock(return_value=[])
    return db


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Clear dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()


# ── DELETE endpoint tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_existing_simulation_returns_204():
    """Deleting an existing simulation should return 204 No Content."""
    db = _mock_db(MOCK_SIMULATION)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/simulations/{MOCK_SIMULATION['id']}")

    assert response.status_code == 204
    db.delete_simulation.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_nonexistent_simulation_returns_404():
    """Deleting a non-existent simulation should return 404."""
    db = _mock_db(None, delete_ok=False)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/v1/simulations/00000000-0000-0000-0000-000000000999")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_delete_in_memory_fallback_works():
    """Deleting from the in-memory fallback store should work."""
    from app.db import DatabaseClient

    db = DatabaseClient()
    # Insert a record into in-memory store
    sim_id = "11111111-1111-1111-1111-111111111111"
    db._saved.append({
        "id": sim_id,
        "region_id": "bengaluru",
        "params": {},
        "horizon_months": 6,
        "result_summary": {},
        "cell_states": [],
    })
    assert len(db._saved) == 1

    deleted = await db.delete_simulation(uuid4())  # wrong ID
    assert deleted is False
    assert len(db._saved) == 1

    deleted = await db.delete_simulation(UUID(sim_id))
    assert deleted is True
    assert len(db._saved) == 0


# ── Export endpoint tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_json_returns_full_data():
    """JSON export should return the complete simulation data."""
    db = _mock_db(MOCK_SIMULATION)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/simulations/{MOCK_SIMULATION['id']}/export",
            params={"format": "json"},
        )

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == MOCK_SIMULATION["id"]
    assert data["data"]["cell_states"] == MOCK_SIMULATION["cell_states"]
    assert data["meta"]["format"] == "json"


@pytest.mark.asyncio
async def test_export_csv_returns_proper_format():
    """CSV export should return properly formatted CSV with headers and rows."""
    db = _mock_db(MOCK_SIMULATION)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/simulations/{MOCK_SIMULATION['id']}/export",
            params={"format": "csv"},
        )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers.get("content-disposition", "")

    lines = response.text.strip().splitlines()
    # Header + 4 data rows (2 months × 2 cells)
    assert len(lines) == 5
    assert lines[0] == "month,h3Index,gdp,unemployment,realEstateIdx,transitLoad"
    # Check first data row
    assert "1,8860a2589ffffff" in lines[1]


@pytest.mark.asyncio
async def test_export_nonexistent_simulation_returns_404():
    """Exporting a non-existent simulation should return 404."""
    db = _mock_db(None)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/simulations/00000000-0000-0000-0000-000000000999/export",
            params={"format": "json"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_csv_no_cell_states_returns_400():
    """CSV export with empty cell_states should return 400."""
    sim_no_cells = {**MOCK_SIMULATION, "cell_states": []}
    db = _mock_db(sim_no_cells)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/simulations/{MOCK_SIMULATION['id']}/export",
            params={"format": "csv"},
        )

    assert response.status_code == 400


# ── Summary endpoint tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_returns_lightweight_data():
    """Summary should return key fields without cell_states."""
    db = _mock_db(MOCK_SIMULATION)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/simulations/{MOCK_SIMULATION['id']}/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    summary = data["data"]
    assert summary["id"] == MOCK_SIMULATION["id"]
    assert summary["city"] == "bengaluru"
    assert summary["scenario"] == "IT boom +20%"
    assert summary["horizon"] == 12
    assert summary["verdict"] == "Positive growth expected"
    assert "key_metrics" in summary
    assert summary["created_at"] == "2025-01-15T10:00:00Z"
    # cell_states must NOT be present
    assert "cell_states" not in summary


@pytest.mark.asyncio
async def test_summary_nonexistent_simulation_returns_404():
    """Summary for a non-existent simulation should return 404."""
    db = _mock_db(None)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/simulations/00000000-0000-0000-0000-000000000999/summary"
        )

    assert response.status_code == 404
