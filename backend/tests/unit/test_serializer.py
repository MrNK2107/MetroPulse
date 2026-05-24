from engine import primary_loop, secondary_loop, serializer
from engine.config import CityConfig
from engine.grid import GridFactory
from engine.models import SimulationParams


def test_serializer_includes_visual_proof_fields():
    cfg = CityConfig.load("bengaluru")
    params = SimulationParams(
        city="bengaluru",
        sector_deltas={"it_ites": 30},
        policies_active=["Digital India"],
        public_works_zone=None,
        horizon_months=12,
        city_config=cfg,
    )
    state = GridFactory.initialize(cfg.get_boundary_polygon(), params)
    state = primary_loop.step(state, params, month=1)
    state = secondary_loop.step(state, params, month=1)
    frame = serializer.to_frame(state, month=1)

    assert frame["cells"]
    assert "proof" in frame["cells"][0]
    assert "visualCue" in frame["cells"][0]
    assert "proof" in frame
    assert "informalEmployment" in frame["metrics"]
