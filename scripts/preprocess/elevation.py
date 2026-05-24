"""
Compute mean elevation per H3 cell from SRTM DEM.

Reads a GeoTIFF (e.g. SRTM 30m) and computes mean elevation
for each H3 cell at resolution 8.

Fallback: synthetic elevation based on city type (coastal cities flat, inland varied).

Usage:
    python scripts/preprocess/elevation.py --city bengaluru --dem srtm.tif
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


def _synthetic_elevation(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    """Synthetic: use city type to guess rough elevation profile."""
    center_lat, center_lon = city_config.center
    lats = np.array([h3.cell_to_latlng(idx)[0] for idx in h3_indices])
    lons = np.array([h3.cell_to_latlng(idx)[1] for idx in h3_indices])
    d_cbd = _haversine_vec(lats, lons, center_lat, center_lon)

    elevation_profiles = {
        "tech_hub": 920.0,
        "financial_hub": 10.0,
        "capital_region": 220.0,
        "auto_it_education": 560.0,
        "auto_it_port": 6.0,
        "pharma_it": 540.0,
        "textile_pharma_auto": 55.0,
        "port_services": 9.0,
        "admin_services": 130.0,
        "tourism_handicrafts": 430.0,
        "planned_services": 350.0,
        "admin_education_it": 45.0,
    }

    base_elevation = elevation_profiles.get(city_config.city_type, 100.0)
    variation = 20 * np.sin(d_cbd / 2.0) + 10 * np.random.random(len(h3_indices))
    return (base_elevation + variation).astype(np.float64)


def compute_elevation(
    h3_indices: list[str],
    city_config: CityConfig,
    dem_path: str | None = None,
) -> dict[str, Any]:
    if dem_path and os.path.exists(dem_path):
        try:
            import rasterio
            from rasterio.windows import from_bounds

            with rasterio.open(dem_path) as src:
                elevations = np.zeros(len(h3_indices), dtype=np.float64)
                for i, idx in enumerate(h3_indices):
                    bounds = h3.cell_to_boundary(idx)
                    lons, lats = zip(*bounds)
                    window = from_bounds(
                        min(lons), min(lats), max(lons), max(lats), src.transform
                    ).round_lengths()
                    if window.width > 0 and window.height > 0:
                        data = src.read(1, window=window)
                        v = float(np.nanmean(data[data > -9999])) if np.any(data > -9999) else 0
                        elevations[i] = max(v, 0)
                    else:
                        elevations[i] = 0

            return {"source": "dem", "data": elevations, "unit": "meters"}

        except Exception as e:
            print(f"  DEM read failed ({e}), using synthetic")

    data = _synthetic_elevation(h3_indices, city_config)
    return {"source": "synthetic", "data": data, "unit": "meters"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--dem", default=None, help="Path to SRTM DEM GeoTIFF")
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_elevation(h3_indices, config, args.dem)
    print(f"  Source: {result['source']}")
    print(f"  Mean elevation: {float(np.mean(result['data'])):.1f} m")
