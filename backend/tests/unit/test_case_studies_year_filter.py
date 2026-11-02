"""Tests for case-studies endpoint year filtering."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app


MOCK_STUDIES = [
    {"id": "s1", "title": "Study 2018", "city": "Mumbai", "year": 2018, "sectors": ["manufacturing"], "policies": []},
    {"id": "s2", "title": "Study 2020", "city": "Mumbai", "year": 2020, "sectors": ["it_ites"], "policies": []},
    {"id": "s3", "title": "Study 2022", "city": "Hyderabad", "year": 2022, "sectors": ["manufacturing"], "policies": ["Make in India"]},
    {"id": "s4", "title": "Study 2024", "city": "Chennai", "year": 2024, "sectors": ["transport_logistics"], "policies": []},
]


def _mock_db(studies=None):
    db = AsyncMock()
    db.list_case_studies = AsyncMock(return_value=studies or [])
    return db


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Clear dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_year_from_filter():
    """year_from should exclude studies before the given year."""
    db = _mock_db(MOCK_STUDIES)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/case-studies", params={"year_from": 2020})

    assert response.status_code == 200
    data = response.json()
    years = [s["year"] for s in data["data"]]
    assert all(y >= 2020 for y in years)
    assert len(data["data"]) == 3  # 2020, 2022, 2024


@pytest.mark.asyncio
async def test_year_to_filter():
    """year_to should exclude studies after the given year."""
    db = _mock_db(MOCK_STUDIES)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/case-studies", params={"year_to": 2020})

    assert response.status_code == 200
    data = response.json()
    years = [s["year"] for s in data["data"]]
    assert all(y <= 2020 for y in years)
    assert len(data["data"]) == 2  # 2018, 2020


@pytest.mark.asyncio
async def test_year_range_filter():
    """Combining year_from and year_to should narrow results to the intersection."""
    db = _mock_db(MOCK_STUDIES)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/case-studies",
            params={"year_from": 2019, "year_to": 2022},
        )

    assert response.status_code == 200
    data = response.json()
    years = [s["year"] for s in data["data"]]
    assert all(2019 <= y <= 2022 for y in years)
    assert len(data["data"]) == 2  # 2020, 2022


@pytest.mark.asyncio
async def test_year_filter_with_other_filters():
    """Year filters should combine correctly with city/sector filters."""
    # Simulate DB returning only Mumbai studies (city filtering done by DB layer)
    mumbai_studies = [s for s in MOCK_STUDIES if s["city"] == "Mumbai"]
    db = _mock_db(mumbai_studies)
    app.dependency_overrides[get_db] = lambda: db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/case-studies",
            params={"year_from": 2020, "city": "Mumbai"},
        )

    assert response.status_code == 200
    data = response.json()
    # Only Mumbai studies from 2020 onward
    for s in data["data"]:
        assert s["city"] == "Mumbai"
        assert s["year"] >= 2020
