from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from engine.models import GridState
from engine.secondary_loop import compute_aggregate_metrics


def to_frame(state: GridState, month: int) -> dict:
    k0_total = np.sum(state.baselines["K"], axis=1)
    kt_total = np.sum(state.K, axis=1)
    total_jobs = state.E_formal + state.E_informal
    deltas = np.divide(kt_total - k0_total, k0_total, out=np.zeros_like(kt_total), where=k0_total > 0)
    deltas = np.clip(deltas, -1.0, 1.0)

    # Vectorized visual cue assignment
    cues = np.full(state.n_cells, "stable", dtype=object)
    cues[deltas > 0.08] = "growth"
    cues[deltas < -0.08] = "stress"
    cues[(deltas >= -0.08) & (deltas <= 0.08) & (state.F > 0.65)] = "flood-risk"

    # Pre-compute shared proof driver string once
    drivers = ", ".join(state.active_effects[:3])

    # Vectorized rounding
    kt_round = np.round(kt_total, 4)
    deltas_round = np.round(deltas, 4)
    e_formal_round = np.round(state.E_formal, 2)
    e_informal_round = np.round(state.E_informal, 2)
    r_round = np.round(state.R, 4)
    t_round = np.round(state.T, 4)
    h_round = np.round(state.H, 4)
    f_round = np.round(state.F, 4)
    m_round = np.round(state.M, 4)

    cells = [
        {
            "h3Index": state.h3_indices[i],
            "economicActivity": float(kt_round[i]),
            "delta": float(deltas_round[i]),
            "jobDensity": float(e_formal_round[i]),
            "jobDensityInformal": float(e_informal_round[i]),
            "realEstateIndex": float(r_round[i]),
            "congestion": float(t_round[i]),
            "housingAffordability": float(h_round[i]),
            "floodRisk": float(f_round[i]),
            "migrationPressure": float(m_round[i]),
            "visualCue": str(cues[i]),
            "proof": (
                f"\\Delta K {(deltas[i] * 100):+.1f}%; "
                f"jobs {total_jobs[i]:,.0f}; "
                f"R={state.R[i]:.2f}, T={state.T[i]:.2f}; "
                f"drivers: {drivers}"
            ),
        }
        for i in range(state.n_cells)
    ]

    year = 2026 + (month - 1) // 12
    m = ((month - 1) % 12) + 1
    return {
        "month": month,
        "timestamp": datetime(year=year, month=m, day=1, tzinfo=timezone.utc).isoformat(),
        "cells": cells,
        "metrics": compute_aggregate_metrics(state),
        "activeLoop": " -> ".join(state.active_effects[:4]) if state.active_effects else "baseline",
        "proof": {
            "formula": "\\Delta K_{sector} = \\text{monthly\\_rate} \\times \\text{sector\\_weight} \\times K; cascading R/T/H/M updates are deterministic vector operations.",
            "dataQuality": "estimated proxy baselines from city YAML, H3 geometry, sector weights, and deterministic spatial decay.",
            "cellCount": state.n_cells,
            "activeEffects": state.active_effects,
        },
    }
