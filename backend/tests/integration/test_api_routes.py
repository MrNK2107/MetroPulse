"""Health, regions, case-study and realtime routes beyond the happy paths (no network)."""
from __future__ import annotations

import types

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app
from app.routes import realtime as realtime_routes


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _with_sources(*freshness: str):
    class FakeDb:
        _client = None

        async def list_data_sources(self, city="bengaluru"):
            return [{"domain": f"d{i}", "freshness": f} for i, f in enumerate(freshness)]

    async def dep():
        return FakeDb()

    app.dependency_overrides[get_db] = dep


@pytest.mark.parametrize(
    ("freshness", "status"),
    [
        (("fresh", "static"), "healthy"),
        (("fresh", "stale"), "degraded"),
        (("fresh", "missing"), "degraded"),
        (("demo", "missing"), "demo"),
        (("demo", "demo"), "demo"),
    ],
)
@pytest.mark.asyncio
async def test_data_health_status_from_source_freshness(client, freshness, status):
    _with_sources(*freshness)
    r = await client.get("/api/health/data?city=pune")
    body = r.json()
    assert r.status_code == 200
    assert body["data"]["status"] == status
    assert body["data"]["city"] == "pune"
    assert len(body["data"]["sources"]) == len(freshness)


@pytest.mark.asyncio
async def test_health_reports_in_memory_fallback(client):
    _with_sources()
    r = await client.get("/api/health")
    assert r.json()["data"]["db_status"] == "in_memory_fallback"


@pytest.mark.asyncio
async def test_region_baseline_shape(client):
    r = await client.get("/api/regions/pune/baseline")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["region_id"] == "pune"
    assert data["data_quality"] == "estimated"
    assert 0 < data["unemployment"] < 1


@pytest.mark.parametrize("path", ["baseline", "profile"])
@pytest.mark.parametrize("region", ["atlantis", "not-a-city", "pune.yaml"])
@pytest.mark.asyncio
async def test_unknown_or_malformed_region_is_404(client, path, region):
    r = await client.get(f"/api/regions/{region}/{path}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_case_studies_meta_count_matches_data(client):
    r = await client.get("/api/case-studies")
    body = r.json()
    assert body["meta"]["count"] == len(body["data"]) == 20

    r = await client.get("/api/case-studies?city=hyderabad")
    body = r.json()
    assert 0 < body["meta"]["count"] <= 20
    assert body["meta"]["count"] == len(body["data"])


@pytest.mark.asyncio
async def test_ingest_reports_snapshot_without_touching_the_network(client, monkeypatch):
    calls = []

    async def fake_cycle(db, city):
        calls.append(city)
        return types.SimpleNamespace(id="snap-1", status="partial", quality_score=0.42)

    monkeypatch.setattr(realtime_routes, "run_ingestion_cycle", fake_cycle)
    r = await client.post("/api/ingest?city=surat")
    assert calls == ["surat"]
    assert r.json() == {
        "success": True,
        "data": {"snapshot_id": "snap-1", "status": "partial", "quality_score": 0.42},
        "error": None,
        "meta": {"city": "surat"},
    }


@pytest.mark.asyncio
async def test_ingest_with_no_data(client, monkeypatch):
    async def fake_cycle(db, city):
        return None

    monkeypatch.setattr(realtime_routes, "run_ingestion_cycle", fake_cycle)
    body = (await client.post("/api/ingest?city=surat")).json()
    assert body["success"] is False
    assert body["data"] == {"snapshot_id": None, "status": "no_data", "quality_score": 0.0}


@pytest.mark.asyncio
async def test_realtime_routes_require_city(client):
    for path in ("/api/data-sources", "/api/snapshots/latest", "/api/snapshots/x/quality"):
        r = await client.get(path)
        assert r.status_code == 422, path
    assert (await client.post("/api/ingest")).status_code == 422
