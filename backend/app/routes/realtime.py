from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db import DatabaseClient, get_db
from app.realtime import run_ingestion_cycle, snapshot_quality

router = APIRouter()


@router.get("/data-sources")
async def list_data_sources(
    city: str = Query(default="bengaluru"),
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
    city: str = Query(default="bengaluru"),
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
    city: str = Query(default="bengaluru"),
    db: DatabaseClient = Depends(get_db),
):
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
    city: str = Query(default="bengaluru"),
    db: DatabaseClient = Depends(get_db),
):
    quality = await db.get_snapshot_quality(snapshot_id, city=city)
    return {
        "success": True,
        "data": quality.model_dump(mode="json"),
        "error": None,
        "meta": {"city": city, "snapshotId": snapshot_id},
    }
