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


# ── Opt-in INGEST_TOKEN on POST /api/ingest ─────────────────────────────────


@pytest.fixture
def ingest_calls(monkeypatch):
    calls = []

    async def fake_cycle(db, city):
        calls.append(city)
        return types.SimpleNamespace(id="snap-1", status="fresh", quality_score=1.0)

    monkeypatch.setattr(realtime_routes, "run_ingestion_cycle", fake_cycle)
    return calls


@pytest.fixture
def ingest_token(monkeypatch):
    monkeypatch.setattr(realtime_routes.settings, "ingest_token", "s3cret-token")
    return "s3cret-token"


@pytest.mark.asyncio
async def test_ingest_is_open_when_no_token_is_configured(client, ingest_calls, monkeypatch):
    monkeypatch.setattr(realtime_routes.settings, "ingest_token", "")
    r = await client.post("/api/ingest?city=pune")
    assert r.status_code == 200
    assert ingest_calls == ["pune"]
    # A stray header is ignored while the check is off.
    r = await client.post("/api/ingest?city=pune", headers={"Authorization": "Bearer whatever"})
    assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong"},
        {"Authorization": "s3cret-token"},  # missing "Bearer "
        {"Authorization": "Basic czNjcmV0LXRva2Vu"},
        {"X-Ingest-Token": "wrong"},
        {"X-Ingest-Token": ""},
        {"Authorization": "Bearer "},
    ],
)
async def test_ingest_rejects_missing_or_wrong_token(client, ingest_calls, ingest_token, headers):
    r = await client.post("/api/ingest?city=pune", headers=headers)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert r.json() == {"detail": "Invalid or missing ingest token"}
    assert ingest_calls == []  # nothing fetched


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer s3cret-token"},
        {"Authorization": "bearer s3cret-token"},
        {"X-Ingest-Token": "s3cret-token"},
        {"X-Ingest-Token": "s3cret-token", "Authorization": "Bearer wrong"},
    ],
)
async def test_ingest_accepts_the_configured_token(client, ingest_calls, ingest_token, headers):
    r = await client.post("/api/ingest?city=pune", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["snapshot_id"] == "snap-1"
    assert ingest_calls == ["pune"]


@pytest.mark.asyncio
async def test_ingest_token_does_not_gate_read_endpoints(client, ingest_token):
    _with_sources("fresh")
    r = await client.get("/api/data-sources?city=pune")
    assert r.status_code == 200


def test_ingest_token_setting_reads_env(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("INGEST_TOKEN", "from-env")
    assert Settings(_env_file=None).ingest_token == "from-env"
    monkeypatch.delenv("INGEST_TOKEN")
    assert Settings(_env_file=None).ingest_token == ""
