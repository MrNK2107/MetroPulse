"""Export the 30 city configs into one JSON file the browser can load.

The Desk (Pulse, Alerts, Siting, Briefing) runs entirely in the browser, so it
needs each city's centre, population, anchor points and boundary. This script
reads data/cities/*.yaml and *.geojson and writes frontend/src/data/cities.json.

Usage: python scripts/export_sample_cities.py
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CITIES = ROOT / "data" / "cities"
OUT = ROOT / "frontend" / "src" / "data" / "cities.json"
MAX_RING_POINTS = 96


def _ring(geojson_path: Path) -> list[list[float]]:
    gj = json.loads(geojson_path.read_text(encoding="utf-8"))
    feature = gj["features"][0] if gj.get("type") == "FeatureCollection" else gj
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
    else:  # MultiPolygon: keep the largest outer ring
        ring = max((p[0] for p in geom["coordinates"]), key=len)
    step = max(1, len(ring) // MAX_RING_POINTS)
    out = [[round(x, 5), round(y, 5)] for x, y in ring[::step]]
    if out[0] != out[-1]:
        out.append(out[0])
    return out


def main() -> None:
    cities = []
    for yml in sorted(CITIES.glob("*.yaml")):
        cfg = yaml.safe_load(yml.read_text(encoding="utf-8"))
        gj = yml.with_suffix(".geojson")
        if not gj.exists():
            continue
        anchors = [
            {
                "name": a["name"],
                "type": a["type"],
                "lat": float(a["lat"]),
                "lng": float(a["lng"]),
                "weight": float(a.get("weight", 0.1)),
            }
            for a in (cfg.get("urban_anchors") or []) + (cfg.get("special_zones") or [])
            if "lat" in a and "lng" in a
        ]
        cities.append(
            {
                "id": yml.stem,
                "name": cfg["name"],
                "state": cfg.get("state", ""),
                "center": [float(cfg["center"][0]), float(cfg["center"][1])],
                "population": int(cfg.get("population", 1_000_000)),
                "metro": bool(cfg.get("metro_system", False)),
                "anchors": anchors,
                "boundary": _ring(gj),
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cities, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cities)} cities to {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
