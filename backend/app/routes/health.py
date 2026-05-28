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
