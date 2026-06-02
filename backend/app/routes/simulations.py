import csv
import io
from uuid import UUID
from collections import Counter

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.db import DatabaseClient, get_db

router = APIRouter()

@router.post("/simulations/compare")
async def compare_simulations(
    body: dict = Body(..., description="JSON body with simulation_id_a and simulation_id_b"),
    db: DatabaseClient = Depends(get_db),
):
    """Compare two simulations side-by-side: key metrics diff, verdict, sectors."""
    id_a = body.get("simulation_id_a")
    id_b = body.get("simulation_id_b")
    if not id_a or not id_b:
        raise HTTPException(status_code=400, detail="Both simulation_id_a and simulation_id_b are required")

    try:
        uuid_a = UUID(str(id_a))
        uuid_b = UUID(str(id_b))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    sim_a = await db.get_simulation(uuid_a)
    sim_b = await db.get_simulation(uuid_b)
    if sim_a is None:
        raise HTTPException(status_code=404, detail=f"Simulation {id_a} not found")
    if sim_b is None:
        raise HTTPException(status_code=404, detail=f"Simulation {id_b} not found")

    km_a = sim_a.get("result_summary", {}).get("key_metrics", {})
    km_b = sim_b.get("result_summary", {}).get("key_metrics", {})
    all_metric_keys = sorted(set(list(km_a.keys()) + list(km_b.keys())))

    metrics_diff = {}
    for key in all_metric_keys:
        val_a = km_a.get(key)
        val_b = km_b.get(key)
        diff = None
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            diff = round(val_b - val_a, 6)
        metrics_diff[key] = {"a": val_a, "b": val_b, "diff": diff}

    verdict_a = sim_a.get("result_summary", {}).get("verdict")
    verdict_b = sim_b.get("result_summary", {}).get("verdict")

    # Sector comparison from result_summary if present
    sectors_a = sim_a.get("result_summary", {}).get("sector_deltas", {})
    sectors_b = sim_b.get("result_summary", {}).get("sector_deltas", {})
    all_sector_keys = sorted(set(list(sectors_a.keys()) + list(sectors_b.keys())))
    sector_comparison = {}
    for key in all_sector_keys:
        val_a = sectors_a.get(key)
        val_b = sectors_b.get(key)
        diff = None
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            diff = round(val_b - val_a, 6)
        sector_comparison[key] = {"a": val_a, "b": val_b, "diff": diff}

    return {
        "success": True,
        "data": {
            "simulation_a": {"id": str(id_a), "city": sim_a.get("region_id"), "verdict": verdict_a},
            "simulation_b": {"id": str(id_b), "city": sim_b.get("region_id"), "verdict": verdict_b},
            "metrics_diff": metrics_diff,
            "sector_comparison": sector_comparison,
            "verdict": {"a": verdict_a, "b": verdict_b, "same": verdict_a == verdict_b},
        },
        "error": None,
        "meta": {},
    }


@router.get("/simulations/stats")
async def simulation_stats(db: DatabaseClient = Depends(get_db)):
    """Aggregate statistics across all simulations."""
    sims = await db.list_all_simulations_unpaged()
    total = len(sims)
    if total == 0:
        return {
            "success": True,
            "data": {"total_simulations": 0, "avg_gdp_delta": None, "most_common_city": None, "most_common_sectors": []},
            "error": None,
            "meta": {},
        }

    gdp_deltas: list[float] = []
    city_counter: Counter = Counter()
    sector_counter: Counter = Counter()

    for sim in sims:
        city = sim.get("region_id") or sim.get("params", {}).get("city")
        if city:
            city_counter[city] += 1

        km = sim.get("result_summary", {}).get("key_metrics", {})
        gdp_val = km.get("gdp_delta") or km.get("gdp_growth") or km.get("gdp")
        if isinstance(gdp_val, (int, float)):
            gdp_deltas.append(float(gdp_val))

        sector_deltas = sim.get("result_summary", {}).get("sector_deltas", {})
        for sector in sector_deltas:
            sector_counter[sector] += 1

    avg_gdp = round(sum(gdp_deltas) / len(gdp_deltas), 4) if gdp_deltas else None
    most_common_city = city_counter.most_common(1)[0][0] if city_counter else None
    most_common_sectors = [s for s, _ in sector_counter.most_common(5)] if sector_counter else []

    return {
        "success": True,
        "data": {
            "total_simulations": total,
            "avg_gdp_delta": avg_gdp,
            "most_common_city": most_common_city,
            "most_common_sectors": most_common_sectors,
        },
        "error": None,
        "meta": {},
    }


@router.post("/simulations/{simulation_id}/notes")
async def add_simulation_note(
    simulation_id: UUID,
    body: dict = Body(..., description="JSON body with 'note' field"),
    db: DatabaseClient = Depends(get_db),
):
    """Add a note/annotation to a simulation."""
    note = body.get("note")
    if not note or not isinstance(note, str) or not note.strip():
        raise HTTPException(status_code=400, detail="'note' field is required and must be a non-empty string")

    # Verify simulation exists
    sim = await db.get_simulation(simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    added = await db.add_note(simulation_id, note.strip())
    if not added:
        raise HTTPException(status_code=500, detail="Failed to add note")

    return {
        "success": True,
        "data": {"simulation_id": str(simulation_id), "note": note.strip()},
        "error": None,
        "meta": {},
    }


@router.get("/simulations/{simulation_id}/notes")
async def get_simulation_notes(simulation_id: UUID, db: DatabaseClient = Depends(get_db)):
    """Retrieve all notes for a simulation."""
    sim = await db.get_simulation(simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    notes = await db.get_notes(simulation_id)
    return {
        "success": True,
        "data": {"simulation_id": str(simulation_id), "notes": notes},
        "error": None,
        "meta": {},
    }


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
