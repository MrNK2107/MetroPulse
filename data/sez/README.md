# SEZ Data

This directory is a placeholder for Special Economic Zone boundary GeoJSON files. The simulation engine uses distance-based zone detection when real boundaries are unavailable.

To use real data, place GeoJSON boundary files here (e.g., `hitec_city.geojson`, `genome_valley.geojson`) and run `scripts/preprocess/sez_zones.py --city <name>`.
