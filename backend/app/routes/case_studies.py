from fastapi import APIRouter, Depends, Query

from app.db import DatabaseClient, get_db

router = APIRouter()


@router.get("/case-studies")
async def list_case_studies(
    city: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    policy: str | None = Query(default=None),
    db: DatabaseClient = Depends(get_db),
):
    studies = await db.list_case_studies(city=city, sector=sector, policy=policy)
    return {
        "success": True,
        "data": studies,
        "error": None,
        "meta": {"count": len(studies)},
    }
