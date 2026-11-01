from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from app import realtime
from app.db import DatabaseClient
from app.realtime import (
    GDELTNewsConnector,
    GoogleNewsConnector,
    NewsMobilitySentimentConnector,
    NewsJobsSentimentConnector,
    NewsLandValueSentimentConnector,
    StaticCensusConnector,
    build_demo_manifest,
    run_ingestion_cycle,
    snapshot_quality,
)
from app.realtime_models import SnapshotData, SourceStatus

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "realtime"
GOOGLE_NEWS_RSS = (FIXTURES / "google_news_rss.xml").read_text(encoding="utf-8")
GDELT_ARTLIST = (FIXTURES / "gdelt_artlist.json").read_text(encoding="utf-8")


class FakeHttp:
    """Serves fixture responses through httpx.MockTransport (no sockets).

    ``fail`` holds hostnames that raise ConnectError instead of answering.
    """

    def __init__(self):
        self.fail: set[str] = set()
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host in self.fail:
            raise httpx.ConnectError("simulated outage", request=request)
        if host == "news.google.com":
            return httpx.Response(200, text=GOOGLE_NEWS_RSS,
                                  headers={"content-type": "application/rss+xml"})
        if host == "api.gdeltproject.org":
            return httpx.Response(200, text=GDELT_ARTLIST,
                                  headers={"content-type": "application/json"})
        return httpx.Response(404)

    def hosts(self) -> list[str]:
        return [r.url.host for r in self.requests]


@pytest.fixture
def fake_http(monkeypatch):
    fake = FakeHttp()
    client = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    monkeypatch.setattr(realtime, "_http_client", client)
    monkeypatch.setattr(realtime, "_response_cache", {})

    async def no_sleep(_seconds):
        return None

    # _fetch_with_retry backs off with asyncio.sleep between retries.
    monkeypatch.setattr(realtime.asyncio, "sleep", no_sleep)
    return fake


def test_demo_manifest_marks_sources_as_demo():
    manifest = build_demo_manifest()

    assert set(manifest) == {"mobility", "jobs", "land_value", "census", "news"}
    assert manifest["mobility"].freshness == "demo"
    assert manifest["mobility"].confidence < 0.5


def test_snapshot_quality_reports_unavailable_without_snapshot():
    quality = snapshot_quality(None)

    assert quality.status == "unavailable"
    assert quality.quality_score == 0.0
    assert quality.source_manifest["jobs"].freshness == "demo"


@pytest.mark.asyncio
async def test_in_memory_latest_snapshot_round_trip():
    db = DatabaseClient()
    observed = datetime.now(timezone.utc)
    snapshot = SnapshotData(
        id="snapshot-test",
        city="bengaluru",
        snapshot_at=observed,
        status="degraded",
        quality_score=0.7,
        source_manifest={
            "mobility": SourceStatus(
                domain="mobility",
                source="Google News (Transport)",
                observed_at=observed,
                fetched_at=observed,
                freshness="fresh",
                confidence=0.7,
                cadence_seconds=604800,
            )
        },
        h3_cells={
            "88618925a9fffff": {
                "economicActivity": 10.0,
                "jobDensity": 20.0,
                "congestion": 0.4,
            }
        },
    )

    await db.save_city_snapshot(snapshot)
    latest = await db.get_latest_snapshot("bengaluru")
    sources = await db.list_data_sources("bengaluru")

    assert latest is snapshot
    assert sources[0]["source"] == "Google News (Transport)"
    assert sources[0]["freshness"] == "fresh"


# ── Google News RSS Connector ────────────────────────────────────────────────


def test_google_news_normalize_empty():
    connector = GoogleNewsConnector()
    result = connector.normalize({"xml": ""})
    assert result == []


