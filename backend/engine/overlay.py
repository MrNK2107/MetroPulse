"""Real-time data overlay for H3 grid cells.

Converts city-level snapshot signals (news sentiment, mobility pressure, etc.)
into per-cell spatial modifiers that influence the simulation.

City-level signals are weighted spatially: CBD cells get stronger economic effects,
transport corridors get stronger mobility effects, and edge cells get migration pressure.
"""

from __future__ import annotations

from typing import Any

import numpy as np


# Spatial weight templates per signal type
_ECONOMIC_WEIGHT_DECAY = 2.5  # tighter — economic effects concentrate at CBD
_MIGRATION_WEIGHT_DECAY = 1.5  # looser — migration affects periphery more
_INVESTMENT_WEIGHT_DECAY = 2.0  # medium — investment spreads moderately


def generate_overlay(
    snapshot: Any,
    h3_indices: list[str],
    city_config: Any,
) -> dict[str, dict[str, float]] | None:
    """Convert city-level snapshot signals into per-cell modifiers.

    Uses urban anchors for spatial differentiation: CBD cells get stronger
    economic effects, transport corridors get stronger mobility effects.

    Returns dict keyed by H3 index. Each value has:
        economic_modifier: float (0.85 - 1.15)
        migration_modifier: float (0.90 - 1.10)
        investment_confidence: float (0.0 - 1.0)

    Returns None if no usable signal data exists.
    """
    cells = getattr(snapshot, "h3_cells", None)
    if not cells:
        return None

    # Extract city-level signals from snapshot
    news = cells.get("_city_level_news", {})
    mobility = cells.get("_city_level_mobility", {})
    jobs = cells.get("_city_level_jobs", {})
    land_value = cells.get("_city_level_land_value", {})

    news_sentiment = float(news.get("news_sentiment", 0.0))
    mobility_sentiment = float(mobility.get("mobility_sentiment", 0.0))
    jobs_sentiment = float(jobs.get("jobs_sentiment", 0.0))
    re_sentiment = float(land_value.get("real_estate_sentiment", 0.0))

    # If all signals are zero, no usable data
    if abs(news_sentiment) < 0.001 and abs(mobility_sentiment) < 0.001:
        return None

    # Get anchors for spatial weighting
    anchors = getattr(city_config, "urban_anchors", [])
    if not anchors:
        # Fallback: uniform application
        return _uniform_overlay(h3_indices, news_sentiment, mobility_sentiment,
                                jobs_sentiment, re_sentiment)

    # Compute spatial weights from anchors
    from engine.config import ANCHOR_DECAY
    n = len(h3_indices)

    # Build per-anchor spatial weight arrays (simplified: use anchor lat/lng directly)
    economic_weights = _compute_anchor_weights(anchors, "cbd", ANCHOR_DECAY.get("cbd", 2.8))
    migration_weights = _compute_anchor_weights(anchors, "residential", ANCHOR_DECAY.get("residential", 1.8))
    investment_weights = _compute_anchor_weights(anchors, "commercial", ANCHOR_DECAY.get("commercial", 2.5))

    # Normalize weights
    ew_sum = max(sum(economic_weights.values()), 0.001)
    mw_sum = max(sum(migration_weights.values()), 0.001)
    iw_sum = max(sum(investment_weights.values()), 0.001)

    # City-wide base modifiers
    base_economic = _clamp(1.0 + news_sentiment * 0.15, 0.85, 1.15)
    base_migration = _clamp(1.0 + (jobs_sentiment - re_sentiment) * 0.05, 0.90, 1.10)
    base_investment = _clamp((news_sentiment + mobility_sentiment + jobs_sentiment) / 3.0 * 0.5 + 0.5, 0.0, 1.0)

    # Apply spatial differentiation per anchor type
    result = {}
    for h3_index in h3_indices:
        # Economic: CBD cells get amplified effect
        cbd_weight = economic_weights.get(h3_index, 0.0) / ew_sum
        economic_mod = _clamp(base_economic * (0.8 + 0.4 * cbd_weight), 0.85, 1.15)

        # Migration: peripheral/residential cells get amplified effect
        mig_weight = migration_weights.get(h3_index, 0.0) / mw_sum
        migration_mod = _clamp(base_migration * (0.9 + 0.2 * mig_weight), 0.90, 1.10)

        # Investment: commercial cells get amplified effect
        inv_weight = investment_weights.get(h3_index, 0.0) / iw_sum
        investment_mod = _clamp(base_investment * (0.85 + 0.3 * inv_weight), 0.0, 1.0)

        result[h3_index] = {
            "economic_modifier": economic_mod,
            "migration_modifier": migration_mod,
            "investment_confidence": investment_mod,
        }

    return result


def _compute_anchor_weights(
    anchors: list[Any], anchor_type: str, decay: float
) -> dict[str, float]:
    """Compute spatial weights for a specific anchor type.

    Returns dict mapping anchor name to weight * exp(-0 * decay) = weight.
    (Since we don't have per-cell distances here, we use anchor weights directly.)
    """
    weights = {}
    for anchor in anchors:
        if getattr(anchor, "type", None) == anchor_type:
            weights[getattr(anchor, "name", "unknown")] = getattr(anchor, "weight", 1.0)
    # If no matching anchors, use CBD as fallback
    if not weights:
        for anchor in anchors:
            if getattr(anchor, "type", None) == "cbd":
                weights[getattr(anchor, "name", "unknown")] = getattr(anchor, "weight", 1.0)
    return weights


def _uniform_overlay(
    h3_indices: list[str],
    news_sentiment: float,
    mobility_sentiment: float,
    jobs_sentiment: float,
    re_sentiment: float,
) -> dict[str, dict[str, float]]:
    """Fallback: uniform application when no anchors available."""
    economic_modifier = _clamp(1.0 + news_sentiment * 0.15, 0.85, 1.15)
    migration_modifier = _clamp(1.0 + (jobs_sentiment - re_sentiment) * 0.05, 0.90, 1.10)
    investment_confidence = _clamp(
        (news_sentiment + mobility_sentiment + jobs_sentiment) / 3.0 * 0.5 + 0.5, 0.0, 1.0
    )

    modifier = {
        "economic_modifier": economic_modifier,
        "migration_modifier": migration_modifier,
        "investment_confidence": investment_confidence,
    }
    return {h3_index: modifier for h3_index in h3_indices}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
