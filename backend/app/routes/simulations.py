import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.db import DatabaseClient, get_db

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


@router.get("/simulations/{simulation_id}/export")
async def export_simulation(
    simulation_id: UUID,
    format: str = Query(default="json", pattern="^(json|csv)$", description="Export format: json or csv"),
    db: DatabaseClient = Depends(get_db),
):
    """Export simulation data in JSON or CSV format."""
    simulation = await db.get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if format == "csv":
        cell_states = simulation.get("cell_states", [])
        if not cell_states:
            raise HTTPException(status_code=400, detail="No cell_states data to export")

        # Flatten cell_states into rows
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ["month", "h3Index", "gdp", "unemployment", "realEstateIdx", "transitLoad"]
        writer.writerow(headers)

        # Write rows
        for state in cell_states:
            month = state.get("month", "")
            cells = state.get("cells", {})
            for h3_index, metrics in cells.items():
                writer.writerow([
                    month,
                    h3_index,
                    metrics.get("gdp", ""),
                    metrics.get("unemployment", ""),
                    metrics.get("realEstateIdx", ""),
                    metrics.get("transitLoad", ""),
                ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=simulation_{simulation_id}.csv"},
        )
    else:
        # JSON export — return full data
        return JSONResponse(
            content={
                "success": True,
                "data": simulation,
                "error": None,
                "meta": {"format": "json"},
            },
            media_type="application/json",
        )


@router.get("/simulations/{simulation_id}/summary")
async def get_simulation_summary(simulation_id: UUID, db: DatabaseClient = Depends(get_db)):
    """Lightweight simulation summary without large cell_states data."""
    simulation = await db.get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Extract only summary fields, excluding cell_states
    summary = {
        "id": simulation.get("id"),
        "city": simulation.get("region_id") or simulation.get("params", {}).get("city"),
        "scenario": simulation.get("params", {}).get("scenario"),
        "horizon": simulation.get("horizon_months"),
        "verdict": simulation.get("result_summary", {}).get("verdict"),
        "key_metrics": simulation.get("result_summary", {}).get("key_metrics", {}),
        "created_at": simulation.get("created_at"),
    }

    return {
        "success": True,
        "data": summary,
        "error": None,
        "meta": {},
    }
