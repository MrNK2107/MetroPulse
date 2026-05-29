from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from app.core.provenance import DataOrigin
from app.simulation.confidence import derived_confidence, label_for_confidence
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
    mode_label = "Realtime Context" if state.data_mode == "real_time" else "Estimated"
    source_label = "contextual data sources" if state.data_mode == "real_time" else "city baseline estimates"

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

    # Compute per-cell confidence (average of all metric confidences)
    conf_arrays = [
        state.confidence_K, state.confidence_R, state.confidence_T,
        state.confidence_H, state.confidence_F, state.confidence_M,
    ]
    valid_confs = [c for c in conf_arrays if c is not None]
    if valid_confs:
        cell_confidence = np.mean(valid_confs, axis=0)
        cell_confidence = np.round(cell_confidence, 2)
    else:
        cell_confidence = np.full(state.n_cells, 0.35)

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
            "confidence": float(cell_confidence[i]),
            "proof": (
                f"\\Delta K {(deltas[i] * 100):+.1f}%; "
                f"jobs {total_jobs[i]:,.0f}; "
                f"R={state.R[i]:.2f}, T={state.T[i]:.2f}; "
                f"{mode_label} via {source_label}; "
                f"drivers: {drivers}"
            ),
        }
        for i in range(state.n_cells)
    ]

    year = 2026 + (month - 1) // 12
    m = ((month - 1) % 12) + 1
    metrics = compute_aggregate_metrics(state)
    overall_confidence = float(np.round(np.mean(cell_confidence), 2))
    overlay_conf = float(state.overlay_summary.get("confidence", 0.0) or 0.0)
    rag_conf = float(state.metric_metadata.get("rag_confidence", 0.0) or 0.0)
    metric_metadata = _metric_metadata(state, metrics, overall_confidence, overlay_conf, rag_conf)

    return {
        "month": month,
        "timestamp": datetime(year=year, month=m, day=1, tzinfo=timezone.utc).isoformat(),
        "cells": cells,
        "metrics": metrics,
        "metric_metadata": metric_metadata,
        "activeLoop": " -> ".join(state.active_effects[:4]) if state.active_effects else "baseline",
        "proof": {
            "formula": "\\Delta K_{sector} = \\text{monthly\\_rate} \\times \\text{sector\\_weight} \\times K; cascading R/T/H/M updates are deterministic vector operations.",
            "dataQuality": (
                "Real-Time Mode uses the latest normalized city snapshot and marks stale domains."
                if state.data_mode == "real_time"
                else "Demo Mode uses city YAML/proxy baselines because no usable live snapshot is available."
            ),
            "dataMode": state.data_mode,
            "snapshotId": state.snapshot_id,
            "qualityScore": state.snapshot_quality_score,
            "dataSources": state.source_manifest or {},
            "cellCount": state.n_cells,
            "activeEffects": state.active_effects,
            "dataOrigins": state.data_origins or {},
            "overallConfidence": overall_confidence,
            "confidenceLabel": label_for_confidence(overall_confidence),
            "overlaySummary": state.overlay_summary,
        },
    }


def _metric_metadata(
    state: GridState,
    metrics: dict[str, float],
    overall_confidence: float,
    overlay_confidence: float,
    rag_confidence: float,
) -> dict[str, dict]:
    sources = ["city_baseline_yaml"]
    if state.overlay_summary.get("applied"):
        sources.append("real_time_context_overlay")
    if rag_confidence > 0:
        sources.append("rag_evidence_pack")

    baseline_conf = 0.60
    coeff_conf = max(rag_confidence, 0.40)
    metadata = {}
    for key in metrics:
        confidence = derived_confidence(
            baseline_confidence=baseline_conf,
            coefficient_confidence=coeff_conf,
            realtime_overlay_confidence=overlay_confidence,
            rag_evidence_confidence=rag_confidence,
        )
        origin = DataOrigin.ESTIMATED.value
        if state.overlay_summary.get("applied"):
            origin = DataOrigin.REAL_TIME_CONTEXT.value
        if key in {"floodDisruption"}:
            origin = DataOrigin.SYNTHETIC.value
        metadata[key] = {
            "value": metrics[key],
            "confidence": round(confidence if key != "floodDisruption" else min(overall_confidence, 0.45), 3),
            "confidence_label": label_for_confidence(confidence),
            "origin": origin,
            "sources": sources,
        }
    return metadata
