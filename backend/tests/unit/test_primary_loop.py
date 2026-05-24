import numpy as np

from engine import primary_loop
from engine.config import CityConfig
from engine.grid import GridFactory
from engine.models import SECTOR_INDEX, SimulationParams


def _state(delta=25.0):
    cfg = CityConfig.load("hyderabad")
    params = SimulationParams(
        city="hyderabad",
        sector_deltas={"manufacturing": delta},
        policies_active=["Make in India"],
        public_works_zone=None,
        horizon_months=24,
        city_config=cfg,
    )
    return GridFactory.initialize(cfg.get_boundary_polygon(), params), params


def test_sector_shock_updates_only_bounded_arrays():
    state, params = _state(40.0)
    before = state.K.copy()
    updated = primary_loop.step(state, params, month=1)

    assert np.all(np.isfinite(updated.K))
    assert np.all(updated.K >= 0)
    assert np.sum(updated.K[:, SECTOR_INDEX["manufacturing"]]) > np.sum(before[:, SECTOR_INDEX["manufacturing"]])
    assert updated.last_delta_k is not None


def test_negative_sector_shock_does_not_create_nan():
    state, params = _state(-60.0)
    updated = primary_loop.step(state, params, month=1)

    assert np.all(np.isfinite(updated.K))
    assert np.all(np.isfinite(updated.E_formal))
