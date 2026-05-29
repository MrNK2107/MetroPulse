"""Tests for the provenance system."""

import numpy as np

from engine.provenance import (
    DataOrigin,
    DEFAULT_ORIGINS,
    ORIGIN_CONFIDENCE,
    PRIMARY_LOOP_DECAY,
    SECONDARY_CASCADE_DECAY,
    SECONDARY_UPDATE_DECAY,
)


def test_data_origin_enum():
    assert DataOrigin.REAL.value == "real"
    assert DataOrigin.ESTIMATED.value == "estimated"
    assert DataOrigin.SYNTHETIC.value == "synthetic"


def test_origin_confidence():
    assert ORIGIN_CONFIDENCE[DataOrigin.REAL] > ORIGIN_CONFIDENCE[DataOrigin.ESTIMATED]
    assert ORIGIN_CONFIDENCE[DataOrigin.ESTIMATED] > ORIGIN_CONFIDENCE[DataOrigin.SYNTHETIC]


def test_default_origins():
    assert DEFAULT_ORIGINS["K"] == DataOrigin.SYNTHETIC
    assert DEFAULT_ORIGINS["E_formal"] == DataOrigin.ESTIMATED
    assert DEFAULT_ORIGINS["F"] == DataOrigin.SYNTHETIC


def test_confidence_decay_factors():
    assert 0 < SECONDARY_CASCADE_DECAY <= SECONDARY_UPDATE_DECAY < PRIMARY_LOOP_DECAY < 1.0


def test_grid_state_has_confidence_fields():
    from engine.models import GridState

    state = GridState(
        h3_indices=["a", "b"],
        cell_centers=np.array([[0.0, 0.0], [1.0, 1.0]]),
        K=np.ones((2, 7)),
        E_formal=np.ones(2),
        E_informal=np.ones(2),
        R=np.ones(2),
        T=np.ones(2),
        H=np.ones(2),
        F=np.ones(2),
        M=np.ones(2),
        baselines={},
        slum_flag=np.zeros(2, dtype=bool),
        sector_weights=np.ones(7) / 7,
        constants={},
        city_center=(0.0, 0.0),
    )
    # Default is None (not initialized until grid.py sets them)
    assert state.confidence_K is None
    assert state.data_origins == {}


def test_grid_initializes_confidence():
    from engine.config import CityConfig
    from engine.grid import GridFactory
    from engine.models import SimulationParams

    cfg = CityConfig.load("hyderabad")
    params = SimulationParams(
        city="hyderabad",
        sector_deltas={"it_ites": 20.0},
        policies_active=[],
        public_works_zone=None,
        horizon_months=24,
        city_config=cfg,
    )
    boundary = cfg.get_boundary_polygon()
    state = GridFactory.initialize(boundary, params)

    assert state.confidence_K is not None
    assert state.confidence_R is not None
    assert state.confidence_F is not None
    assert len(state.confidence_K) == state.n_cells
    assert state.data_origins["K"] == "synthetic"
    assert state.data_origins["F"] == "synthetic"
    assert all(0 < c <= 1.0 for c in state.confidence_K)
