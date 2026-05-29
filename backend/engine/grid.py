from __future__ import annotations

import json
from typing import Any

import h3
import numpy as np

from engine.models import GridState, N_SECTORS, SECTOR_INDEX, SECTOR_NAMES, SimulationParams


class GridFactory:
    @classmethod
    def initialize(cls, region_boundary: dict[str, Any], params: SimulationParams) -> GridState:
        resolution = 8
        shape = h3.geo_to_h3shape(region_boundary)
        h3_indices = list(h3.h3shape_to_cells(shape, resolution))
        if not h3_indices:
            center_lat, center_lng = params.city_config.center
            h3_indices = list(h3.grid_disk(h3.latlng_to_cell(center_lat, center_lng, resolution), 3))

        centers = np.array([h3.cell_to_latlng(idx) for idx in h3_indices], dtype=np.float64)
        n = len(h3_indices)
        center_lat, center_lng = params.city_config.center
        # Multi-center density: sum weighted exponential decay from each urban anchor
        from engine.config import ANCHOR_DECAY
        anchors = params.city_config.urban_anchors
        density = np.zeros(n, dtype=np.float64)
        for anchor in anchors:
            d = _haversine_vec(centers[:, 0], centers[:, 1], anchor.lat, anchor.lng)
            d_max = max(float(np.max(d)), 1.0)
            d_n = d / d_max
            decay = ANCHOR_DECAY.get(anchor.type, 2.0)
            density += anchor.weight * np.exp(-d_n * decay)
        density = density / max(float(density.sum()), 1.0)

        # Distance from primary center (used for outer_density, d_norm references)
        d_cbd = _haversine_vec(centers[:, 0], centers[:, 1], center_lat, center_lng)
        d_norm = d_cbd / max(float(np.max(d_cbd)), 1.0)

        weights = np.array(
            [float(params.city_config.sector_weights.get(name, 1.0 / N_SECTORS)) for name in SECTOR_NAMES],
            dtype=np.float64,
        )
        weights = weights / max(float(weights.sum()), 1.0)

        baselines = params.city_config.baselines
        total_formal = float(baselines.get("employment_formal", params.city_config.population * 0.25))
        total_informal = float(baselines.get("employment_informal", params.city_config.population * 0.35))
        gdp_proxy = float(baselines.get("gdp_estimate_crores", params.city_config.population / 100.0))
        slum_pct = float(baselines.get("slum_population_pct", 0.15))
        outer_density = (0.25 + d_norm) / max(float(np.sum(0.25 + d_norm)), 1.0)

        E_formal = total_formal * density
        E_informal = total_informal * (0.65 * density + 0.35 * outer_density)
        K_total = gdp_proxy * (0.75 * density + 0.25 / n)
        K = K_total[:, None] * weights[None, :]

        R = np.clip(1.25 * np.exp(-d_norm * 1.8) + 0.35, 0.25, 1.8)
        T = np.clip(0.25 + 0.55 * np.exp(-d_norm * 1.4), 0.05, 0.95)
        H = np.clip(1.25 - (R - np.mean(R)) * 0.35 - slum_pct * 0.15, 0.35, 1.6)
        F = _flood_proxy(params.city_config, centers, d_norm)
        M = np.clip(0.15 + d_norm * 0.65 + weights[SECTOR_INDEX["informal"]] * 0.4, 0.0, 1.0)
        slum_flag = d_norm > np.quantile(d_norm, max(0.55, 1.0 - slum_pct))

        # Initialize confidence arrays (all synthetic initially)
        from engine.provenance import ORIGIN_CONFIDENCE, DataOrigin, DEFAULT_ORIGINS

        confidence_K = np.full(n, ORIGIN_CONFIDENCE[DataOrigin.SYNTHETIC])
        confidence_R = np.full(n, ORIGIN_CONFIDENCE[DataOrigin.SYNTHETIC])
        confidence_T = np.full(n, ORIGIN_CONFIDENCE[DataOrigin.SYNTHETIC])
        confidence_H = np.full(n, ORIGIN_CONFIDENCE[DataOrigin.SYNTHETIC])
        confidence_F = np.full(n, ORIGIN_CONFIDENCE[DataOrigin.SYNTHETIC])
        confidence_M = np.full(n, ORIGIN_CONFIDENCE[DataOrigin.SYNTHETIC])
        data_origins = {k: v.value for k, v in DEFAULT_ORIGINS.items()}

        # Apply real-time overlay from snapshot (city-level signals → per-cell modifiers)
        snapshot = getattr(params, "realtime_snapshot", None)
        overlay_summary: dict[str, Any] = {}
        if snapshot:
            from app.simulation.overlay import generate_overlay

            overlay = generate_overlay(snapshot, h3_indices, params.city_config)
            if overlay:
                confidences = []
                sources: set[str] = set()
                modified = 0
                for i, h3_index in enumerate(h3_indices):
                    mod = overlay.get(h3_index)
                    if not mod:
                        continue
                    modified += 1
                    K[i, :] *= float(mod["economic_activity_multiplier"])
                    M[i] *= float(mod["migration_pressure_multiplier"])
                    R[i] *= float(mod["real_estate_multiplier"])
                    confidence = float(mod.get("confidence", 0.0))
                    confidence_K[i] = max(confidence_K[i], confidence)
                    confidence_M[i] = max(confidence_M[i], confidence)
                    confidence_R[i] = max(confidence_R[i], confidence * 0.9)
                    confidences.append(confidence)
                    sources.update(mod.get("sources", []))
                data_origins["K"] = "real_time_context"
                data_origins["M"] = "real_time_context"
                data_origins["R"] = "real_time_context"
                overlay_summary = {
                    "applied": modified > 0,
                    "modified_cells": modified,
                    "origin": "real_time_context",
                    "sources": sorted(sources),
                    "confidence": float(np.mean(confidences)) if confidences else 0.0,
                }

        neighbor_pairs = cls._neighbor_pairs(h3_indices)
        zone_flags = cls._zone_flags(h3_indices, params.city_config)

        # Precompute neighbor arrays as numpy for fast secondary_loop
        neighbor_i_idx = None
        neighbor_j_idx = None
        neighbor_weights = None
        if neighbor_pairs:
            pairs_arr = np.array(neighbor_pairs, dtype=np.float64)
            neighbor_i_idx = pairs_arr[:, 0].astype(int)
            neighbor_j_idx = pairs_arr[:, 1].astype(int)
            lambda_r = float(params.city_config.constants.get("lambda_realestate_cascade", 3.2))
            neighbor_weights = np.exp(-pairs_arr[:, 2] / lambda_r)

        return GridState(
            h3_indices=h3_indices,
            cell_centers=centers,
            K=K,
            E_formal=E_formal,
            E_informal=E_informal,
            R=R,
            T=T,
            H=H,
            F=F,
            M=M,
            baselines={
                "K": K.copy(),
                "E_formal": E_formal.copy(),
                "E_informal": E_informal.copy(),
                "R": R.copy(),
                "T": T.copy(),
                "H": H.copy(),
                "M": M.copy(),
                "unemployment_rate": float(baselines.get("unemployment_rate", 0.05)),
            },
            slum_flag=slum_flag,
            sector_weights=weights,
            constants=dict(params.city_config.constants),
            city_center=(center_lat, center_lng),
            neighbor_pairs=neighbor_pairs,
            neighbor_i_idx=neighbor_i_idx,
            neighbor_j_idx=neighbor_j_idx,
            neighbor_weights=neighbor_weights,
            zone_flags=zone_flags,
            snapshot_id=getattr(snapshot, "id", None),
            data_mode="real_time" if getattr(snapshot, "is_realtime", False) else "demo",
            source_manifest=snapshot.manifest_for_json() if snapshot else {},
            snapshot_quality_score=float(getattr(snapshot, "quality_score", 0.0) or 0.0),
            confidence_K=confidence_K,
            confidence_R=confidence_R,
            confidence_T=confidence_T,
            confidence_H=confidence_H,
            confidence_F=confidence_F,
            confidence_M=confidence_M,
            data_origins=data_origins,
            overlay_summary=overlay_summary,
            metric_metadata={
                "rag_confidence": float((params.evidence_pack or {}).get("overall_evidence_confidence", 0.0) or 0.0)
            },
        )

    @staticmethod
    def _neighbor_pairs(h3_indices: list[str]) -> list[tuple[int, int, float]]:
        idx_to_pos = {idx: i for i, idx in enumerate(h3_indices)}
        pairs: list[tuple[int, int, float]] = []
        for i, idx in enumerate(h3_indices):
            center_i = h3.cell_to_latlng(idx)
            for neighbor in h3.grid_disk(idx, 1):
                j = idx_to_pos.get(neighbor)
                if j is None or j == i:
                    continue
                center_j = h3.cell_to_latlng(neighbor)
                pairs.append((i, j, _haversine(center_i, center_j)))
        return pairs

    @staticmethod
    def _zone_flags(h3_indices: list[str], city_config: Any) -> dict[str, np.ndarray]:
        flags: dict[str, np.ndarray] = {}
        n = len(h3_indices)
        centers = np.array([h3.cell_to_latlng(idx) for idx in h3_indices], dtype=np.float64)
        center_lat, center_lng = city_config.center

        for zone in city_config.special_zones:
            name = zone.get("name", "zone")
            zone_file = zone.get("file")

            # Try GeoJSON polygon containment first
            if zone_file:
                import os
                abs_path = os.path.join(os.path.dirname(__file__), "..", "..", zone_file)
                if os.path.exists(abs_path):
                    try:
                        with open(abs_path, "r") as f:
                            geojson = json.load(f)
                        features = geojson.get("features", [])
                        if features:
                            geom = features[0]["geometry"]
                            if geom.get("type") in ("Polygon", "MultiPolygon"):
                                shape = h3.geo_to_h3shape(geom)
                                zone_cells = set(h3.h3shape_to_cells(shape, 8))
                                mask = np.isin(np.array(h3_indices), list(zone_cells))
                                if np.any(mask):
                                    flags[name] = mask
                                    continue
                    except Exception:
                        pass  # Fall through to distance fallback

            # Fallback: distance radius from city center
            dist = _haversine_vec(centers[:, 0], centers[:, 1], center_lat, center_lng)
            radius = float(zone.get("radius_km", 5.0))
            flags[name] = dist <= radius

        return flags


