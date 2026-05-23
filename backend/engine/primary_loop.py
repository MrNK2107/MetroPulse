from __future__ import annotations

import numpy as np

from engine.grid import GridState
from engine.models import SimulationParams

ALPHA: float = 0.6
BETA: float = 0.3
LAMBDA: float = 2.0

SECTOR_WEIGHTS: dict[str, float] = {
    "tech": 0.4,
    "manufacturing": 0.35,
    "realEstate": 0.25,
}


def step(state: GridState, params: SimulationParams) -> GridState:
    delta_K = np.zeros(state.n_cells, dtype=np.float64)

    sector_map = {
        "tech": params.fdi.tech,
        "manufacturing": params.fdi.manufacturing,
        "realEstate": params.fdi.realEstate,
    }

    for sector, rate in sector_map.items():
        if rate == 0.0:
            continue
        fdi_rate = rate / 100.0
        weight = SECTOR_WEIGHTS[sector]
        delta_K += fdi_rate * weight * state.K

    if params.publicWorksZone is not None:
        zone_indices = state.get_zone_cells(params.publicWorksZone)
        zone_idx_set = set(
            i for i, idx in enumerate(state.h3_indices) if idx in zone_indices
        )

        if zone_idx_set:
            zone_centers = [
                (i, __import__("h3").h3_to_geo(state.h3_indices[i]))
                for i in zone_idx_set
            ]
            if zone_centers:
                centroid_lat = np.mean([c[1][0] for c in zone_centers])
                centroid_lon = np.mean([c[1][1] for c in zone_centers])

                for i in range(state.n_cells):
                    lat, lon = __import__("h3").h3_to_geo(state.h3_indices[i])
                    dlat = np.radians(lat - centroid_lat)
                    dlon = np.radians(lon - centroid_lon)
                    a = (
                        np.sin(dlat / 2) ** 2
                        + np.cos(np.radians(centroid_lat))
                        * np.cos(np.radians(lat))
                        * np.sin(dlon / 2) ** 2
                    )
                    d = 6371.0 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
                    boost = BETA * np.exp(-d / LAMBDA)
                    delta_K[i] += boost

    state.K = state.K + delta_K

    employment_elasticity = np.full(state.n_cells, 1.0, dtype=np.float64)
    delta_E = ALPHA * delta_K * employment_elasticity
    state.E = state.E + delta_E

    state.E = np.maximum(state.E, 0.0)
    state.K = np.maximum(state.K, 0.0)

    return state
