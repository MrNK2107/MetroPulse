import numpy as np

from engine import primary_loop, secondary_loop
from engine.config import CityConfig
from engine.grid import GridFactory
from engine.models import SimulationParams


def test_secondary_loop_metrics_are_bounded():
    cfg = CityConfig.load("mumbai")
    params = SimulationParams(
        city="mumbai",
        sector_deltas={"real_estate": 35},
        policies_active=["RERA Compliance", "AMRUT"],
        public_works_zone=None,
        horizon_months=24,
        city_config=cfg,
    )
    state = GridFactory.initialize(cfg.get_boundary_polygon(), params)
    state = primary_loop.step(state, params, month=1)
    state = secondary_loop.step(state, params, month=1)
    metrics = secondary_loop.compute_aggregate_metrics(state)

    assert 0 <= metrics["unemploymentRate"] <= 1
    assert 0 <= metrics["transitCongestion"] <= 1
    assert metrics["housingAffordability"] > 0
    assert np.all(np.isfinite(state.R))