def test_google_news_normalize_with_rss():
    connector = GoogleNewsConnector()
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
        <item><title>Bengaluru economy sees strong growth in tech sector</title></item>
        <item><title>New infrastructure projects boost Bengaluru development</title></item>
        <item><title>Bengaluru traffic congestion worsens amid construction</title></item>
    </channel></rss>"""
    result = connector.normalize({"xml": rss_xml})
    assert len(result) == 1
    assert result[0]["domain"] == "news"
    assert result[0]["article_count"] == 3
    assert 0.0 <= result[0]["news_pressure"] <= 1.0
    assert -1.0 <= result[0]["news_sentiment"] <= 1.0


@pytest.mark.asyncio
async def test_google_news_fetch_parses_fixture(fake_http):
    connector = GoogleNewsConnector()
    payload = await connector.fetch("bengaluru")
    assert payload is not None
    assert payload["city"] == "Bengaluru"
    query = fake_http.requests[0].url.params["q"]
    assert query.startswith('"Bengaluru"')
    rows = connector.normalize(payload)
    assert rows[0]["article_count"] == 4.0
    # Fixture titles carry more positive words (expand, boost, hiring, investment, growth)
    # than negative ones (congestion, flood, damage), so sentiment is positive.
    assert 0.0 < rows[0]["news_sentiment"] <= 1.0


@pytest.mark.asyncio
async def test_google_news_fetch_handles_network_error(fake_http):
    fake_http.fail.add("news.google.com")
    connector = GoogleNewsConnector()
    result = await connector.fetch("bengaluru")
    assert result is None
    # One initial attempt plus two retries.
    assert fake_http.hosts() == ["news.google.com"] * 3


# ── GDELT Connector ─────────────────────────────────────────────────────────


def test_gdelt_normalize_empty_payload():
    connector = GDELTNewsConnector()
    result = connector.normalize({})
    assert result == []


def test_gdelt_normalize_with_articles():
    connector = GDELTNewsConnector()
    result = connector.normalize({
        "articles": [
            {"tone": 2.5},
            {"tone": -1.0},
            {"tone": 0.5},
        ]
    })
    assert len(result) == 1
    assert result[0]["domain"] == "news"
    assert result[0]["article_count"] == 3
    assert 0.0 <= result[0]["news_pressure"] <= 1.0
    assert -1.0 <= result[0]["news_sentiment"] <= 1.0


@pytest.mark.asyncio
async def test_gdelt_fetch_parses_fixture(fake_http):
    connector = GDELTNewsConnector()
    payload = await connector.fetch("bengaluru")
    assert payload is not None and len(payload["articles"]) == 3
    params = fake_http.requests[0].url.params
    assert params["format"] == "json" and params["mode"] == "ArtList"
    rows = connector.normalize(payload)
    assert rows[0]["article_count"] == 3.0
    assert rows[0]["news_sentiment"] == pytest.approx((3.2 - 2.0 + 0.8) / 3 / 10)


@pytest.mark.asyncio
async def test_gdelt_fetch_handles_network_error(fake_http):
    fake_http.fail.add("api.gdeltproject.org")
    connector = GDELTNewsConnector()
    result = await connector.fetch("bengaluru")
    assert result is None
    assert fake_http.hosts() == ["api.gdeltproject.org"] * 3


# ── Mobility News Sentiment Connector ────────────────────────────────────────


def test_mobility_normalize_empty():
    connector = NewsMobilitySentimentConnector()
    result = connector.normalize({"xml": ""})
    assert result == []


def test_mobility_normalize_with_rss():
    connector = NewsMobilitySentimentConnector()
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
        <item><title>Bengaluru metro expansion reaches Whitefield</title></item>
        <item><title>Traffic congestion worsens on ORR Bengaluru</title></item>
    </channel></rss>"""
    result = connector.normalize({"xml": rss_xml})
    assert len(result) == 1
    assert result[0]["domain"] == "mobility"
    assert -1.0 <= result[0]["mobility_sentiment"] <= 1.0


# ── News Jobs Sentiment Connector ────────────────────────────────────────────


