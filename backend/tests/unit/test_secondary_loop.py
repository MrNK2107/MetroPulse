import pytest
import numpy as np
from engine.grid import GridState
from engine.models import SimulationParams, FDIParams
from engine.secondary_loop import step, compute_aggregate_metrics


def test_clamping():
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [-74.025, 40.700],
            [-73.925, 40.700],
            [-73.925, 40.795],
            [-74.025, 40.795],
            [-74.025, 40.700],
        ]],
    }
    params = SimulationParams(fdi=FDIParams(tech=0, manufacturing=0, realEstate=0))
    state = GridState.initialize(boundary, params.model_dump())

    state.R = np.full(state.n_cells, 5.0)
    state.T = np.full(state.n_cells, 2.0)

    state = step(state, params)

    assert np.all(state.R <= 2.0)
    assert np.all(state.R >= 0.0)
    assert np.all(state.T <= 1.0)
    assert np.all(state.T >= 0.0)


def test_aggregate_metrics_no_change():
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [-74.025, 40.700],
            [-73.925, 40.700],
            [-73.925, 40.795],
            [-74.025, 40.795],
            [-74.025, 40.700],
        ]],
    }
    params = SimulationParams(fdi=FDIParams(tech=0, manufacturing=0, realEstate=0))
    state = GridState.initialize(boundary, params.model_dump())

    metrics = compute_aggregate_metrics(state)

    assert abs(metrics["gdpDelta"]) < 0.001
    assert 0 <= metrics["unemploymentRate"] <= 1
    assert metrics["realEstateIndex"] > 0
    assert 0 <= metrics["transitCongestion"] <= 1


def test_aggregate_metrics_after_change():
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [-74.025, 40.700],
            [-73.925, 40.700],
            [-73.925, 40.795],
            [-74.025, 40.795],
            [-74.025, 40.700],
        ]],
    }
    params = SimulationParams(fdi=FDIParams(tech=50, manufacturing=0, realEstate=0))
    state = GridState.initialize(boundary, params.model_dump())

    from engine.primary_loop import step as primary_step
    state = primary_step(state, params)
    state = step(state, params)

    metrics = compute_aggregate_metrics(state)

    assert 0 <= metrics["unemploymentRate"] <= 1
    assert metrics["realEstateIndex"] > 0
    assert 0 <= metrics["transitCongestion"] <= 1