def public_zone_mask(state: GridState, zone_geojson: dict[str, Any] | None) -> np.ndarray:
    mask = np.zeros(state.n_cells, dtype=bool)
    if not zone_geojson:
        return mask
    zone_type = zone_geojson.get("type")
    try:
        if zone_type == "Point":
            lng, lat = zone_geojson["coordinates"]
            dist = _haversine_vec(state.cell_centers[:, 0], state.cell_centers[:, 1], lat, lng)
            return dist <= 3.0
        if zone_type == "Polygon":
            # Cache the public zone distance computation by hash of coords
            zone_key = hash(str(zone_geojson["coordinates"]))
            if zone_key not in state.public_dist_cache:
                shape = h3.geo_to_h3shape(zone_geojson)
                zone_cells = set(h3.h3shape_to_cells(shape, 8))
                state.public_dist_cache[zone_key] = np.isin(
                    np.array(state.h3_indices), list(zone_cells)
                )
            return state.public_dist_cache[zone_key]
    except Exception:
        return mask
    return mask


def _flood_proxy(city_config: Any, centers: np.ndarray, d_norm: np.ndarray) -> np.ndarray:
    """Estimate per-cell flood risk using urban geography heuristics.

    Uses distance-from-center as a proxy for proximity to waterways
    (rivers/coast typically at city edges). Port cities get elevated base risk.
    Still synthetic but grounded in urban morphology, not arbitrary sine waves.
    """
    # Base risk increases toward periphery (rivers/coast at edges)
    base = 0.10 + 0.25 * d_norm
    # Port cities get elevated coastal risk
    if city_config.port_city:
        base += 0.15
    # Cells near city boundary = higher water proximity risk
    edge_proximity = 1.0 - d_norm
    base += 0.08 * edge_proximity
    # Allow city-specific override
    city_flood_baseline = float(city_config.constants.get("flood_baseline", 0.0))
    if city_flood_baseline > 0:
        base = city_flood_baseline * np.ones_like(base)
    return np.clip(base, 0.0, 1.0)


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(_haversine_vec(np.array([a[0]]), np.array([a[1]]), b[0], b[1])[0])


def _haversine_vec(lat: np.ndarray, lng: np.ndarray, center_lat: float, center_lng: float) -> np.ndarray:
    lat1 = np.radians(lat)
    lon1 = np.radians(lng)
    lat2 = np.radians(center_lat)
    lon2 = np.radians(center_lng)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    hav = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(hav))
