import pytest

from engine.runner import run_simulation, set_deadline
from engine.scenario_parser import build_params, parse_scenario


@pytest.mark.asyncio
async def test_simulation_emits_correct_frame_count():
    parsed = await parse_scenario("Hyderabad pharma FDI drops 40% for 6 months")
    params = build_params(parsed)
    params.horizon_months = 6

    set_deadline(5000)
    frames = []
    async for frame in run_simulation(params, params.city_config.get_boundary_polygon(), db=None):
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
    set_deadline(5000)
    async for _ in run_simulation(params, params.city_config.get_boundary_polygon(), db=None):
        frame_count += 1

    assert frame_count == 24
