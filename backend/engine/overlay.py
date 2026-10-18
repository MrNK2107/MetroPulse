"""Real-time data overlay for H3 grid cells — DEPRECATED.

The canonical implementation lives in ``app/simulation/overlay.py``.
This module re-exports ``generate_overlay`` for backward compatibility
but new code should import from ``app.simulation.overlay`` directly.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)
logger.warning(
    "engine.overlay is deprecated; use app.simulation.overlay.generate_overlay instead."
)


def generate_overlay(
    snapshot: Any,
    h3_indices: list[str],
    city_config: Any,
) -> dict[str, dict[str, float]] | None:
    """DEPRECATED — delegates to ``app.simulation.overlay.generate_overlay``."""
    from app.simulation.overlay import generate_overlay as _real

    result = _real(snapshot, h3_indices, city_config)
    if not result:
        return None

    # Map back to the legacy return-type keys for existing engine callers
    mapped: dict[str, dict[str, float]] = {}
    for h3_index, vals in result.items():
        mapped[h3_index] = {
            "economic_modifier": float(vals.get("economic_modifier", 1.0)),
            "migration_modifier": float(vals.get("migration_modifier", 1.0)),
            "investment_confidence": float(vals.get("investment_confidence", 0.5)),
        }
    return mapped
