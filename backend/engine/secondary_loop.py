from __future__ import annotations

import numpy as np

from engine.grid import GridState
from engine.models import SimulationParams

GAMMA: float = 0.15
LAMBDA_R: float = 3.5
DELTA: float = 0.08


def step(state: GridState, params: SimulationParams, delta_K_prev: np.ndarray | None = None) -> GridState:
    if delta_K_prev is None:
        delta_K_prev = np.zeros(state.n_cells, dtype=np.float64)

    delta_R = np.zeros(state.n_cells, dtype=np.float64)
    pairs = state.get_neighbor_distances()

    if len(pairs) > 0:
        pairs_arr = np.array(pairs, dtype=np.float64)
        i_idx = pairs_arr[:, 0].astype(int)
        j_idx = pairs_arr[:, 1].astype(int)
        dists = pairs_arr[:, 2]

        weights = np.exp(-dists / LAMBDA_R)

        for idx in np.unique(i_idx):
            mask = i_idx == idx
            neighbor_j = j_idx[mask]
            neighbor_w = weights[mask]
            delta_K_neighbors = delta_K_prev[neighbor_j]
            delta_R[idx] = GAMMA * np.sum(delta_K_neighbors * neighbor_w)

    state.R = state.R + delta_R
    state.R = np.clip(state.R, 0.0, 2.0)

    capacity = np.full(state.n_cells, 1.0, dtype=np.float64)
    delta_T = DELTA * (delta_K_prev) / capacity
    state.T = state.T + delta_T
    state.T = np.clip(state.T, 0.0, 1.0)

    return state


def compute_aggregate_metrics(state: GridState) -> dict[str, float]:
    K0_sum = np.sum(state.baselines["K"])
    Kt_sum = np.sum(state.K)
    gdp_delta = (Kt_sum - K0_sum) / K0_sum if K0_sum > 0 else 0.0

    E0_sum = np.sum(state.baselines["E"])
    Et_sum = np.sum(state.E)
    baseline_unemployment = float(state.baselines["unemployment_rate"])
    unemployment = 1.0 - (Et_sum / E0_sum) * (1.0 - baseline_unemployment) if E0_sum > 0 else baseline_unemployment
    unemployment = max(0.0, min(1.0, unemployment))

    real_estate_idx = float(np.mean(state.R))
    transit_congestion = float(np.mean(state.T))

    return {
        "gdpDelta": round(gdp_delta, 4),
        "unemploymentRate": round(unemployment, 4),
        "realEstateIndex": round(real_estate_idx, 4),
        "transitCongestion": round(transit_congestion, 4),
    }
