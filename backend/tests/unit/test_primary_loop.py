import pytest
import numpy as np
from engine.grid import GridState
from engine.models import SimulationParams, FDIParams
from engine.primary_loop import step


def test_zero_fdi_no_change():
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

    K_before = state.K.copy()
    E_before = state.E.copy()

    state = step(state, params)

    np.testing.assert_array_almost_equal(state.K, K_before)
    np.testing.assert_array_almost_equal(state.E, E_before)


def test_positive_tech_fdi():
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

    K_before = state.K.copy()
    state = step(state, params)

    assert np.all(state.K >= K_before)
    assert np.any(state.K > K_before)


def test_negative_fdi():
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
    params = SimulationParams(fdi=FDIParams(tech=0, manufacturing=-50, realEstate=0))
    state = GridState.initialize(boundary, params.model_dump())

    K_before = state.K.copy()
    state = step(state, params)

    assert np.all(state.K <= K_before)


def test_no_nan_or_inf():
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
    params = SimulationParams(fdi=FDIParams(tech=100, manufacturing=100, realEstate=100))
    state = GridState.initialize(boundary, params.model_dump())

    state = step(state, params)

    assert not np.any(np.isnan(state.K))
    assert not np.any(np.isinf(state.K))
    assert not np.any(np.isnan(state.E))
    assert not np.any(np.isinf(state.E))
