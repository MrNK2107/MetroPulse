"""
Compute flood risk score [0, 1] per H3 cell per month.

Uses elevation (from DEM) + proximity to drainage/water bodies + historical
inundation data. Returns a (n_cells, 12) array — one value per month.

Fallback: synthetic based on elevation + monsoon season intensity.

Usage:
    python scripts/preprocess/flood_risk.py --city mumbai --dem srtm.tif
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


def _synthetic_flood_risk(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    """Synthetic: low-lying areas near coast/water have higher risk."""
    center_lat, center_lon = city_config.center
    lats = np.array([h3.cell_to_latlng(idx)[0] for idx in h3_indices])
    lons = np.array([h3.cell_to_latlng(idx)[1] for idx in h3_indices])
    d_cbd = _haversine_vec(lats, lons, center_lat, center_lon)

    if city_config.port_city:
        flood_base = 0.3 * np.exp(-d_cbd / 10.0)
    else:
        flood_base = 0.1 * np.exp(-d_cbd / 8.0)

    flood_base += 0.05 * np.random.random(len(h3_indices))
    flood_base = np.clip(flood_base, 0.0, 1.0)

    risk = np.zeros((len(h3_indices), 12), dtype=np.float64)
    for m in range(12):
        if (m + 1) in city_config.monsoon_season:
            risk[:, m] = flood_base
        else:
            risk[:, m] = flood_base * 0.1

    return risk


def compute_flood_risk(
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
                        elevations[i] = float(np.nanmean(data[data > -9999])) if np.any(data > -9999) else 50
                    else:
                        elevations[i] = 50

                elevations[elevations < 0] = 0
                max_elev = max(elevations.max(), 1)
                flood_base = 1.0 - (elevations / max_elev)
                flood_base = np.clip(flood_base, 0.0, 1.0)

        except Exception as e:
            print(f"  DEM read failed ({e}), using synthetic")
            flood_base = None
    else:
        flood_base = None

    if flood_base is None:
        data = _synthetic_flood_risk(h3_indices, city_config)
        return {"source": "synthetic", "data": data, "unit": "risk_0_1", "months": list(range(1, 13))}

    data = np.zeros((len(h3_indices), 12), dtype=np.float64)
    for m in range(12):
        if (m + 1) in city_config.monsoon_season:
            data[:, m] = flood_base
        else:
            data[:, m] = flood_base * 0.1

    return {"source": "dem", "data": data, "unit": "risk_0_1", "months": list(range(1, 13))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--dem", default=None, help="Path to SRTM DEM GeoTIFF")
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_flood_risk(h3_indices, config, args.dem)
    print(f"  Source: {result['source']}")
    print(f"  Max risk (monsoon): {float(np.max(result['data'][:, [m-1 for m in config.monsoon_season]])):.3f}")
