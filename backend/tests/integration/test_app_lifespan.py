"""app.main: startup/shutdown lifespan, the background ingestion loop, and CORS. No network."""
from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app import main, realtime


class StopLoop(BaseException):
    """Raised by the fake sleep to end the endless loop (BaseException, like CancelledError)."""


@pytest.fixture
def loop_env(monkeypatch):
    """Fake cities, fake ingestion and a sleep that records and stops after N periodic waits."""
    state = {"ingested": [], "sleeps": [], "fail_for": set(), "max_periodic": 3}

    async def fake_cycle(db, city):
        state["ingested"].append(city)
        if city in state["fail_for"]:
            raise RuntimeError(f"{city} feed down")
        return None

    async def fake_sleep(seconds):
        state["sleeps"].append(seconds)
        periodic = [s for s in state["sleeps"] if s == main.settings.news_refresh_seconds]
        if len(periodic) > state["max_periodic"]:
            raise StopLoop

    monkeypatch.setattr(realtime, "run_ingestion_cycle", fake_cycle)
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(main, "_all_city_ids", lambda: ["a", "b"])
    monkeypatch.setattr(main.settings, "news_refresh_seconds", 900)
    return state


@pytest.mark.asyncio
async def test_ingestion_loop_runs_every_city_then_rotates(loop_env):
    with pytest.raises(StopLoop):
        await main._ingestion_loop(db=object())
    # Startup pass over every city (2 s apart), then one city per refresh period, round robin.
    assert loop_env["ingested"] == ["a", "b", "a", "b", "a"]
    assert loop_env["sleeps"] == [2, 2, 900, 900, 900, 900]


@pytest.mark.asyncio
async def test_ingestion_loop_survives_failing_cities(loop_env, caplog):
    loop_env["fail_for"] = {"a"}
    with pytest.raises(StopLoop):
        await main._ingestion_loop(db=object())
    # A failure neither stops the loop nor stalls the rotation on the failing city.
    assert loop_env["ingested"] == ["a", "b", "a", "b", "a"]
    messages = [r.getMessage() for r in caplog.records]
    assert messages.count("Initial ingestion failed for a: a feed down") == 1
    # The log names the city that failed (scheduled runs 1 and 3 are "a").
    assert messages.count("Scheduled ingestion failed for a: a feed down") == 2
    assert not any("failed for b" in m for m in messages)


@pytest.mark.asyncio
async def test_ingestion_loop_with_no_cities_just_waits(loop_env, monkeypatch):
    monkeypatch.setattr(main, "_all_city_ids", lambda: [])
    with pytest.raises(StopLoop):
        await main._ingestion_loop(db=object())
    assert loop_env["ingested"] == []
    assert loop_env["sleeps"][:2] == [900, 900]


@pytest.mark.asyncio
async def test_all_city_ids_lists_the_yaml_configs():
    ids = main._all_city_ids()
    assert "bengaluru" in ids and len(ids) == 30


@pytest.mark.asyncio
async def test_lifespan_starts_and_cancels_the_ingestion_task(monkeypatch):
    started = asyncio.Event()
    cancelled = []

    async def fake_loop(db):
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    monkeypatch.setattr(main, "_ingestion_loop", fake_loop)
    monkeypatch.setattr(main.settings, "seed_case_studies_on_startup", False)

    async with main.lifespan(main.app):
        await asyncio.wait_for(started.wait(), timeout=5)
        assert realtime._http_client is not None and not realtime._http_client.is_closed

    assert cancelled == [True]
    assert realtime._http_client is None  # shared client closed on shutdown


@pytest.mark.asyncio
async def test_lifespan_seeding_failure_does_not_block_startup(monkeypatch):
    async def fake_loop(db):
        await asyncio.Event().wait()

    class Db:
        async def seed_case_studies(self):
            raise RuntimeError("seed failed")

    async def fake_get_db():
        return Db()

    monkeypatch.setattr(main, "_ingestion_loop", fake_loop)
    monkeypatch.setattr(main, "get_db", fake_get_db)
    monkeypatch.setattr(main.settings, "seed_case_studies_on_startup", True)

    async with main.lifespan(main.app):
        pass  # reaching here is the assertion


@pytest.mark.asyncio
@pytest.mark.parametrize("header", ["authorization", "x-ingest-token", "content-type"])
async def test_cors_preflight_allows_the_ingest_headers(header):
    origin = main.settings.cors_origin_list[0]
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.options(
            "/api/ingest?city=pune",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": header,
            },
        )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin
    assert header in r.headers["access-control-allow-headers"].lower()


@pytest.mark.asyncio
async def test_cors_preflight_rejects_unknown_origins():
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as c:
        r = await c.options(
            "/api/ingest",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
        )
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers
