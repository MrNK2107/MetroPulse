"""
Aggregate population density from ward-level census data into H3 cells.

Reads a ward boundary GeoJSON with population attribute, performs
area-weighted interpolation to assign population to each H3 cell.

Fallback: synthetic exponential decay from city center.

Usage:
    python scripts/preprocess/census_to_h3.py --city bengaluru --wards wards.geojson
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


def _synthetic_population(
    h3_indices: list[str],
    city_config: CityConfig,
) -> np.ndarray:
    """Synthetic population density decaying from CBD, with peak density ~3km out."""
    center_lat, center_lon = city_config.center
    lats = np.array([h3.cell_to_latlng(idx)[0] for idx in h3_indices])
    lons = np.array([h3.cell_to_latlng(idx)[1] for idx in h3_indices])
    d_cbd = _haversine_vec(lats, lons, center_lat, center_lon)

    peak_density = city_config.population / 100.0
    density = peak_density * (d_cbd + 0.5) * np.exp(-d_cbd / 4.0)
    density = density / np.max(density) * 15000  # scale to ~15k/km2 peak
    return density.astype(np.float64)


def compute_population_density(
    h3_indices: list[str],
    city_config: CityConfig,
    wards_path: str | None = None,
    population_field: str = "population",
) -> dict[str, Any]:
    if wards_path and os.path.exists(wards_path):
        try:
            import geopandas as gpd
            from shapely.geometry import Polygon as ShapelyPolygon
            from shapely.geometry import Point

            wards = gpd.read_file(wards_path)
            if population_field not in wards.columns:
                raise KeyError(f"Field '{population_field}' not in ward data")

            densities = np.zeros(len(h3_indices), dtype=np.float64)
            areas = np.zeros(len(h3_indices), dtype=np.float64)

            for i, idx in enumerate(h3_indices):
                boundary = h3.cell_to_boundary(idx)
                coords = [(lon, lat) for lat, lon in boundary]
                h3_poly = ShapelyPolygon(coords)

                hits = wards[wards.intersects(h3_poly)]
                if len(hits) == 0:
                    densities[i] = 0
                    continue

                total_pop = 0
                total_area = 0
                for _, ward in hits.iterrows():
                    inter = ward.geometry.intersection(h3_poly)
                    if inter.area > 0:
                        ward_pop = ward[population_field]
                        ward_area = ward.geometry.area
                        ratio = inter.area / ward_area if ward_area > 0 else 0
                        total_pop += ward_pop * ratio
                        total_area += inter.area

                densities[i] = total_pop / max(total_area, 1e-10) if total_area > 0 else 0
                areas[i] = total_area

            return {"source": "wards", "data": densities, "unit": "pop_per_km2"}

        except Exception as e:
            print(f"  Ward processing failed ({e}), using synthetic")

    data = _synthetic_population(h3_indices, city_config)
    return {"source": "synthetic", "data": data, "unit": "pop_per_km2"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--wards", default=None)
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    result = compute_population_density(h3_indices, config, args.wards)
    print(f"  Source: {result['source']}")
    print(f"  Max density: {float(np.max(result['data'])):.1f} / km2")
