import asyncio

import pytest

from engine.runner import run_simulation, SimulationTimeoutError
from engine.scenario_parser import build_params, parse_scenario


@pytest.mark.asyncio
async def test_simulation_emits_correct_frame_count():
    parsed = await parse_scenario("Hyderabad pharma FDI drops 40% for 6 months")
    params = build_params(parsed)
    params.horizon_months = 6

    deadline = asyncio.get_running_loop().time() + 30
    frames = []
    async for frame in run_simulation(params, params.city_config.get_boundary_polygon(), db=None, deadline=deadline):
        frames.append(frame)

    assert len(frames) == 6
    assert frames[0]["month"] == 1
    assert frames[-1]["month"] == 6
    assert "proof" in frames[-1]


@pytest.mark.asyncio
async def test_vague_valid_prompt_runs_with_defaults():
    parsed = await parse_scenario("Bengaluru tech boom")
    params = build_params(parsed)

    assert params.horizon_months == 24
    frame_count = 0
    deadline = asyncio.get_running_loop().time() + 30
    async for _ in run_simulation(params, params.city_config.get_boundary_polygon(), db=None, deadline=deadline):
        frame_count += 1

    assert frame_count == 24
