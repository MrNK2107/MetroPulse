import pytest
import json
from unittest.mock import AsyncMock, patch

from engine.runner import run_simulation, set_deadline
from engine.models import SimulationParams, FDIParams


@pytest.mark.asyncio
async def test_simulation_emits_correct_frame_count():
    params = SimulationParams(
        fdi=FDIParams(tech=10, manufacturing=0, realEstate=0),
        horizonMonths=6,
    )
    region_boundary = {
        "type": "Polygon",
        "coordinates": [[
            [-74.025, 40.700],
            [-73.925, 40.700],
            [-73.925, 40.795],
            [-74.025, 40.795],
            [-74.025, 40.700],
        ]],
    }

    set_deadline(5000)
    frames = []
    insights = []

    async for msg in run_simulation(params, region_boundary, db=None):
        if "type" in msg and msg["type"] == "INSIGHT":
            insights.append(msg)
        else:
            frames.append(msg)

    assert len(frames) == 6
    for i, frame in enumerate(frames):
        assert frame["month"] == i + 1
        assert len(frame["cells"]) > 0
        assert "metrics" in frame

    assert len(insights) == 1
    assert "markdown" in insights[0]


@pytest.mark.asyncio
async def test_simulation_different_horizons():
    for horizon in [6, 12, 24]:
        params = SimulationParams(
            fdi=FDIParams(tech=20, manufacturing=-10, realEstate=5),
            horizonMonths=horizon,
        )
        region_boundary = {
            "type": "Polygon",
            "coordinates": [[
                [-74.025, 40.700],
                [-73.925, 40.700],
                [-73.925, 40.795],
                [-74.025, 40.795],
                [-74.025, 40.700],
            ]],
        }

        set_deadline(5000)
        frame_count = 0
        async for msg in run_simulation(params, region_boundary, db=None):
            if "type" not in msg:
                frame_count += 1

        assert frame_count == horizon, f"Expected {horizon} frames, got {frame_count}"
