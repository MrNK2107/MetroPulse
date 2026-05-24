"""
Orchestrate all preprocessing for a given city and save cached .npy files.

Usage:
    python scripts/preprocess/build_city_cache.py --city bengaluru
    python scripts/preprocess/build_city_cache.py --city mumbai --all

Optional flags:
    --lulc-geotiff    Path to LULC GeoTIFF
    --dem             Path to SRTM DEM GeoTIFF
    --nightlights     Path to VIIRS nightlights GeoTIFF
    --wards           Path to ward boundary GeoJSON
    --slums           Path to slum boundary GeoJSON
    --stations        Path to transit stations GeoJSON
"""
import argparse
import os
import sys
import json

import numpy as np
import h3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from engine.config import CityConfig  # noqa: E402

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cities")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--lulc-geotiff", default=None)
    parser.add_argument("--dem", default=None)
    parser.add_argument("--nightlights", default=None)
    parser.add_argument("--wards", default=None)
    parser.add_argument("--slums", default=None)
    parser.add_argument("--stations", default=None)
    args = parser.parse_args()

    config = CityConfig.load(args.city)
    boundary = config.get_boundary_polygon()
    h3_indices = list(h3.geo_to_h3shape(boundary).h3shape_to_cells(8))
    print(f"[{args.city}] H3 cells at res 8: {len(h3_indices)}")

    os.makedirs(CACHE_DIR, exist_ok=True)

    # 1. LULC
    from lulc_to_h3 import compute_lulc
    lulc = compute_lulc(h3_indices, config, args.lulc_geotiff)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_lulc.npy"), lulc["data"])
    print(f"  LULC: {lulc['source']}, saved")

    # 2. Road proximity
    from road_proximity import compute_road_proximity
    road = compute_road_proximity(h3_indices, config)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_road_dist.npy"), road["data"])
    print(f"  Roads: {road['source']}, saved")

    # 3. Transit distance
    from transit_nodes import compute_transit_distance
    transit = compute_transit_distance(h3_indices, config, args.stations)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_transit_dist.npy"), transit["data"])
    print(f"  Transit: {transit['source']}, saved")

    # 4. Population density
    from census_to_h3 import compute_population_density
    pop = compute_population_density(h3_indices, config, args.wards)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_population_density.npy"), pop["data"])
    print(f"  Population: {pop['source']}, saved")

    # 5. Economic activity (night lights)
    from nl_to_baseline import compute_economic_activity
    econ = compute_economic_activity(h3_indices, config, args.nightlights)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_economic_activity.npy"), econ["data"])
    print(f"  Economic activity: {econ['source']}, saved")

    # 6. SEZ masks
    from sez_zones import compute_sez_masks
    sez = compute_sez_masks(h3_indices, config)
    sez_dict = {name: mask.tolist() for name, mask in sez.items()}
    np.save(os.path.join(CACHE_DIR, f"{args.city}_sez_masks.npy"), sez_dict)
    print(f"  SEZ: {len(sez)} zones, saved")

    # 7. Slum flags
    from slum_boundaries import compute_slum_flags
    slum = compute_slum_flags(h3_indices, config, args.slums)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_slum_flags.npy"), slum["data"])
    print(f"  Slums: {slum['source']}, saved")

    # 8. Flood risk
    from flood_risk import compute_flood_risk
    flood = compute_flood_risk(h3_indices, config, args.dem)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_flood_risk.npy"), flood["data"])
    print(f"  Flood risk: {flood['source']}, saved")

    # 9. Elevation
    from elevation import compute_elevation
    elev = compute_elevation(h3_indices, config, args.dem)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_elevation.npy"), elev["data"])
    print(f"  Elevation: {elev['source']}, saved")

    # 10. H3 indices (reference)
    np.save(os.path.join(CACHE_DIR, f"{args.city}_h3_indices.npy"), np.array(h3_indices))
    print(f"  H3 indices saved")

    print(f"\n[{args.city}] Cache build complete. {len(h3_indices)} cells.")


if __name__ == "__main__":
    main()
