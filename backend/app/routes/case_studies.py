from fastapi import APIRouter, Depends, Query

from app.db import DatabaseClient, get_db

router = APIRouter()


@router.get("/case-studies")
async def list_case_studies(
    city: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    policy: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: DatabaseClient = Depends(get_db),
):
    studies = await db.list_case_studies(city=city, sector=sector, policy=policy)
    total = len(studies)
    start = (page - 1) * per_page
    end = start + per_page
    studies = studies[start:end]
    return {
        "success": True,
        "data": studies,
        "error": None,
        "meta": {"count": len(studies), "total": total, "page": page, "perPage": per_page},
    }