def test_jobs_normalize_empty():
    connector = NewsJobsSentimentConnector()
    result = connector.normalize({"xml": ""})
    assert result == []


def test_jobs_normalize_with_rss():
    connector = NewsJobsSentimentConnector()
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
        <item><title>Major hiring spree in Bengaluru IT sector</title></item>
        <item><title>Bengaluru sees layoffs in startup sector</title></item>
    </channel></rss>"""
    result = connector.normalize({"xml": rss_xml})
    assert len(result) == 1
    assert result[0]["domain"] == "jobs"
    assert -1.0 <= result[0]["jobs_sentiment"] <= 1.0


# ── News Land Value Sentiment Connector ──────────────────────────────────────


def test_land_value_normalize_empty():
    connector = NewsLandValueSentimentConnector()
    result = connector.normalize({"xml": ""})
    assert result == []


def test_land_value_normalize_with_rss():
    connector = NewsLandValueSentimentConnector()
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
        <item><title>Bengaluru real estate boom continues</title></item>
        <item><title>Property prices surge in Whitefield</title></item>
    </channel></rss>"""
    result = connector.normalize({"xml": rss_xml})
    assert len(result) == 1
    assert result[0]["domain"] == "land_value"
    assert -1.0 <= result[0]["real_estate_sentiment"] <= 1.0


# ── Static Census Connector ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_census_fetch_returns_city_data():
    connector = StaticCensusConnector()
    result = await connector.fetch("bengaluru")
    assert result is not None
    assert result["population"] == 13_000_000
    assert 0 < result["unemployment_rate"] < 1


def test_census_normalize():
    connector = StaticCensusConnector()
    result = connector.normalize({
        "population": 13_000_000,
        "unemployment_rate": 0.035,
        "literacy_rate": 0.88,
        "slum_population_pct": 0.15,
        "employment_formal": 3_500_000,
        "employment_informal": 5_000_000,
        "gdp_estimate_crores": 550_000,
    })
    assert len(result) == 1
    assert result[0]["domain"] == "census"
    assert result[0]["population"] == 13_000_000


# ── Integration: ingestion cycle ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ingestion_cycle_bengaluru(fake_http):
    db = DatabaseClient()
    snapshot = await run_ingestion_cycle(db, "bengaluru")
    assert snapshot is not None
    assert snapshot.city == "bengaluru"
    # All five domains answer from fixtures (Google News wins, GDELT is never asked).
    assert snapshot.status == "fresh"
    assert snapshot.quality_score == 1.0
    assert "api.gdeltproject.org" not in fake_http.hosts()
    assert snapshot.source_manifest["news"].source == "Google News RSS"
    assert snapshot.source_manifest["census"].freshness == "static"
    assert snapshot.h3_cells["_city_level_census"]["population"] == 13_000_000
    # Saved to the in-memory store (no Supabase configured in tests).
    assert (await db.get_latest_snapshot("bengaluru")).id == snapshot.id


@pytest.mark.asyncio
async def test_ingestion_cycle_mumbai_falls_back_to_gdelt(fake_http):
    fake_http.fail.add("news.google.com")
    db = DatabaseClient()
    snapshot = await run_ingestion_cycle(db, "mumbai")
    assert snapshot is not None
    assert snapshot.city == "mumbai"
    # Only news (via GDELT) and census succeed: 2 of 5 domains.
    assert snapshot.source_manifest["news"].source == "GDELT"
    assert snapshot.source_manifest["mobility"].freshness == "missing"
    assert snapshot.quality_score == pytest.approx(2 / 5)
    assert snapshot.status == "degraded"


@pytest.mark.asyncio
async def test_ingestion_cycle_nonexistent_city(fake_http):
    fake_http.fail.update({"news.google.com", "api.gdeltproject.org"})
    db = DatabaseClient()
    # No city config and every feed down: nothing to save, and no crash.
    snapshot = await run_ingestion_cycle(db, "atlantis")
    assert snapshot is None
