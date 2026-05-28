from __future__ import annotations

import numpy as np

from engine.models import GridState, SimulationParams


def step(state: GridState, params: SimulationParams, month: int) -> GridState:
    delta_k = state.last_delta_k if state.last_delta_k is not None else np.zeros(state.n_cells)
    delta_e = state.last_delta_e if state.last_delta_e is not None else np.zeros(state.n_cells)

    gamma = float(state.constants.get("gamma_realestate", 0.12))
    lambda_r = float(state.constants.get("lambda_realestate_cascade", 3.2))
    delta_congestion = float(state.constants.get("delta_congestion", 0.10))

    # Read policy effect factors from city constants
    rera_dampening = float(state.constants.get("policy_rera_dampening", 0.88))
    pmay_multiplier = float(state.constants.get("policy_pmay_multiplier", 2.0))
    amrut_housing = float(state.constants.get("policy_amrut_housing", 0.004))
    amrut_congestion = float(state.constants.get("policy_amrut_congestion", -0.002))
    smart_city_congestion = float(state.constants.get("policy_smart_city_congestion", -0.003))

    delta_r = np.zeros(state.n_cells, dtype=np.float64)

    if state.neighbor_i_idx is not None:
        np.add.at(delta_r, state.neighbor_i_idx, gamma * delta_k[state.neighbor_j_idx] * state.neighbor_weights)
    elif state.neighbor_pairs:
        pairs = np.array(state.neighbor_pairs, dtype=np.float64)
        i_idx = pairs[:, 0].astype(int)
        j_idx = pairs[:, 1].astype(int)
        weights = np.exp(-pairs[:, 2] / lambda_r)
        np.add.at(delta_r, i_idx, gamma * delta_k[j_idx] * weights)

    if "RERA Compliance" in params.policies_active:
        delta_r *= rera_dampening
        state.active_effects.append("RERA volatility dampening")

    if "PM Awas Yojana" in params.policies_active:
        state.H[state.slum_flag] += float(state.constants.get("slum_upgrade_rate", 0.012)) * pmay_multiplier
        state.active_effects.append("PMAY housing upgrade")

    if "AMRUT" in params.policies_active:
        state.H += amrut_housing
        state.T += amrut_congestion
        state.active_effects.append("AMRUT services improvement")

    if "Smart City Mission" in params.policies_active:
        state.T += smart_city_congestion
        state.active_effects.append("Smart City operations")

    # Housing/migration coefficients from city constants
    housing_xi = float(state.constants.get("housing_xi", 0.08))
    migration_eta = float(state.constants.get("migration_eta", 0.05))
    flood_k_impact = float(state.constants.get("flood_k_impact", 0.18))
    flood_t_impact = float(state.constants.get("flood_t_impact", 0.025))

    if month in params.city_config.monsoon_season:
        flood_impact = float(state.constants.get("flood_impact", 0.15)) / max(len(params.city_config.monsoon_season), 1)
        state.K *= (1.0 - flood_impact * state.F[:, None] * flood_k_impact)
        state.T += float(state.constants.get("flood_congestion_bonus", 0.2)) * state.F * flood_t_impact
        state.active_effects.append("monsoon flood pressure")

    state.R = np.clip(state.R + delta_r, 0.0, 2.0)
    capacity = np.maximum(state.E_formal + state.E_informal, 1.0)
    state.T = np.clip(state.T + delta_congestion * delta_e / capacity, 0.0, 1.0)
    state.H = np.clip(state.H - np.maximum(delta_r, 0.0) * housing_xi, 0.2, 1.8)
    state.M = np.clip(
        state.M + (1.0 - state.H) * migration_eta - np.maximum(delta_e, 0.0) / capacity * 0.01,
        0.0,
        1.0,
    )
    return state


def compute_aggregate_metrics(state: GridState) -> dict[str, float]:
    k0 = np.sum(state.baselines["K"])
    kt = np.sum(state.K)
    gdp_delta = (kt - k0) / k0 if k0 > 0 else 0.0

    e0 = np.sum(state.baselines["E_formal"]) + np.sum(state.baselines["E_informal"])
    et = np.sum(state.E_formal) + np.sum(state.E_informal)
    baseline_unemployment = float(state.baselines["unemployment_rate"])
    unemployment = baseline_unemployment - ((et - e0) / max(e0, 1.0)) * 0.65

    informal_share = np.sum(state.E_informal) / max(et, 1.0)
    flood_disruption = float(np.mean(state.F * np.maximum(0.0, -gdp_delta)))

    return {
        "gdpDelta": round(float(gdp_delta), 4),
        "unemploymentRate": round(float(np.clip(unemployment, 0.0, 1.0)), 4),
        "realEstateIndex": round(float(np.mean(state.R)), 4),
        "transitCongestion": round(float(np.mean(state.T)), 4),
        "informalEmployment": round(float(informal_share), 4),
        "housingAffordability": round(float(np.mean(state.H)), 4),
        "floodDisruption": round(flood_disruption, 4),
        "migrationBalance": round(float(np.mean(state.M) - np.mean(state.baselines["H"]) * 0.0), 4),
    }
