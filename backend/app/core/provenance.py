"""Provenance types — re-exported from engine.provenance.

The canonical definitions live in engine/provenance.py so the simulation
engine can use them without importing from the app package.  This module
re-exports everything so that existing ``from app.core.provenance import ...``
call-sites continue to work.
"""

from engine.provenance import (
    DataOrigin,
    MetricProvenance,
    ORIGIN_CONFIDENCE,
    DEFAULT_ORIGINS,
    clamp_confidence,
    confidence_label,
)

__all__ = [
    "DataOrigin",
    "MetricProvenance",
    "ORIGIN_CONFIDENCE",
    "DEFAULT_ORIGINS",
    "clamp_confidence",
    "confidence_label",
]
