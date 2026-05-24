"""
Compute boolean mask of H3 cells that fall within Special Economic Zones.

Reads SEZ boundary GeoJSON files referenced in the city config.

Usage:
    python scripts/preprocess/sez_zones.py --city bengaluru
"""
import argparse
import json
import os
import sys

import numpy as np
import h3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from engine.config import CityConfig  # noqa: E402


def compute_sez_masks(
    h3_indices: list[str],
    city_config: CityConfig,
) -> dict[str, np.ndarray]:
    """Return dict of {sez_name: boolean_mask} for this city."""
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    masks: dict[str, np.ndarray] = {}

    for zone in city_config.special_zones:
        zone_file = zone.get("file", "")
        zone_name = zone.get("name", "unknown")
        zone_path = os.path.join(DATA_DIR, zone_file)

        if not os.path.exists(zone_path):
            print(f"  SEZ boundary not found: {zone_path} (skipping)")
            continue

        try:
            with open(zone_path) as f:
                geojson = json.load(f)
        except Exception as e:
            print(f"  Error reading {zone_path}: {e}")
            continue

        features = geojson.get("features", [geojson])
        zone_indices: set[str] = set()
        for feat in features:
            geom = feat.get("geometry", feat)
            try:
                shape = h3.geo_to_h3shape(geom)
                cells = list(h3.h3shape_to_cells(shape, 8))
                zone_indices.update(cells)
            except Exception as e:
                print(f"  H3 polyfill error for {zone_name}: {e}")

        mask = np.array([idx in zone_indices for idx in h3_indices], dtype=bool)
        masks[zone_name] = mask
        print(f"  SEZ '{zone_name}': {int(mask.sum())} cells covered")

    return masks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"  Cells: {len(h3_indices)}")

    masks = compute_sez_masks(h3_indices, config)
    print(f"  Total SEZ zones: {len(masks)}")
