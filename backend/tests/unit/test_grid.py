import pytest
import numpy as np
from engine.grid import GridState


def test_grid_initialization():
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
    params = {"fdi": {"tech": 0, "manufacturing": 0, "realEstate": 0}}
    state = GridState.initialize(boundary, params)

    assert state.n_cells > 0
    assert len(state.h3_indices) == state.n_cells
    assert state.E.shape == (state.n_cells,)
    assert state.K.shape == (state.n_cells,)
    assert state.R.shape == (state.n_cells,)
    assert state.T.shape == (state.n_cells,)
    assert np.all(state.E >= 0)
    assert np.all(state.K >= 0)
    assert np.all(state.R >= 0)
    assert np.all(state.T >= 0)


def test_grid_initialization_fallback():
    boundary = {"type": "Polygon", "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]}
    params = {"fdi": {"tech": 0, "manufacturing": 0, "realEstate": 0}}
    state = GridState.initialize(boundary, params)

    assert state.n_cells == 1
    assert state.h3_indices[0] == "882a100d2dfffff"


def test_get_zone_cells_point():
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
    state = GridState.initialize(boundary, {"fdi": {"tech": 0, "manufacturing": 0, "realEstate": 0}})

    point = {"type": "Point", "coordinates": [-73.98, 40.75]}
    cells = state.get_zone_cells(point)
    assert len(cells) == 1
    assert isinstance(cells[0], str)


def test_get_zone_cells_polygon():
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
    state = GridState.initialize(boundary, {"fdi": {"tech": 0, "manufacturing": 0, "realEstate": 0}})

    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-73.98, 40.74],
            [-73.96, 40.74],
            [-73.96, 40.76],
            [-73.98, 40.76],
            [-73.98, 40.74],
        ]],
    }
    cells = state.get_zone_cells(polygon)
    assert len(cells) > 0


def test_haversine():
    a = (40.7128, -74.0060)
    b = (40.7580, -73.9855)
    d = GridState._haversine(a, b)
    assert d > 0
    assert d < 10
