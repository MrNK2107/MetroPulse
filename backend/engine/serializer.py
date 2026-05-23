from datetime import datetime, timezone

import numpy as np
import h3 as h3_lib

from engine.grid import GridState
from secondary_loop import compute_aggregate_metrics


def to_frame(state: GridState, month: int) -> dict:
    cells: list[dict] = []
    for i in range(state.n_cells):
        K0 = float(state.baselines["K"][i])
        Kt = float(state.K[i])
        delta = 0.0
        if K0 > 0:
            delta = max(-1.0, min(1.0, (Kt - K0) / K0))

        cells.append({
            "h3Index": state.h3_indices[i],
            "economicActivity": round(float(state.K[i]), 4),
            "delta": round(delta, 4),
            "jobDensity": round(float(state.E[i]), 2),
            "realEstateIndex": round(float(state.R[i]), 4),
            "congestion": round(float(state.T[i]), 4),
        })

    metrics = compute_aggregate_metrics(state)

    timestamp = datetime(
        year=2025, month=month, day=1,
        tzinfo=timezone.utc,
    ).isoformat()

    return {
        "month": month,
        "timestamp": timestamp,
        "cells": cells,
        "metrics": metrics,
    }
