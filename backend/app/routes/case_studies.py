from fastapi import APIRouter, Depends, Query

from app.db import DatabaseClient, get_db

router = APIRouter()


@router.get("/case-studies")
async def list_case_studies(
    city: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    policy: str | None = Query(default=None),
    year_from: int | None = Query(default=None, ge=1900, le=2100, description="Filter studies from this year (inclusive)"),
    year_to: int | None = Query(default=None, ge=1900, le=2100, description="Filter studies up to this year (inclusive)"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: DatabaseClient = Depends(get_db),
):
    studies = await db.list_case_studies(city=city, sector=sector, policy=policy)

    # Apply year range filters
    if year_from is not None:
        studies = [s for s in studies if s.get("year", 0) >= year_from]
    if year_to is not None:
        studies = [s for s in studies if s.get("year", 0) <= year_to]

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
