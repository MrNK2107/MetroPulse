"""
Compute distance from each H3 cell to nearest rail / metro station.

Fallback: synthetic distance based on city type (metro cities get denser station networks).

Usage:
    python scripts/preprocess/transit_nodes.py --city bengaluru
"""
import argparse
import json
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


def _synthetic_transit_distance(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    center_lat, center_lon = city_config.center
    lats = np.array([h3.cell_to_latlng(idx)[0] for idx in h3_indices])
    lons = np.array([h3.cell_to_latlng(idx)[1] for idx in h3_indices])
    d_cbd = _haversine_vec(lats, lons, center_lat, center_lon)

    if city_config.metro_system:
        base = 0.3
        scale = 3.0
    else:
        base = 1.0
        scale = 5.0

    dist = base + scale * np.exp(d_cbd / 6.0) - scale
    return np.maximum(dist, 0.1)


def compute_transit_distance(
    h3_indices: list[str],
    city_config: CityConfig,
    station_file: str | None = None,
) -> dict[str, Any]:
    if station_file and os.path.exists(station_file):
        try:
            with open(station_file) as f:
                stations = json.load(f)
            features = stations.get("features", [])
            if features:
                coords = []
                for feat in features:
                    geom = feat.get("geometry", {})
                    if geom.get("type") == "Point":
                        coords.append(geom["coordinates"])
                if coords:
                    coords = np.array(coords)
                    station_lons = coords[:, 0]
                    station_lats = coords[:, 1]

                    distances = np.full(len(h3_indices), 999.0, dtype=np.float64)
                    for i, idx in enumerate(h3_indices):
                        lat, lon = h3.cell_to_latlng(idx)
                        d = _haversine_vec(lat, lon, station_lats, station_lons)
                        distances[i] = float(np.min(d))
                    return {"source": "stations_file", "data": distances, "unit": "km"}

        except Exception as e:
            print(f"  Station file read failed ({e}), using synthetic")

    data = _synthetic_transit_distance(h3_indices, city_config)
    return {"source": "synthetic", "data": data, "unit": "km"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--stations", default=None, help="GeoJSON of stations")
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_transit_distance(h3_indices, config, args.stations)
    print(f"  Source: {result['source']}")
    print(f"  Min distance: {float(np.min(result['data'])):.3f} km")
    print(f"  Max distance: {float(np.max(result['data'])):.3f} km")
