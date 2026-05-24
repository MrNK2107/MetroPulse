"""
Aggregate land use / land cover into H3 hexagons.

Reads a GeoTIFF (e.g. from ISRO Bhuvan) and computes the dominant
LULC class per H3 cell at the given resolution.

Fallback: generates synthetic LULC based on city type (CBD vs periphery).

Usage:
    python scripts/preprocess/lulc_to_h3.py --city bengaluru
"""
import argparse
import os
import sys
from typing import Any

import numpy as np
import h3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from engine.config import CityConfig  # noqa: E402

LULC_CLASSES = {
    0: "water",
    1: "built_up",
    2: "industrial",
    3: "vegetation",
    4: "agriculture",
    5: "barren",
    6: "wetland",
}


def _synthetic_lulc(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    """Generate synthetic LULC classes based on distance from city center."""
    center_lat, center_lon = city_config.center
    n = len(h3_indices)
    classes = np.full(n, 3, dtype=np.int32)  # default vegetation

    for i, idx in enumerate(h3_indices):
        lat, lon = h3.cell_to_latlng(idx)
        dlat = np.radians(lat - center_lat)
        dlon = np.radians(lon - center_lon)
        a = (
            np.sin(dlat / 2) ** 2
            + np.cos(np.radians(center_lat))
            * np.cos(np.radians(lat))
            * np.sin(dlon / 2) ** 2
        )
        d_km = 6371.0 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        if d_km < 3:
            classes[i] = 1  # built_up core
        elif d_km < 8:
            classes[i] = 2  # industrial / mixed
        elif d_km < 15:
            classes[i] = 4  # agriculture fringe
        else:
            classes[i] = 3  # vegetation

    return classes


def compute_lulc(
    h3_indices: list[str],
    city_config: CityConfig,
    geotiff_path: str | None = None,
) -> dict[str, Any]:
    if geotiff_path and os.path.exists(geotiff_path):
        try:
            import rasterio
            from rasterio.features import geometry_mask

            with rasterio.open(geotiff_path) as src:
                lulc_data = _from_rasterio(h3_indices, src)
            return {"source": "raster", "data": lulc_data, "classes": LULC_CLASSES}
        except Exception as e:
            print(f"  Raster read failed ({e}), falling back to synthetic")

    classes = _synthetic_lulc(h3_indices, city_config)
    return {"source": "synthetic", "data": classes, "classes": LULC_CLASSES}


def _from_rasterio(h3_indices: list[str], src: Any) -> np.ndarray:
    """Read actual GeoTIFF and aggregate per H3 cell."""
    import rasterio.features
    from rasterio.windows import from_bounds

    results = np.empty(len(h3_indices), dtype=np.int32)
    for i, idx in enumerate(h3_indices):
        bounds = h3.cell_to_boundary(idx)
        lons, lats = zip(*bounds)
        window = from_bounds(
            min(lons), min(lats), max(lons), max(lats), src.transform
        )
        window = window.round_lengths()
        if window.width > 0 and window.height > 0:
            data = src.read(1, window=window)
            results[i] = int(np.bincount(data[data > 0].astype(int)).argmax()) if data.size > 0 else 3
        else:
            results[i] = 3
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True, help="City name (e.g. bengaluru)")
    parser.add_argument("--geotiff", default=None, help="Path to LULC GeoTIFF")
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_lulc(h3_indices, config, args.geotiff)
    print(f"  Source: {result['source']}")
    unique, counts = np.unique(result["data"], return_counts=True)
    for cls, cnt in zip(unique, counts):
        print(f"    {LULC_CLASSES.get(int(cls), 'unknown')}: {cnt} cells")
