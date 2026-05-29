from __future__ import annotations

from app.core.provenance import DataOrigin, ORIGIN_CONFIDENCE, clamp_confidence, confidence_label


def base_confidence(origin: DataOrigin | str) -> float:
    data_origin = DataOrigin(origin)
    return ORIGIN_CONFIDENCE[data_origin]


def derived_confidence(
    *,
    baseline_confidence: float,
    coefficient_confidence: float,
    realtime_overlay_confidence: float,
    rag_evidence_confidence: float,
    model_confidence: float = 0.85,
) -> float:
    weighted = (
        0.4 * baseline_confidence
        + 0.3 * coefficient_confidence
        + 0.2 * realtime_overlay_confidence
        + 0.1 * rag_evidence_confidence
    )
    return clamp_confidence(weighted * model_confidence)


def label_for_confidence(value: float) -> str:
    return confidence_label(value)
