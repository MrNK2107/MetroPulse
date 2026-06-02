from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Core provenance types (canonical home: engine/) ─────────────────────────

class DataOrigin(str, Enum):
    REAL = "real"
    REAL_TIME_CONTEXT = "real_time_context"
    ESTIMATED = "estimated"
    SYNTHETIC = "synthetic"
    HARDCODED = "hardcoded"
    FALLBACK = "fallback"
    RAG_EVIDENCE = "rag_evidence"


class MetricProvenance(BaseModel):
    origin: DataOrigin
    source: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    method: Optional[str] = None
    notes: Optional[str] = None


ORIGIN_CONFIDENCE: dict[DataOrigin, float] = {
    DataOrigin.REAL: 0.85,
    DataOrigin.REAL_TIME_CONTEXT: 0.70,
    DataOrigin.ESTIMATED: 0.60,
    DataOrigin.SYNTHETIC: 0.35,
    DataOrigin.HARDCODED: 0.40,
    DataOrigin.FALLBACK: 0.25,
    DataOrigin.RAG_EVIDENCE: 0.65,
}


DEFAULT_ORIGINS: dict[str, DataOrigin] = {
    "K": DataOrigin.SYNTHETIC,
    "E_formal": DataOrigin.ESTIMATED,
    "E_informal": DataOrigin.ESTIMATED,
    "R": DataOrigin.SYNTHETIC,
    "T": DataOrigin.SYNTHETIC,
    "H": DataOrigin.SYNTHETIC,
    "F": DataOrigin.SYNTHETIC,
    "M": DataOrigin.SYNTHETIC,
}


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def confidence_label(value: float) -> str:
    score = clamp_confidence(value)
    if score >= 0.70:
        return "High"
    if score >= 0.40:
        return "Medium"
    return "Low"


# ── Decay constants used by simulation loops ────────────────────────────────

PRIMARY_LOOP_DECAY = 0.97
SECONDARY_CASCADE_DECAY = 0.95
SECONDARY_UPDATE_DECAY = 0.85
MONSOON_DECAY = 0.75


def interpret_confidence(score: float) -> str:
    label = confidence_label(score)
    if label == "High":
        return "High confidence - grounded in measured or high-quality contextual data"
    if label == "Medium":
        return "Medium confidence - evidence-informed estimate"
    return "Low confidence - synthetic or fallback-heavy estimate"
