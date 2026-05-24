from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from engine.grid import GridState
from engine.models import SimulationParams
from engine import primary_loop, secondary_loop, serializer, tertiary_loop


SIMULATION_TIMEOUT_MS = 3000


class SimulationTimeoutError(Exception):
    pass


_deadline: float | None = None


def set_deadline(timeout_ms: int = SIMULATION_TIMEOUT_MS) -> None:
    global _deadline
    _deadline = asyncio.get_running_loop().time() + timeout_ms / 1000.0


async def run_simulation(
    params: SimulationParams,
    region_boundary: dict[str, Any],
    db: Any = None,
) -> AsyncGenerator[dict[str, Any], None]:
    state = GridState.initialize(region_boundary, params.model_dump())

    last_frame: dict[str, Any] | None = None

    for month in range(1, params.horizonMonths + 1):
        if _deadline is not None and asyncio.get_running_loop().time() > _deadline:
            raise SimulationTimeoutError("Simulation exceeded deadline")

        delta_K_before = state.K.copy()

        state = primary_loop.step(state, params)
        delta_K_step = state.K - delta_K_before
        state = secondary_loop.step(state, params, delta_K_prev=delta_K_step)

        last_frame = serializer.to_frame(state, month)
        yield last_frame

    if db is not None and last_frame is not None:
        try:
            final_metrics = secondary_loop.compute_aggregate_metrics(state)
            await db.save_simulation(
                region_id=None,
                params=params.model_dump(),
                horizon_months=params.horizonMonths,
                result_summary=final_metrics,
                cell_states=last_frame["cells"],
            )
        except Exception:
            pass

    insight = await tertiary_loop.synthesize(params, state, db=db)
    yield {"type": "INSIGHT", "markdown": insight}
