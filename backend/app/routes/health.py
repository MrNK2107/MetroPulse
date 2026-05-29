from fastapi import APIRouter, Depends

from app.db import get_db, DatabaseClient

router = APIRouter()


@router.get("/api/health")
async def health_check(db: DatabaseClient = Depends(get_db)):
    db_status = "connected" if db._client else "in_memory_fallback"
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
            "db_status": db_status,
        },
        "error": None,
        "meta": {},
    }


@router.get("/api/health/data")
async def data_health(city: str = "bengaluru", db: DatabaseClient = Depends(get_db)):
    sources = await db.list_data_sources(city=city)
    status = "healthy"
    if any(source["freshness"] in {"stale", "missing"} for source in sources):
        status = "degraded"
    if all(source["freshness"] in {"missing", "demo"} for source in sources):
        status = "demo"
    return {
        "success": True,
        "data": {
            "status": status,
            "city": city,
            "sources": sources,
        },
        "error": None,
        "meta": {},
    }
