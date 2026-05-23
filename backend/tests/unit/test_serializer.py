import pytest
import numpy as np
from engine.grid import GridState
from engine.serializer import to_frame


def test_to_frame_structure():
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

    frame = to_frame(state, month=3)

    assert frame["month"] == 3
    assert "timestamp" in frame
    assert "cells" in frame
    assert "metrics" in frame
    assert len(frame["cells"]) == state.n_cells

    cell = frame["cells"][0]
    assert "h3Index" in cell
    assert "economicActivity" in cell
    assert "delta" in cell
    assert "jobDensity" in cell
    assert "realEstateIndex" in cell
    assert "congestion" in cell

    metrics = frame["metrics"]
    assert "gdpDelta" in metrics
    assert "unemploymentRate" in metrics
    assert "realEstateIndex" in metrics
    assert "transitCongestion" in metrics


def test_to_frame_delta_bounds():
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

    state.K = state.K * 3
    frame = to_frame(state, month=1)

    for cell in frame["cells"]:
        assert -1.0 <= cell["delta"] <= 1.0
