"""
Seed regions and baseline data for development.

Usage:
  python scripts/seed_regions.py
"""
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

REGIONS: list[dict[str, Any]] = [
    {
        "name": "Manhattan",
        "city": "New York",
        "country": "US",
        "population": 1_600_000,
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [-74.025, 40.700],
                [-73.925, 40.700],
                [-73.925, 40.795],
                [-74.025, 40.795],
                [-74.025, 40.700],
            ]],
        },
        "baseline": {
            "gdp_index": 1.0,
            "unemployment": 0.04,
            "real_estate_idx": 1.0,
            "transit_load": 0.5,
        },
    },
    {
        "name": "Downtown Brooklyn",
        "city": "New York",
        "country": "US",
        "population": 750_000,
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [-73.990, 40.680],
                [-73.940, 40.680],
                [-73.940, 40.710],
                [-73.990, 40.710],
                [-73.990, 40.680],
            ]],
        },
        "baseline": {
            "gdp_index": 0.85,
            "unemployment": 0.055,
            "real_estate_idx": 0.8,
            "transit_load": 0.45,
        },
    },
]


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Warning: SUPABASE_URL or SUPABASE_KEY not set.")
        print("Seed data:")
        print(json.dumps(REGIONS, indent=2))
        return

    print(f"Prepared {len(REGIONS)} regions for seeding.")

    for region in REGIONS:
        baseline = region.pop("baseline")
        print(f"Region: {region['name']}, Baseline: {json.dumps(baseline)}")

    print("To insert, run: supabase db push")


if __name__ == "__main__":
    main()
