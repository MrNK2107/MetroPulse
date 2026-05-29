from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from app.config import settings
from app.realtime_models import (
    SnapshotData,
    SnapshotQuality,
    SnapshotStatus,
    SourceStatus,
    utc_now,
)

logger = logging.getLogger(__name__)

PRIORITY_DOMAINS = ("mobility", "jobs", "land_value", "census", "news")

# ── City display names for news queries ──────────────────────────────────────
_CITY_DISPLAY: dict[str, str] = {
    "bengaluru": "Bengaluru",
    "mumbai": "Mumbai",
    "delhi_ncr": "Delhi NCR",
    "chennai": "Chennai",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "kolkata": "Kolkata",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "lucknow": "Lucknow",
    "chandigarh": "Chandigarh",
    "bhubaneswar": "Bhubaneswar",
}

# ── Sentiment keywords ───────────────────────────────────────────────────────
_POSITIVE_WORDS = {
    "growth", "boom", "surge", "rise", "increase", "boost", "expand",
    "investment", "hiring", "development", "improve", "recovery", "gains",
    "uptick", "flourish", "thrive", "opportunities", "infrastructure",
    "launch", "milestone", "record", "strong", "robust", "positive",
}
_NEGATIVE_WORDS = {
    "crisis", "decline", "fall", "drop", "slowdown", "layoff", "loss",
    "recession", "slump", "shutdown", "protest", "strike", "flood",
    "damage", "congestion", "pollution", "shortage", "scam", "fraud",
    "collapse", "warning", "risk", "concern", "struggle", "weak",
}

# ── City center coordinates (lat, lng) for Overpass queries ──────────────────
_CITY_CENTERS: dict[str, tuple[float, float]] = {
    "bengaluru": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "delhi_ncr": (28.6139, 77.2090),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462),
    "chandigarh": (30.7333, 76.7794),
    "bhubaneswar": (20.2961, 85.8245),
}


def source_cadence_seconds(domain: str) -> int:
    return {
        "mobility": settings.mobility_refresh_seconds,
        "jobs": settings.jobs_refresh_seconds,
        "land_value": settings.land_value_refresh_seconds,
        "census": settings.census_refresh_seconds,
        "news": settings.news_refresh_seconds,
    }.get(domain, 86_400)


def payload_hash(payload: Any) -> str:
    import json
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_demo_manifest() -> dict[str, SourceStatus]:
    now = datetime.now(timezone.utc)
    sources = {
        "mobility": "Estimated from city YAML transit constants",
        "jobs": "Estimated from city YAML employment baselines",
        "land_value": "Estimated from distance-decay real-estate model",
        "census": "Estimated from city YAML population metadata",
        "news": "No live news data available",
    }
    return {
        domain: SourceStatus(
            domain=domain,  # type: ignore[arg-type]
            source=source,
            observed_at=now,
            fetched_at=now,
            freshness="demo",
            confidence=0.25 if domain != "news" else 0.0,
            cadence_seconds=source_cadence_seconds(domain),
            notes="Using city baseline estimates",
        )
        for domain, source in sources.items()
    }


def snapshot_quality(snapshot: SnapshotData | None) -> SnapshotQuality:
    if snapshot is None:
        return SnapshotQuality(
            status="unavailable",
            quality_score=0.0,
            source_manifest=build_demo_manifest(),
            message="No real-time snapshot is available for this city.",
        )
    if snapshot.status == "demo":
        message = "Using city baseline estimates. Live data sources will activate automatically when available."
    elif snapshot.status == "degraded":
        message = "Partial live data — some sources are using last-known-good values."
    else:
        message = "Using the latest live data from connected sources."
    return SnapshotQuality(
        status=snapshot.status,
        quality_score=snapshot.quality_score,
        source_manifest=snapshot.source_manifest,
        message=message,
    )


# ── Connector base class ────────────────────────────────────────────────────


