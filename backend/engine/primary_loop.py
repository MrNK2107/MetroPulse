from __future__ import annotations

import numpy as np

from engine.grid import public_zone_mask
from engine.models import GridState, SECTOR_INDEX, SECTOR_NAMES, SimulationParams


def step(state: GridState, params: SimulationParams, month: int) -> GridState:
    rates = np.array(
        [float(params.sector_deltas.get(sector, 0.0)) / 100.0 for sector in SECTOR_NAMES],
        dtype=np.float64,
    )
    if params.coefficient_factors:
        factors = np.array(
            [float(params.coefficient_factors.get(sector, 1.0)) for sector in SECTOR_NAMES],
            dtype=np.float64,
        )
        rates = rates * factors
    monthly_rates = rates / max(params.horizon_months, 1)
    alpha = float(state.constants.get("alpha_default", 0.55))
    beta_informal = float(state.constants.get("beta_informal", 0.35))

    # Read policy boost factors from city constants (with sensible defaults)
    di_it_boost = float(state.constants.get("policy_digital_india_it_boost", 0.015))
    mii_mfg_boost = float(state.constants.get("policy_make_in_india_mfg_boost", 0.012))
    sez_multiplier = float(state.constants.get("policy_sez_multiplier", 0.01))
    pw_boost = float(state.constants.get("public_works_boost", 0.018))
    pw_decay = float(state.constants.get("public_works_decay", 0.04))

    # Employment pressure weights per sector (read from city config)
    _default_epw = [0.7, 0.65, 0.5, 0.8, 0.6, 0.45, 0.4]
    epw_raw = state.constants.get("employment_pressure_weights", _default_epw)
    employment_pressure_weights = np.array(epw_raw, dtype=np.float64)

    delta_k = state.K * monthly_rates[None, :] * state.sector_weights[None, :]
    effects: list[str] = []

    if np.any(rates != 0):
        effects.append("sector shock")

    if "Digital India" in params.policies_active:
        delta_k[:, SECTOR_INDEX["it_ites"]] += state.K[:, SECTOR_INDEX["it_ites"]] * di_it_boost
        effects.append("Digital India IT boost")

    if "Make in India" in params.policies_active:
        delta_k[:, SECTOR_INDEX["manufacturing"]] += state.K[:, SECTOR_INDEX["manufacturing"]] * mii_mfg_boost
        effects.append("Make in India manufacturing boost")

    if "SEZ Notification" in params.policies_active and state.zone_flags:
        combined = np.zeros(state.n_cells, dtype=bool)
        for mask in state.zone_flags.values():
            combined |= mask
        if np.any(combined):
            delta_k[combined, :] += state.K[combined, :] * sez_multiplier
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
        boost = pw_boost * np.exp(-dist / max(pw_decay, 0.001))
        delta_k[:, SECTOR_INDEX["real_estate"]] += state.K[:, SECTOR_INDEX["real_estate"]] * boost
        delta_k[:, SECTOR_INDEX["public_admin"]] += state.K[:, SECTOR_INDEX["public_admin"]] * boost
        effects.append("public works distance boost")

    state.K = np.maximum(state.K + delta_k, 0.0)
    total_delta_k = np.sum(delta_k, axis=1)
    sector_employment_pressure = np.dot(delta_k, employment_pressure_weights)
    delta_formal = alpha * sector_employment_pressure
    lag = 0.6 if month > 1 else 0.25
    delta_informal = beta_informal * lag * delta_formal + state.M * 0.002 * np.maximum(state.E_formal, 1.0)

    state.E_formal = np.maximum(state.E_formal + delta_formal, 0.0)
    state.E_informal = np.maximum(state.E_informal + delta_informal, 0.0)
    state.last_delta_k = total_delta_k
    state.last_delta_e = delta_formal + delta_informal
    state.active_effects = effects or ["baseline drift"]

    # Confidence propagation — each step accumulates uncertainty
    from engine.provenance import PRIMARY_LOOP_DECAY
    if state.confidence_K is not None:
        state.confidence_K = np.clip(state.confidence_K * PRIMARY_LOOP_DECAY, 0.1, 1.0)
        if params.coefficient_adjustments:
            coeff_conf = np.mean([
                float(item.get("confidence", 0.35)) if isinstance(item, dict) else 0.35
                for item in params.coefficient_adjustments.values()
            ])
            state.confidence_K = np.maximum(state.confidence_K, min(coeff_conf, 0.75))
            state.data_origins["K"] = "rag_evidence"

    return state
