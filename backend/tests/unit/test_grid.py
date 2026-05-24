import numpy as np

from engine.config import CityConfig
from engine.grid import GridFactory
from engine.models import N_SECTORS, SimulationParams


def test_grid_initializes_india_sector_state():
    cfg = CityConfig.load("hyderabad")
    params = SimulationParams(
        city="hyderabad",
        sector_deltas={"manufacturing": -40},
        policies_active=[],
        public_works_zone=None,
        horizon_months=24,
        city_config=cfg,
    )
    state = GridFactory.initialize(cfg.get_boundary_polygon(), params)

    assert state.n_cells > 0
    assert state.K.shape == (state.n_cells, N_SECTORS)
    assert state.E_formal.shape == (state.n_cells,)
    assert np.all(np.isfinite(state.K))
    assert np.std(np.sum(state.K, axis=1)) > 0


def test_neighbor_pairs_are_precomputed():
    cfg = CityConfig.load("bengaluru")
    params = SimulationParams(
        city="bengaluru",
        sector_deltas={"it_ites": 25},
        policies_active=[],
        public_works_zone=None,
        horizon_months=12,
        city_config=cfg,
    )
    state = GridFactory.initialize(cfg.get_boundary_polygon(), params)

    assert isinstance(state.neighbor_pairs, list)
