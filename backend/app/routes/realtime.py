from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.db import DatabaseClient, get_db
from app.realtime import run_ingestion_cycle, snapshot_quality

router = APIRouter()

# ── In-memory rate limiter for POST /ingest ───────────────────────
_ingest_rate_limit: dict[str, list[float]] = defaultdict(list)
_INGEST_MAX_REQUESTS = 3
_INGEST_WINDOW_SECONDS = 60.0
_INGEST_ENTRY_TTL = 120.0  # purge IP entries older than this
_INGEST_LAST_SEEN: dict[str, float] = {}


@router.get("/data-sources")
async def list_data_sources(
    city: str = Query(..., description="City ID (e.g. bengaluru, mumbai, delhi_ncr)"),
    db: DatabaseClient = Depends(get_db),
):
    sources = await db.list_data_sources(city=city)
    return {
        "success": True,
        "data": sources,
        "error": None,
        "meta": {"city": city},
    }


@router.get("/snapshots/latest")
async def latest_snapshot(
    city: str = Query(..., description="City ID (e.g. bengaluru, mumbai, delhi_ncr)"),
    db: DatabaseClient = Depends(get_db),
):
    snapshot = await db.get_latest_snapshot(city=city)
    quality = snapshot_quality(snapshot)
    data = None
    if snapshot:
        data = {
            "id": snapshot.id,
            "city": snapshot.city,
            "snapshot_at": snapshot.snapshot_at.isoformat(),
            "aggregate_metrics": snapshot.aggregate_metrics,
            "source_manifest": snapshot.manifest_for_json(),
            "quality_score": snapshot.quality_score,
            "status": snapshot.status,
        }
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": {"city": city, "quality": quality.model_dump(mode="json")},
    }


@router.post("/ingest")
async def trigger_ingestion(
    request: Request,
    city: str = Query(..., description="City ID (e.g. bengaluru, mumbai, delhi_ncr)"),
    db: DatabaseClient = Depends(get_db),
):
    # ── Rate limit check ─────────────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    # Purge stale IP entries to prevent unbounded memory growth
    stale_ips = [ip for ip, last in _INGEST_LAST_SEEN.items() if now - last > _INGEST_ENTRY_TTL]
    for ip in stale_ips:
        del _ingest_rate_limit[ip]
        del _INGEST_LAST_SEEN[ip]
    _INGEST_LAST_SEEN[client_ip] = now
    timestamps = _ingest_rate_limit[client_ip]
    # Evict expired entries
    _ingest_rate_limit[client_ip] = [t for t in timestamps if now - t < _INGEST_WINDOW_SECONDS]
    timestamps = _ingest_rate_limit[client_ip]
    if len(timestamps) >= _INGEST_MAX_REQUESTS:
        retry_after = _INGEST_WINDOW_SECONDS - (now - timestamps[0])
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "data": None,
                "error": f"Rate limit exceeded. Max {_INGEST_MAX_REQUESTS} requests per {_INGEST_WINDOW_SECONDS:.0f}s.",
                "meta": {"city": city, "retry_after_seconds": round(retry_after, 1)},
            },
        )
    timestamps.append(now)

    snapshot = await run_ingestion_cycle(db, city)
    return {
        "success": snapshot is not None,
        "data": {
            "snapshot_id": snapshot.id if snapshot else None,
            "status": snapshot.status if snapshot else "no_data",
            "quality_score": snapshot.quality_score if snapshot else 0.0,
        },
        "error": None,
        "meta": {"city": city},
    }


@router.get("/snapshots/{snapshot_id}/quality")
async def snapshot_quality_endpoint(
    snapshot_id: str,
    city: str = Query(..., description="City ID (e.g. bengaluru, mumbai, delhi_ncr)"),
    db: DatabaseClient = Depends(get_db),
):
    quality = await db.get_snapshot_quality(snapshot_id, city=city)
    return {
        "success": True,
        "data": quality.model_dump(mode="json"),
        "error": None,
        "meta": {"city": city, "snapshotId": snapshot_id},
    }