class RealtimeConnector:
    domain: str = ""
    source_name: str = ""

    async def fetch(self, city: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def normalize(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError


# ── News: Google News RSS (primary) ─────────────────────────────────────────


class GoogleNewsConnector(RealtimeConnector):
    """Fetch city economic news via Google News RSS. Free, no API key, reliable."""
    domain = "news"
    source_name = "Google News RSS"

    _ECONOMY_TERMS = "economy OR infrastructure OR jobs OR housing OR development OR traffic"

    async def fetch(self, city: str) -> dict[str, Any] | None:
        display = _CITY_DISPLAY.get(city, city.replace("_", " ").title())
        query = f'"{display}" ({self._ECONOMY_TERMS})'
        url = "https://news.google.com/rss/search"
        params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return {"xml": resp.text, "city": display}
        except Exception as e:
            logger.warning("Google News RSS fetch failed for %s: %s", city, e)
            return None

    def normalize(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        articles = self._parse_rss(payload.get("xml", ""))
        if not articles:
            return []

        # Score sentiment from titles
        positive = 0
        negative = 0
        for art in articles:
            title_lower = art.lower()
            positive += sum(1 for w in _POSITIVE_WORDS if w in title_lower)
            negative += sum(1 for w in _NEGATIVE_WORDS if w in title_lower)

        total_sentiment_signals = positive + negative
        if total_sentiment_signals > 0:
            sentiment = (positive - negative) / total_sentiment_signals
        else:
            sentiment = 0.0

        article_count = len(articles)
        news_pressure = min(1.0, article_count / 30.0)

        return [{
            "domain": "news",
            "article_count": float(article_count),
            "news_pressure": round(news_pressure, 4),
            "news_sentiment": round(max(-1.0, min(1.0, sentiment)), 4),
        }]

    @staticmethod
    def _parse_rss(xml_text: str) -> list[str]:
        try:
            root = ET.fromstring(xml_text)
            items = root.findall(".//item")
            titles = []
            for item in items:
                title = item.findtext("title", "")
                if title:
                    titles.append(title)
            return titles
        except ET.ParseError:
            return []


# ── News: GDELT (fallback) ──────────────────────────────────────────────────


class GDELTNewsConnector(RealtimeConnector):
    """GDELT news as fallback. Shorter timeout since it's often unreliable."""
    domain = "news"
    source_name = "GDELT"

    async def fetch(self, city: str) -> dict[str, Any] | None:
        display = _CITY_DISPLAY.get(city, city.replace("_", " ").title())
        query = f'"{display}" (economy OR infrastructure OR traffic OR housing OR jobs OR development)'
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "format": "json",
            "mode": "ArtList",
            "maxrecords": 25,
            "sort": "DateDesc",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("GDELT fetch failed for %s: %s", city, e)
            return None

    def normalize(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        articles = payload.get("articles", [])
        if not articles:
            return []
        tones = []
        for art in articles:
            tone = art.get("tone")
            if tone is not None:
                try:
                    tones.append(float(tone))
                except (ValueError, TypeError):
                    pass
        avg_tone = sum(tones) / len(tones) if tones else 0.0
        news_pressure = max(0.0, min(1.0, len(articles) / 50.0))
        news_sentiment = max(-1.0, min(1.0, avg_tone / 10.0))
        return [{
            "domain": "news",
            "article_count": float(len(articles)),
            "news_pressure": news_pressure,
            "news_sentiment": news_sentiment,
        }]


# ── Mobility: OpenStreetMap infrastructure density ───────────────────────────


class NewsMobilitySentimentConnector(RealtimeConnector):
    """Mobility proxy: Google News RSS filtered for traffic/transport/metro news.
    Overpass API is blocked in India, so we use news as a proxy for transport activity.
    """
    domain = "mobility"
    source_name = "Google News (Transport)"

    async def fetch(self, city: str) -> dict[str, Any] | None:
        display = _CITY_DISPLAY.get(city, city.replace("_", " ").title())
        query = f'"{display}" (traffic OR metro OR transport OR commute OR road OR congestion OR infrastructure)'
        url = "https://news.google.com/rss/search"
        params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return {"xml": resp.text}
        except Exception as e:
            logger.warning("Mobility news fetch failed for %s: %s", city, e)
            return None

    def normalize(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        articles = GoogleNewsConnector._parse_rss(payload.get("xml", ""))
        if not articles:
            return []

        positive = 0
        negative = 0
        for title in articles:
            t = title.lower()
            positive += sum(1 for w in ("metro", "expansion", "new route", "flyover", "expressway", "infrastructure", "smart city") if w in t)
            negative += sum(1 for w in ("congestion", "traffic jam", "pothole", "accident", "gridlock", "delay", "waterlogging") if w in t)

        total = positive + negative
        sentiment = (positive - negative) / total if total > 0 else 0.0
        volume = min(1.0, len(articles) / 25.0)

        return [{
            "domain": "mobility",
            "mobility_article_count": float(len(articles)),
            "mobility_sentiment": round(max(-1.0, min(1.0, sentiment)), 4),
            "mobility_volume": round(volume, 4),
        }]


# ── Jobs: News-based employment sentiment ────────────────────────────────────


class NewsJobsSentimentConnector(RealtimeConnector):
    """Jobs proxy: Google News RSS filtered for employment/hiring/layoff news."""
    domain = "jobs"
    source_name = "Google News (Jobs)"

    async def fetch(self, city: str) -> dict[str, Any] | None:
        display = _CITY_DISPLAY.get(city, city.replace("_", " ").title())
        query = f'"{display}" (jobs OR hiring OR layoffs OR employment OR unemployment OR recruitment)'
        url = "https://news.google.com/rss/search"
        params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return {"xml": resp.text}
        except Exception as e:
            logger.warning("Jobs news fetch failed for %s: %s", city, e)
            return None

    def normalize(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        articles = GoogleNewsConnector._parse_rss(payload.get("xml", ""))
        if not articles:
            return []

        positive = 0
        negative = 0
        for title in articles:
            t = title.lower()
            positive += sum(1 for w in ("hiring", "recruitment", "jobs", "employment", "opportunity") if w in t)
            negative += sum(1 for w in ("layoff", "layoffs", "unemployment", "job loss", "fired", "downsizing") if w in t)

        total = positive + negative
        sentiment = (positive - negative) / total if total > 0 else 0.0
        volume = min(1.0, len(articles) / 20.0)

        return [{
            "domain": "jobs",
            "jobs_article_count": float(len(articles)),
            "jobs_sentiment": round(max(-1.0, min(1.0, sentiment)), 4),
            "jobs_volume": round(volume, 4),
        }]


# ── Land Value: News-based real estate sentiment ─────────────────────────────


class NewsLandValueSentimentConnector(RealtimeConnector):
    """Land value proxy: Google News RSS for real estate/rent/property news."""
    domain = "land_value"
    source_name = "Google News (Real Estate)"

    async def fetch(self, city: str) -> dict[str, Any] | None:
        display = _CITY_DISPLAY.get(city, city.replace("_", " ").title())
        query = f'"{display}" (real estate OR property OR rent OR housing OR construction OR home prices)'
        url = "https://news.google.com/rss/search"
        params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return {"xml": resp.text}
        except Exception as e:
            logger.warning("Land value news fetch failed for %s: %s", city, e)
            return None

    def normalize(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        articles = GoogleNewsConnector._parse_rss(payload.get("xml", ""))
        if not articles:
            return []

        positive = 0
        negative = 0
        for title in articles:
            t = title.lower()
            positive += sum(1 for w in ("boom", "surge", "rise", "demand", "construction", "growth", "appreciation") if w in t)
            negative += sum(1 for w in ("crash", "decline", "fall", "slump", "oversupply", "vacant", "correction") if w in t)

        total = positive + negative
        sentiment = (positive - negative) / total if total > 0 else 0.0
        volume = min(1.0, len(articles) / 20.0)

        return [{
            "domain": "land_value",
            "re_article_count": float(len(articles)),
            "real_estate_sentiment": round(max(-1.0, min(1.0, sentiment)), 4),
            "real_estate_volume": round(volume, 4),
        }]


# ── Census: Static from city YAML config ─────────────────────────────────────


class StaticCensusConnector(RealtimeConnector):
    """Census domain: read population/demographic data from city YAML config.
    Census data changes yearly — this is accurate but not real-time."""
    domain = "census"
    source_name = "City YAML Census Data"

    async def fetch(self, city: str) -> dict[str, Any] | None:
        from engine.config import CityConfig
        try:
            cfg = CityConfig.load(city)
            return {
                "population": cfg.population,
                "unemployment_rate": cfg.baselines.get("unemployment_rate", 0.05),
                "literacy_rate": cfg.baselines.get("literacy_rate", 0.8),
                "slum_population_pct": cfg.baselines.get("slum_population_pct", 0.15),
                "employment_formal": cfg.baselines.get("employment_formal", 1_000_000),
                "employment_informal": cfg.baselines.get("employment_informal", 500_000),
                "gdp_estimate_crores": cfg.baselines.get("gdp_estimate_crores", 100_000),
            }
        except FileNotFoundError:
            logger.warning("City config not found for census: %s", city)
            return None

    def normalize(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return [{
            "domain": "census",
            "population": float(payload.get("population", 0)),
            "unemployment_rate": float(payload.get("unemployment_rate", 0.05)),
            "literacy_rate": float(payload.get("literacy_rate", 0.8)),
            "slum_pct": float(payload.get("slum_population_pct", 0.15)),
            "formal_jobs": float(payload.get("employment_formal", 0)),
            "informal_jobs": float(payload.get("employment_informal", 0)),
            "gdp_crores": float(payload.get("gdp_estimate_crores", 0)),
        }]


# ── Connector registry ──────────────────────────────────────────────────────

CONNECTORS: tuple[RealtimeConnector, ...] = (
    GoogleNewsConnector(),
    GDELTNewsConnector(),
    NewsMobilitySentimentConnector(),
    NewsJobsSentimentConnector(),
    NewsLandValueSentimentConnector(),
    StaticCensusConnector(),
)


# ── Ingestion pipeline ──────────────────────────────────────────────────────


async def run_ingestion_cycle(db: Any, city: str) -> SnapshotData | None:
    """Run one ingestion cycle for a city: fetch, normalize, merge, save."""
    now = utc_now()
    merged_cells: dict[str, dict[str, float]] = {}
    source_manifest: dict[str, SourceStatus] = {}
    domains_ok = 0
    domains_total = 0

    # Track which domains we've already filled (first connector wins per domain)
    filled_domains: set[str] = set()

    for connector in CONNECTORS:
        domain = connector.domain
        if domain in filled_domains:
            continue  # already got data for this domain from a prior connector

        domains_total += 1
        cadence = source_cadence_seconds(domain)
        freshness: str = "fresh"
        if connector.source_name == "City YAML Census Data":
            freshness = "static"

        try:
            payload = await connector.fetch(city)
            if payload is not None:
                normalized = connector.normalize(payload)
                if normalized:
                    _merge_normalized(merged_cells, normalized, city)
                    domains_ok += 1
                    filled_domains.add(domain)
                    confidence = 0.7 if freshness == "fresh" else 0.9
                    source_manifest[domain] = SourceStatus(
                        domain=domain,  # type: ignore[arg-type]
                        source=connector.source_name,
                        observed_at=now,
                        fetched_at=now,
                        freshness=freshness,  # type: ignore[arg-type]
                        confidence=confidence,
                        cadence_seconds=cadence,
                    )
                else:
                    source_manifest[domain] = SourceStatus(
                        domain=domain,  # type: ignore[arg-type]
                        source=connector.source_name,
                        observed_at=None,
                        fetched_at=now,
                        freshness="missing",
                        confidence=0.0,
                        cadence_seconds=cadence,
                        notes="Connector returned empty data",
                    )
            else:
                source_manifest[domain] = SourceStatus(
                    domain=domain,  # type: ignore[arg-type]
                    source=connector.source_name,
                    observed_at=None,
                    fetched_at=now,
                    freshness="missing",
                    confidence=0.0,
                    cadence_seconds=cadence,
                    notes="Connector returned no data",
                )
        except Exception as e:
            logger.warning("Ingestion failed for %s/%s: %s", city, domain, e)
            source_manifest[domain] = SourceStatus(
                domain=domain,  # type: ignore[arg-type]
                source=connector.source_name,
                observed_at=None,
                fetched_at=now,
                freshness="missing",
                confidence=0.0,
                cadence_seconds=cadence,
                notes=f"Error: {e}",
            )

    # Fill any missing domains with "not configured" entries
    for domain in PRIORITY_DOMAINS:
        if domain not in source_manifest:
            source_manifest[domain] = SourceStatus(
                domain=domain,  # type: ignore[arg-type]
                source="Not configured",
                freshness="missing",
                confidence=0.0,
                cadence_seconds=source_cadence_seconds(domain),
            )

    if domains_ok == 0:
        logger.info("No connectors returned data for %s; skipping snapshot save", city)
        return None

    quality = domains_ok / max(domains_total, 1)
    status: SnapshotStatus = "fresh" if quality >= 0.6 else "degraded"

    snapshot = SnapshotData(
        id=str(uuid4()),
        city=city.lower().replace(" ", "_"),
        snapshot_at=now,
        status=status,
        quality_score=quality,
        source_manifest=source_manifest,
        h3_cells=merged_cells,
        aggregate_metrics={"domains_active": float(domains_ok)},
    )

    await db.save_city_snapshot(snapshot)
    logger.info("Saved snapshot %s for %s (%d/%d domains)", snapshot.id, city, domains_ok, domains_total)
    return snapshot


def _merge_normalized(
    merged: dict[str, dict[str, float]],
    normalized: list[dict[str, Any]],
    city: str,
) -> None:
    """Merge normalized connector data into the merged cells dict.

    Stores city-level data under _city_level_{domain} keys for provenance
    and data quality tracking. These are consumed by the DataFreshnessPanel
    and evidence synthesis, not by the grid overlay (which uses city YAML
    baselines for absolute cell values).
    """
    for entry in normalized:
        domain = entry.get("domain", "unknown")
        key = f"_city_level_{domain}"
        merged[key] = {k: v for k, v in entry.items() if k != "domain" and isinstance(v, (int, float))}
