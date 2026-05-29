from __future__ import annotations

from app.core.provenance import DataOrigin, ORIGIN_CONFIDENCE, DEFAULT_ORIGINS, confidence_label

PRIMARY_LOOP_DECAY = 0.90
SECONDARY_CASCADE_DECAY = 0.80
SECONDARY_UPDATE_DECAY = 0.85
MONSOON_DECAY = 0.75


def interpret_confidence(score: float) -> str:
    label = confidence_label(score)
    if label == "High":
        return "High confidence - grounded in measured or high-quality contextual data"
    if label == "Medium":
        return "Medium confidence - evidence-informed estimate"
    return "Low confidence - synthetic or fallback-heavy estimate"
