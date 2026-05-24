"""
Derive economic activity baseline from nightlight intensity per H3 cell.

Reads NASA VIIRS / ISRO nightlight GeoTIFF and aggregates mean radiance
per H3 cell. Normalizes to [0, 1] as a proxy for economic activity.

Fallback: synthetic gradient from CBD (brighter centre).

Usage:
    python scripts/preprocess/nl_to_baseline.py --city bengaluru --tiff viirs.tif
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


def _synthetic_economic_activity(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    """Synthetic economic activity: bright core, gradient decay."""
    center_lat, center_lon = city_config.center
    lats = np.array([h3.cell_to_latlng(idx)[0] for idx in h3_indices])
    lons = np.array([h3.cell_to_latlng(idx)[1] for idx in h3_indices])
    d_cbd = _haversine_vec(lats, lons, center_lat, center_lon)

    activity = np.exp(-d_cbd / 5.0)
    activity = np.clip(activity, 0.05, 1.0)
    return activity.astype(np.float64)


def compute_economic_activity(
    h3_indices: list[str],
    city_config: CityConfig,
    tiff_path: str | None = None,
) -> dict[str, Any]:
    if tiff_path and os.path.exists(tiff_path):
        try:
            import rasterio
            from rasterio.windows import from_bounds

            with rasterio.open(tiff_path) as src:
                values = np.zeros(len(h3_indices), dtype=np.float64)
                for i, idx in enumerate(h3_indices):
                    bounds = h3.cell_to_boundary(idx)
                    lons, lats = zip(*bounds)
                    window = from_bounds(
                        min(lons), min(lats), max(lons), max(lats), src.transform
                    ).round_lengths()
                    if window.width > 0 and window.height > 0:
                        data = src.read(1, window=window)
                        v = float(np.nanmean(data[data > 0])) if np.any(data > 0) else 0
                        values[i] = v

                if values.max() > 0:
                    values = values / values.max()

            return {"source": "viirs", "data": values, "unit": "normalized_0_1"}

        except Exception as e:
            print(f"  TIFF read failed ({e}), using synthetic")

    data = _synthetic_economic_activity(h3_indices, city_config)
    return {"source": "synthetic", "data": data, "unit": "normalized_0_1"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--tiff", default=None, help="Path to VIIRS nightlight GeoTIFF")
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_economic_activity(h3_indices, config, args.tiff)
    print(f"  Source: {result['source']}")
    print(f"  Mean activity: {float(np.mean(result['data'])):.3f}")
