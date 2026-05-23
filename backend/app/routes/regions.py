from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db, DatabaseClient

router = APIRouter()


@router.get("/regions")
async def list_regions(db: DatabaseClient = Depends(get_db)):
    regions = await db.list_regions()
    return {
        "success": True,
        "data": regions,
        "error": None,
        "meta": {},
    }


@router.get("/regions/{region_id}/baseline")
async def get_region_baseline(region_id: UUID, db: DatabaseClient = Depends(get_db)):
    baseline = await db.get_baseline(region_id)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return {
        "success": True,
        "data": baseline,
        "error": None,
        "meta": {},
    }
