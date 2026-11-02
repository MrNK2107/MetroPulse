"""Export the 30 city configs into one JSON file the browser can load.

The Desk (Pulse, Alerts, Siting, Briefing) runs entirely in the browser, so it
needs each city's centre, population, anchor points and boundary. This script
reads data/cities/*.yaml and writes frontend/src/data/cities.json.

Boundary. The data/cities/*.geojson outlines are procedural and share one
template, so every city came out the same shape (and Chennai's reached into the
Bay of Bengal). The sample boundary is now drawn from the city's own config: a
core disc sized by population, joined to a disc around every anchor point within
reach, smoothed, with a small seeded wobble, and cut at the coast for the five
coastal cities. It is still a sample outline, not an administrative boundary.

Usage: python scripts/export_sample_cities.py
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CITIES = ROOT / "data" / "cities"
OUT = ROOT / "frontend" / "src" / "data" / "cities.json"

RAYS = 96  # boundary vertices
CORE_DENSITY = 6000  # residents per km2 used to size the core disc
CORE_MIN_KM, CORE_MAX_KM = 6.0, 14.0
ANCHOR_RADIUS_KM = 3.5
ANCHOR_REACH_KM = 28.0  # anchors further out (outlying SEZs, border posts) are left off the sample map
SMOOTH_DEG = 12

# Sea side of the coastline near the city: (lat, lng) of a point on the shore and
# the compass bearing (degrees clockwise from north) pointing out to sea.
COASTS: dict[str, tuple[float, float, float]] = {
    "chennai": (13.08, 80.3, 90),
    "mumbai": (19.0, 72.815, 270),
    "kochi": (9.96, 76.24, 270),
    "visakhapatnam": (17.714, 83.323, 135),
    "surat": (21.17, 72.62, 270),
}


def _seed(text: str) -> float:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def _envelope(city_id: str, center: tuple[float, float], population: int, anchors: list[dict]) -> list[list[float]]:
    lat0, lng0 = center
    kx = 111.32 * math.cos(math.radians(lat0))
    ky = 110.57
    core = min(CORE_MAX_KM, max(CORE_MIN_KM, math.sqrt(population / CORE_DENSITY / math.pi)))
    discs = [(0.0, 0.0, core)]
    for a in anchors:
        x, y = (a["lng"] - lng0) * kx, (a["lat"] - lat0) * ky
        if math.hypot(x, y) <= ANCHOR_REACH_KM:
            discs.append((x, y, ANCHOR_RADIUS_KM))

    # star-shaped union: along each ray from the centre, the far edge of the furthest disc it crosses
    radii = []
    for k in range(RAYS):
        t = 2 * math.pi * k / RAYS
        ux, uy = math.cos(t), math.sin(t)
        r = core
        for x, y, rad in discs:
            along = x * ux + y * uy
            perp2 = (x * x + y * y) - along * along
            if along > 0 and perp2 < rad * rad:
                r = max(r, along + math.sqrt(rad * rad - perp2))
        radii.append(r)

    # smooth (circular moving average), then a gentle seeded wobble so no two cities match
    w = max(1, round(SMOOTH_DEG / (360 / RAYS)))
    smooth = [sum(radii[(k + j) % RAYS] for j in range(-w, w + 1)) / (2 * w + 1) for k in range(RAYS)]
    p1, p2 = 2 * math.pi * _seed(city_id + ":a"), 2 * math.pi * _seed(city_id + ":b")
    ring = []
    coast = COASTS.get(city_id)
    for k in range(RAYS):
        t = 2 * math.pi * k / RAYS
        r = smooth[k] * (1 + 0.06 * math.sin(3 * t + p1) + 0.04 * math.sin(5 * t + p2))
        ux, uy = math.cos(t), math.sin(t)
        if coast:
            # cut the ray at the shoreline: a line through the shore point, normal pointing to sea
            clat, clng, bearing = coast
            sx, sy = (clng - lng0) * kx, (clat - lat0) * ky
            nx, ny = math.sin(math.radians(bearing)), math.cos(math.radians(bearing))
            dot = ux * nx + uy * ny
            if dot > 1e-6:
                r = min(r, (sx * nx + sy * ny) / dot)
        ring.append([round(lng0 + r * ux / kx, 5), round(lat0 + r * uy / ky, 5)])
    ring.append(ring[0])
    return ring


def main() -> None:
    cities = []
    for yml in sorted(CITIES.glob("*.yaml")):
        cfg = yaml.safe_load(yml.read_text(encoding="utf-8"))
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
        center = (float(cfg["center"][0]), float(cfg["center"][1]))
        population = int(cfg.get("population", 1_000_000))
        cities.append(
            {
                "id": yml.stem,
                "name": cfg["name"],
                "state": cfg.get("state", ""),
                "center": list(center),
                "population": population,
                "metro": bool(cfg.get("metro_system", False)),
                "anchors": anchors,
                "boundary": _envelope(yml.stem, center, population, anchors),
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cities, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cities)} cities to {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
