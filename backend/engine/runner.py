from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from engine import primary_loop, secondary_loop, serializer
from engine.grid import GridFactory
from engine.models import SimulationParams

SIMULATION_TIMEOUT_MS = 3000


class SimulationTimeoutError(Exception):
    pass


async def run_simulation(
    params: SimulationParams,
    region_boundary: dict[str, Any],
    db: Any = None,
    deadline: float | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    state = GridFactory.initialize(region_boundary, params)
    last_frame: dict[str, Any] | None = None

    for month in range(1, params.horizon_months + 1):
        if deadline is not None and asyncio.get_running_loop().time() > deadline:
            raise SimulationTimeoutError("Simulation exceeded deadline")

        state = primary_loop.step(state, params, month)
        state = secondary_loop.step(state, params, month)
        last_frame = serializer.to_frame(state, month)
        yield last_frame
        await asyncio.sleep(0)

    if db is not None and last_frame is not None:
        await db.save_simulation(
            region_id=None,
            params=params.to_dict(),
            horizon_months=params.horizon_months,
            result_summary=last_frame["metrics"],
            cell_states=last_frame["cells"],
        )
