"""
Compute distance from each H3 cell to nearest major road.

Uses OSMnx to fetch road network for the city boundary, then computes
haversine distance from each H3 cell center to the nearest arterial road.

Fallback: synthetic distance based on distance from city center
(roads denser near CBD).

Usage:
    python scripts/preprocess/road_proximity.py --city bengaluru
"""
import argparse
import os
import sys
from typing import Any

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


def _synthetic_road_distance(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    """Synthetic: distance to nearest road increases with distance from CBD."""
    center_lat, center_lon = city_config.center
    lats = np.array([h3.cell_to_latlng(idx)[0] for idx in h3_indices])
    lons = np.array([h3.cell_to_latlng(idx)[1] for idx in h3_indices])
    d_cbd = _haversine_vec(lats, lons, center_lat, center_lon)

    road_dist = 0.05 + 0.8 * np.exp(d_cbd / 8.0) - 0.8
    return np.maximum(road_dist, 0.02)


def compute_road_proximity(
    h3_indices: list[str],
    city_config: CityConfig,
) -> dict[str, Any]:
    try:
        import osmnx as ox

        boundary = city_config.get_boundary_polygon()
        G = ox.graph_from_polygon(
            boundary["coordinates"][0],
            network_type="drive",
            simplify=True,
        )
        nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

        if "highway" in edges.columns:
            major = edges[edges["highway"].isin(
                ["motorway", "trunk", "primary", "secondary", "tertiary"]
            )]
        else:
            major = edges

        if major.empty:
            raise ValueError("No major roads found")

        major_lats = major.geometry.centroid.y.values
        major_lons = major.geometry.centroid.x.values

        distances = np.full(len(h3_indices), 999.0, dtype=np.float64)
        for i, idx in enumerate(h3_indices):
            lat, lon = h3.cell_to_latlng(idx)
            d = _haversine_vec(lat, lon, major_lats, major_lons)
            distances[i] = float(np.min(d))

        return {"source": "osmnx", "data": distances, "unit": "km"}

    except Exception as e:
        print(f"  OSMnx failed ({e}), using synthetic")
        data = _synthetic_road_distance(h3_indices, city_config)
        return {"source": "synthetic", "data": data, "unit": "km"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_road_proximity(h3_indices, config)
    print(f"  Source: {result['source']}")
    print(f"  Min distance: {float(np.min(result['data'])):.3f} km")
    print(f"  Max distance: {float(np.max(result['data'])):.3f} km")
