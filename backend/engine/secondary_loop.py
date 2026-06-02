from __future__ import annotations

import numpy as np

from engine.models import GridState, SimulationParams
from engine.provenance import SECONDARY_CASCADE_DECAY, MONSOON_DECAY

# Policy alias mapping: city-specific policy names → engine policy names
POLICY_ALIASES: dict[str, str] = {
    # RERA variations
    "rera compliance": "RERA Compliance",
    "rera": "RERA Compliance",
    "maharera": "RERA Compliance",
    # PM Awas Yojana variations
    "pm awas yojana": "PM Awas Yojana",
    "pmay": "PM Awas Yojana",
    "pradhan mantri awas yojana": "PM Awas Yojana",
    "sra slum redevelopment": "PM Awas Yojana",
    "slum rehabilitation": "PM Awas Yojana",
    "slum redevelopment": "PM Awas Yojana",
    "affordable housing scheme": "PM Awas Yojana",
    # AMRUT variations
    "amrut": "AMRUT",
    "atal mission for rejuvenation": "AMRUT",
    "urban rejuvenation": "AMRUT",
    # Smart City variations
    "smart city mission": "Smart City Mission",
    "smart city": "Smart City Mission",
    "chandigarh smart city": "Smart City Mission",
    "bengaluru smart city": "Smart City Mission",
    "pune smart city": "Smart City Mission",
    # Transport/metro policies → congestion reduction (AMRUT-like)
    "mumbai metro expansion": "AMRUT",
    "bmrcl metro phase 2": "AMRUT",
    "delhi metro expansion": "AMRUT",
    "chennai metro phase 2": "AMRUT",
    "kolkata metro expansion": "AMRUT",
    # Heritage/conservation → Smart City
    "le corbusier heritage zone": "Smart City Mission",
    "heritage conservation": "Smart City Mission",
}


def _resolve_policy(name: str) -> str | None:
    """Resolve a city-specific policy name to an engine policy name."""
    lower = name.strip().lower()
    return POLICY_ALIASES.get(lower)


def _has_policy(policies_active: list[str], target: str) -> bool:
    """Check if a target policy is active, considering aliases."""
    if target in policies_active:
        return True
    for policy in policies_active:
        if _resolve_policy(policy) == target:
            return True
    return False


def step(state: GridState, params: SimulationParams, month: int) -> GridState:
    delta_k = state.last_delta_k if state.last_delta_k is not None else np.zeros(state.n_cells)
    delta_e = state.last_delta_e if state.last_delta_e is not None else np.zeros(state.n_cells)

    gamma = float(state.constants.get("gamma_realestate", 0.10))
    lambda_r = float(state.constants.get("lambda_realestate_cascade", 2.8))
    delta_congestion = float(state.constants.get("delta_congestion", 0.12))

    # Read policy effect factors from city constants
    rera_dampening = float(state.constants.get("policy_rera_dampening", 0.85))
    pmay_multiplier = float(state.constants.get("policy_pmay_multiplier", 2.5))
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

    if _has_policy(params.policies_active, "RERA Compliance"):
        delta_r *= rera_dampening
        if "RERA volatility dampening" not in state.active_effects:
            state.active_effects.append("RERA volatility dampening")

    if _has_policy(params.policies_active, "PM Awas Yojana"):
        state.H[state.slum_flag] += float(state.constants.get("slum_upgrade_rate", 0.008)) * pmay_multiplier
        state.H = np.clip(state.H, 0.2, 1.8)
        if "PMAY housing upgrade" not in state.active_effects:
            state.active_effects.append("PMAY housing upgrade")

    if _has_policy(params.policies_active, "AMRUT"):
        state.H += amrut_housing
        state.T += amrut_congestion
        if "AMRUT services improvement" not in state.active_effects:
            state.active_effects.append("AMRUT services improvement")

    if _has_policy(params.policies_active, "Smart City Mission"):
        state.T += smart_city_congestion
        if "Smart City operations" not in state.active_effects:
            state.active_effects.append("Smart City operations")

    # Housing/migration coefficients from city constants
    housing_xi = float(state.constants.get("housing_xi", 0.08))
    migration_eta = float(state.constants.get("migration_eta", 0.05))
    flood_k_impact = float(state.constants.get("flood_k_impact", 0.18))
    flood_t_impact = float(state.constants.get("flood_t_impact", 0.025))

    if month in params.city_config.monsoon_season:
        flood_impact = float(state.constants.get("flood_impact", 0.20)) / max(len(params.city_config.monsoon_season), 1)
        state.K *= (1.0 - flood_impact * state.F[:, None] * flood_k_impact)
        state.T += float(state.constants.get("flood_congestion_bonus", 0.2)) * state.F * flood_t_impact
        if "monsoon flood pressure" not in state.active_effects:
            state.active_effects.append("monsoon flood pressure")

    state.R = np.clip(state.R + delta_r, 0.0, 2.0)
    capacity = np.maximum(state.E_formal + state.E_informal, 1.0)
    state.T = np.clip(state.T + delta_congestion * delta_e / capacity, 0.0, 1.0)
    state.H = np.clip(state.H - np.maximum(delta_r, 0.0) * housing_xi, 0.2, 1.8)
    baselines_K = np.sum(state.baselines.get("K", state.K))
    current_K = np.sum(state.K)
    migration_pull = np.clip(current_K / max(baselines_K, 1.0) - 0.5, 0, 1)
    affordability_push = np.clip(1.0 - state.H, 0, 1)
    state.M = np.clip(
        state.M + migration_eta * (migration_pull + affordability_push) * 0.5 - np.maximum(delta_e, 0.0) / capacity * 0.01,
        0.0,
        1.0,
    )
    state.migration_balance = float(np.mean(state.M) - np.mean(state.baselines.get("M", state.M)))

    # Confidence propagation — secondary effects are less certain than primary
    if state.confidence_R is not None:
        state.confidence_R = np.clip(state.confidence_R * SECONDARY_CASCADE_DECAY, 0.1, 1.0)
    if state.confidence_T is not None:
        state.confidence_T = np.clip(state.confidence_T * SECONDARY_CASCADE_DECAY, 0.1, 1.0)
    if state.confidence_H is not None:
        state.confidence_H = np.clip(state.confidence_H * SECONDARY_CASCADE_DECAY, 0.1, 1.0)
    if state.confidence_M is not None:
        state.confidence_M = np.clip(state.confidence_M * SECONDARY_CASCADE_DECAY, 0.1, 1.0)
    # Monsoon further reduces confidence
    if month in params.city_config.monsoon_season and state.confidence_F is not None:
        state.confidence_F = np.clip(state.confidence_F * MONSOON_DECAY, 0.1, 1.0)

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
    flood_disruption = float(np.mean(state.F * np.abs(gdp_delta)))

    return {
        "gdpDelta": round(float(gdp_delta), 4),
        "unemploymentRate": round(float(np.clip(unemployment, 0.0, 1.0)), 4),
        "realEstateIndex": round(float(np.mean(state.R)), 4),
        "transitCongestion": round(float(np.mean(state.T)), 4),
        "informalEmployment": round(float(informal_share), 4),
        "housingAffordability": round(float(np.mean(state.H)), 4),
        "floodDisruption": round(flood_disruption, 4),
        "migrationBalance": round(float(state.migration_balance), 4),
    }
