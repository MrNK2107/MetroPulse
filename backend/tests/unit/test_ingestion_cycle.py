"""run_ingestion_cycle with fake connectors: fallback order, manifest, quality and status (no network)."""
from __future__ import annotations

import pytest

from app import realtime
from app.realtime import PRIORITY_DOMAINS, RealtimeConnector, run_ingestion_cycle


class Fake(RealtimeConnector):
    def __init__(self, domain, name, payload=None, rows=None, error=None):
        self.domain, self.source_name = domain, name
        self.payload, self.rows, self.error = payload, rows, error
        self.calls = 0

    async def fetch(self, city):
        self.calls += 1
        if self.error:
            raise self.error
        return self.payload

    def normalize(self, payload):
        return self.rows or []


def ok(domain, name, **values):
    return Fake(domain, name, payload={"raw": 1}, rows=[{"domain": domain, **values}])


class Db:
    def __init__(self):
        self.saved = []

    async def save_city_snapshot(self, snapshot):
        self.saved.append(snapshot)


@pytest.mark.asyncio
async def test_fallback_connector_fills_a_failed_domain_without_lowering_quality(monkeypatch):
    primary = Fake("news", "Google News", error=RuntimeError("dns down"))
    fallback = ok("news", "GDELT", sentiment=0.2)
    connectors = (
        primary,
        fallback,
        ok("mobility", "Mobility", index=1.1),
        ok("jobs", "Jobs", index=0.9),
        ok("land_value", "Land", index=1.0),
        ok("census", "City YAML Census Data", population=100, label="text is dropped"),
    )
    monkeypatch.setattr(realtime, "CONNECTORS", connectors)
    db = Db()
    snap = await run_ingestion_cycle(db, "Delhi NCR")

    assert db.saved == [snap]
    assert snap.city == "delhi_ncr"
    assert snap.quality_score == 1.0
    assert snap.status == "fresh"
    assert snap.aggregate_metrics == {"domains_active": 5.0}
    assert snap.source_manifest["news"].source == "GDELT"
    assert snap.source_manifest["news"].freshness == "fresh"
    assert snap.source_manifest["census"].freshness == "static"
    assert snap.source_manifest["census"].confidence == 0.9
    # Only numeric values are kept, under a per-domain key.
    assert snap.h3_cells["_city_level_census"] == {"population": 100}


@pytest.mark.asyncio
async def test_first_successful_connector_wins_and_later_ones_are_skipped(monkeypatch):
    first = ok("news", "Google News", sentiment=0.5)
    second = ok("news", "GDELT", sentiment=-0.5)
    monkeypatch.setattr(realtime, "CONNECTORS", (first, second))
    snap = await run_ingestion_cycle(Db(), "pune")

    assert second.calls == 0
    assert snap.h3_cells["_city_level_news"] == {"sentiment": 0.5}


@pytest.mark.asyncio
async def test_missing_domains_are_reported_and_low_quality_is_degraded(monkeypatch):
    connectors = (
        ok("news", "News", sentiment=0.1),
        Fake("mobility", "Mobility", payload=None),
        Fake("jobs", "Jobs", payload={"raw": 1}, rows=[]),
        Fake("land_value", "Land", error=ValueError("boom")),
        ok("census", "Census", population=1),
    )
    monkeypatch.setattr(realtime, "CONNECTORS", connectors)
    snap = await run_ingestion_cycle(Db(), "pune")

    assert snap.quality_score == pytest.approx(2 / 5)
    assert snap.status == "degraded"
    m = snap.source_manifest
    assert m["mobility"].notes == "Connector returned no data"
    assert m["jobs"].notes == "Connector returned empty data"
    assert m["land_value"].notes == "Error: boom"
    assert all(m[d].freshness == "missing" and m[d].confidence == 0.0 for d in ("mobility", "jobs", "land_value"))


@pytest.mark.asyncio
async def test_unconfigured_domains_are_listed_and_nothing_saved_without_data(monkeypatch):
    monkeypatch.setattr(realtime, "CONNECTORS", (Fake("news", "News", payload=None),))
    db = Db()
    assert await run_ingestion_cycle(db, "pune") is None
    assert db.saved == []


@pytest.mark.asyncio
async def test_unconfigured_priority_domains_get_placeholder_entries(monkeypatch):
    monkeypatch.setattr(realtime, "CONNECTORS", (ok("news", "News", sentiment=0.0),))
    snap = await run_ingestion_cycle(Db(), "pune")

    assert set(snap.source_manifest) == set(PRIORITY_DOMAINS)
    assert snap.source_manifest["jobs"].source == "Not configured"
    assert snap.quality_score == 1.0
