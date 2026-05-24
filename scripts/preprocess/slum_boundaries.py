"""
Compute boolean mask of H3 cells that overlap with informal settlements.

Reads slum boundary polygon GeoJSON (from government / NGO sources).

Fallback: synthetic slum flags based on distance from CBD + LULC class.

Usage:
    python scripts/preprocess/slum_boundaries.py --city mumbai --slums slums.geojson
"""
import argparse
import json
import os
import sys

import numpy as np
import h3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from engine.config import CityConfig  # noqa: E402


def _haversine_vec(lat1, lon1, lat2, lon2):
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def _synthetic_slum_flags(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    """Slums cluster 3-8km from CBD, correlated with low LULC quality."""
    center_lat, center_lon = city_config.center
    lats = np.array([h3.cell_to_latlng(idx)[0] for idx in h3_indices])
    lons = np.array([h3.cell_to_latlng(idx)[1] for idx in h3_indices])
    d_cbd = _haversine_vec(lats, lons, center_lat, center_lon)

    slum_pct = city_config.baselines.get("slum_population_pct", 0.15)
    prob = slum_pct * 3 * np.exp(-((d_cbd - 5) ** 2) / 8)
    np.random.seed(42)
    flags = np.random.random(len(h3_indices)) < prob
    return flags


def compute_slum_flags(
    h3_indices: list[str],
    city_config: CityConfig,
    slums_path: str | None = None,
) -> dict[str, np.ndarray]:
    if slums_path and os.path.exists(slums_path):
        try:
            with open(slums_path) as f:
                geojson = json.load(f)

            features = geojson.get("features", [geojson])
            slum_indices: set[str] = set()
            for feat in features:
                geom = feat.get("geometry", feat)
                try:
                    shape = h3.geo_to_h3shape(geom)
                    cells = list(h3.h3shape_to_cells(shape, 8))
                    slum_indices.update(cells)
                except Exception:
                    pass

            mask = np.array([idx in slum_indices for idx in h3_indices], dtype=bool)
            return {"source": "slums_file", "data": mask}

        except Exception as e:
            print(f"  Slum file read failed ({e}), using synthetic")

    data = _synthetic_slum_flags(h3_indices, city_config)
    return {"source": "synthetic", "data": data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--slums", default=None, help="GeoJSON of slum boundaries")
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_slum_flags(h3_indices, config, args.slums)
    print(f"  Source: {result['source']}")
    print(f"  Slum cells: {int(result['data'].sum())} / {len(h3_indices)}")
