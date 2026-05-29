from __future__ import annotations

from typing import Any

import h3
import numpy as np


def generate_overlay(
    snapshot: Any | None,
    h3_indices: list[str],
    city_config: Any,
) -> dict[str, dict[str, Any]]:
    if snapshot is None or not h3_indices:
        return {}

    cells = getattr(snapshot, "h3_cells", None) or {}
    news = cells.get("_city_level_news", {})
    mobility = cells.get("_city_level_mobility", {})
    jobs = cells.get("_city_level_jobs", {})
    land_value = cells.get("_city_level_land_value", {})

    news_sentiment = float(news.get("news_sentiment", 0.0))
    news_pressure = float(news.get("news_pressure", 0.0))
    mobility_sentiment = float(mobility.get("mobility_sentiment", 0.0))
    jobs_sentiment = float(jobs.get("jobs_sentiment", 0.0))
    real_estate_sentiment = float(land_value.get("real_estate_sentiment", 0.0))

    if max(abs(news_sentiment), abs(mobility_sentiment), abs(jobs_sentiment), abs(real_estate_sentiment), news_pressure) < 0.001:
        return {}

    centers = np.array([h3.cell_to_latlng(idx) for idx in h3_indices], dtype=np.float64)
    spatial_weight = _spatial_weights(centers, city_config)
    confidence = _overlay_confidence(snapshot)
    sources = _overlay_sources(snapshot)

    context_signal = _clamp(
        0.45 * news_sentiment
        + 0.25 * mobility_sentiment
        + 0.20 * jobs_sentiment
        + 0.10 * real_estate_sentiment,
        -1.0,
        1.0,
    )

    overlay: dict[str, dict[str, Any]] = {}
    for i, h3_index in enumerate(h3_indices):
        weight = float(spatial_weight[i])
        localized = context_signal * weight
        economic = _clamp(1.0 + localized * 0.15, 0.85, 1.15)
        migration = _clamp(1.0 - localized * 0.05 + max(-localized, 0.0) * 0.04, 0.90, 1.10)
        investment_delta = _clamp(localized * 0.15, -0.15, 0.15)
        real_estate = _clamp(1.0 + real_estate_sentiment * weight * 0.10, 0.90, 1.10)

        overlay[h3_index] = {
            "economic_activity_multiplier": economic,
            "migration_pressure_multiplier": migration,
            "investment_confidence_delta": investment_delta,
            "real_estate_multiplier": real_estate,
            "confidence": confidence,
            "origin": "real_time_context",
            "sources": sources,
            # Backward-compatible aliases for older engine callers.
            "economic_modifier": economic,
            "migration_modifier": migration,
            "investment_confidence": _clamp(0.5 + investment_delta, 0.0, 1.0),
        }
    return overlay


def _spatial_weights(centers: np.ndarray, city_config: Any) -> np.ndarray:
    center_lat, center_lng = city_config.center
    centrality = _decay(centers, center_lat, center_lng, 2.2)
    economic = _anchor_decay(centers, city_config, {"cbd", "commercial", "industrial"}, fallback=centrality)
    transport = _anchor_decay(centers, city_config, {"transport"}, fallback=centrality)
    weights = 0.5 * centrality + 0.3 * economic + 0.2 * transport
    return weights / max(float(np.max(weights)), 1.0)


def _anchor_decay(centers: np.ndarray, city_config: Any, types: set[str], fallback: np.ndarray) -> np.ndarray:
    anchors = [anchor for anchor in getattr(city_config, "urban_anchors", []) if getattr(anchor, "type", "") in types]
    if not anchors:
        return fallback
    result = np.zeros(centers.shape[0], dtype=np.float64)
    for anchor in anchors:
        result += float(getattr(anchor, "weight", 1.0)) * _decay(centers, anchor.lat, anchor.lng, 2.0)
    return result / max(float(np.max(result)), 1.0)


def _decay(centers: np.ndarray, lat: float, lng: float, decay: float) -> np.ndarray:
    dist = _haversine_vec(centers[:, 0], centers[:, 1], lat, lng)
    norm = dist / max(float(np.max(dist)), 1.0)
    return np.exp(-norm * decay)


def _overlay_confidence(snapshot: Any) -> float:
    quality = float(getattr(snapshot, "quality_score", 0.0) or 0.0)
    return _clamp(quality * 0.85, 0.0, 0.70)


def _overlay_sources(snapshot: Any) -> list[str]:
    manifest = getattr(snapshot, "source_manifest", {}) or {}
    return sorted({getattr(source, "source", "") for source in manifest.values() if getattr(source, "confidence", 0.0) > 0})


def _haversine_vec(lat: np.ndarray, lng: np.ndarray, center_lat: float, center_lng: float) -> np.ndarray:
    radius = 6371.0
    lat1 = np.radians(lat)
    lat2 = np.radians(center_lat)
    dlat = lat2 - lat1
    dlng = np.radians(center_lng) - np.radians(lng)
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2.0) ** 2
    return 2 * radius * np.arcsin(np.sqrt(a))


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))
