from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db, DatabaseClient

router = APIRouter()


@router.get("/simulations")
async def list_simulations(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    city: str | None = Query(default=None, description="Filter by city ID"),
    db: DatabaseClient = Depends(get_db),
):
    simulations = await db.list_simulations(page=page, per_page=per_page, city=city)
    return {
        "success": True,
        "data": simulations,
        "error": None,
        "meta": {"page": page, "perPage": per_page, "city": city},
    }


@router.get("/simulations/{simulation_id}")
async def get_simulation(simulation_id: UUID, db: DatabaseClient = Depends(get_db)):
    simulation = await db.get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {
        "success": True,
        "data": simulation,
        "error": None,
        "meta": {},
    }


@router.delete("/simulations/{simulation_id}", status_code=204)
async def delete_simulation(simulation_id: UUID, db: DatabaseClient = Depends(get_db)):
    deleted = await db.delete_simulation(simulation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return None
