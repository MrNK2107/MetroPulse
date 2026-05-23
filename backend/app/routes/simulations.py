from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.db import get_db, DatabaseClient

router = APIRouter()


@router.get("/simulations")
async def list_simulations(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: DatabaseClient = Depends(get_db),
):
    simulations = await db.list_simulations(page=page, per_page=per_page)
    return {
        "success": True,
        "data": simulations,
        "error": None,
        "meta": {"page": page, "perPage": per_page},
    }


@router.get("/simulations/{simulation_id}")
async def get_simulation(simulation_id: UUID, db: DatabaseClient = Depends(get_db)):
    simulation = await db.get_simulation(simulation_id)
    if simulation is None:
        return {
            "success": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "Simulation not found"},
            "meta": {},
        }
    return {
        "success": True,
        "data": simulation,
        "error": None,
        "meta": {},
    }
