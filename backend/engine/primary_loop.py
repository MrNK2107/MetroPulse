from __future__ import annotations

import numpy as np

from engine.grid import public_zone_mask
from engine.models import GridState, SECTOR_INDEX, SECTOR_NAMES, SimulationParams


def step(state: GridState, params: SimulationParams, month: int) -> GridState:
    rates = np.array(
        [float(params.sector_deltas.get(sector, 0.0)) / 100.0 for sector in SECTOR_NAMES],
        dtype=np.float64,
    )
    monthly_rates = rates / max(params.horizon_months, 1)
    alpha = float(state.constants.get("alpha_default", 0.55))
    beta_informal = float(state.constants.get("beta_informal", 0.35))

    delta_k = state.K * monthly_rates[None, :] * state.sector_weights[None, :]
    effects: list[str] = []

    if np.any(rates != 0):
        effects.append("sector shock")

    if "Digital India" in params.policies_active:
        delta_k[:, SECTOR_INDEX["it_ites"]] += state.K[:, SECTOR_INDEX["it_ites"]] * 0.015
        effects.append("Digital India IT boost")

    if "Make in India" in params.policies_active:
        delta_k[:, SECTOR_INDEX["manufacturing"]] += state.K[:, SECTOR_INDEX["manufacturing"]] * 0.012
        effects.append("Make in India manufacturing boost")

    if "SEZ Notification" in params.policies_active and state.zone_flags:
        combined = np.zeros(state.n_cells, dtype=bool)
        for mask in state.zone_flags.values():
            combined |= mask
        if np.any(combined):
            delta_k[combined, :] += state.K[combined, :] * 0.01
            effects.append("SEZ zone multiplier")

    public_mask = public_zone_mask(state, params.public_works_zone)
    if np.any(public_mask):
        # Cache the distance computation keyed by the public mask hash
        mask_key = hash(public_mask.tobytes())
        if mask_key not in state.public_dist_cache:
            state.public_dist_cache[mask_key] = np.min(
                np.linalg.norm(
                    state.cell_centers[:, None, :] - state.cell_centers[public_mask][None, :, :],
                    axis=2,
                ),
                axis=1,
            )
        dist = state.public_dist_cache[mask_key]
        boost = 0.018 * np.exp(-dist / 0.04)
        delta_k[:, SECTOR_INDEX["real_estate"]] += state.K[:, SECTOR_INDEX["real_estate"]] * boost
        delta_k[:, SECTOR_INDEX["public_admin"]] += state.K[:, SECTOR_INDEX["public_admin"]] * boost
        effects.append("public works distance boost")

    state.K = np.maximum(state.K + delta_k, 0.0)
    total_delta_k = np.sum(delta_k, axis=1)
    sector_employment_pressure = np.dot(delta_k, np.array([0.7, 0.65, 0.5, 0.8, 0.6, 0.45, 0.4]))
    delta_formal = alpha * sector_employment_pressure
    lag = 0.6 if month > 1 else 0.25
    delta_informal = beta_informal * lag * delta_formal + state.M * 0.002 * np.maximum(state.E_formal, 1.0)

    state.E_formal = np.maximum(state.E_formal + delta_formal, 0.0)
    state.E_informal = np.maximum(state.E_informal + delta_informal, 0.0)
    state.last_delta_k = total_delta_k
    state.last_delta_e = delta_formal + delta_informal
    state.active_effects = effects or ["baseline drift"]
    return state
