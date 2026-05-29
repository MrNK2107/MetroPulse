from __future__ import annotations

import functools
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# Decay rates per anchor type — tighter for CBD, looser for sprawl
ANCHOR_DECAY: dict[str, float] = {
    "cbd": 2.8,
    "commercial": 2.5,
    "industrial": 2.0,
    "residential": 1.8,
    "transport": 1.5,
}


@dataclass
class UrbanAnchor:
    """A named urban center that attracts economic activity."""
    name: str
    type: str  # cbd, commercial, industrial, residential, transport
    lat: float
    lng: float
    weight: float = 1.0


@dataclass
class CityConfig:
    name: str
    state: str
    country: str = "India"
    center: list[float] = field(default_factory=lambda: [20.5, 78.9])
    zoom: int = 10
    boundary_source: str = ""
    population: int = 1_000_000
    city_type: str = "generic"
    port_city: bool = False
    monsoon_season: list[int] = field(default_factory=lambda: [6, 7, 8, 9])
    metro_system: bool = False

    baselines: dict[str, Any] = field(default_factory=dict)
    sector_weights: dict[str, float] = field(default_factory=dict)
    constants: dict[str, float] = field(default_factory=dict)
    special_zones: list[dict[str, Any]] = field(default_factory=list)
    policies: dict[str, Any] = field(default_factory=dict)
    urban_anchors: list[UrbanAnchor] = field(default_factory=list)

    @classmethod
    @functools.lru_cache(maxsize=32)
    def load(cls, city_name: str) -> CityConfig:
        yaml_path = os.path.join(DATA_DIR, "cities", f"{city_name}.yaml")
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"City config not found: {yaml_path}")
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        # Parse urban_anchors from YAML (list of dicts → list of UrbanAnchor)
        raw_anchors = data.pop("urban_anchors", None)
        cfg = cls(**data)

        if raw_anchors:
            cfg.urban_anchors = [
                UrbanAnchor(
                    name=a.get("name", f"anchor_{i}"),
                    type=a.get("type", "cbd"),
                    lat=float(a.get("lat", cfg.center[0])),
                    lng=float(a.get("lng", cfg.center[1])),
                    weight=float(a.get("weight", 1.0)),
                )
                for i, a in enumerate(raw_anchors)
            ]
        else:
            # Auto-generate single CBD anchor from city center
            cfg.urban_anchors = [UrbanAnchor(
                name="CBD", type="cbd", lat=cfg.center[0], lng=cfg.center[1], weight=1.0
            )]

        # Warn about missing zone files
        for zone in cfg.special_zones:
            zone_file = zone.get("file")
            if zone_file:
                abs_path = os.path.join(DATA_DIR, "..", zone_file)
                if not os.path.exists(abs_path):
                    logger.warning("Zone file not found for %s: %s (using distance fallback)", cfg.name, zone_file)
        return cfg

    @classmethod
    @functools.lru_cache(maxsize=32)
    def load_geojson(cls, city_name: str) -> dict[str, Any]:
        geojson_path = os.path.join(DATA_DIR, "cities", f"{city_name}.geojson")
        if not os.path.exists(geojson_path):
            raise FileNotFoundError(f"City boundary not found: {geojson_path}")
        with open(geojson_path, "r") as f:
            return json.load(f)

    def get_boundary_polygon(self) -> dict[str, Any]:
        import math
        lat, lng = self.center
        # Set radius based on population size (mega-cities: 18km, others: 14km)
        radius_km = 18.0 if self.population > 10000000 else 14.0
        n_points = 64
        coords = []
        for i in range(n_points + 1):
            angle = 2 * math.pi * i / n_points
            dx = radius_km * math.cos(angle)
            dy = radius_km * math.sin(angle)
            
            # 1 degree of latitude is approx 111.32 km
            # 1 degree of longitude is approx 111.32 * cos(lat) km
            point_lat = lat + (dy / 111.32)
            point_lng = lng + (dx / (111.32 * math.cos(math.radians(lat))))
            coords.append([point_lng, point_lat])
            
        return {
            "type": "Polygon",
            "coordinates": [coords]
        }


def list_available_cities() -> list[dict[str, Any]]:
    cities_dir = os.path.join(DATA_DIR, "cities")
    result = []
    for f in sorted(os.listdir(cities_dir)):
        if f.endswith(".yaml"):
            city_name = f[:-5]
            try:
                cfg = CityConfig.load(city_name)
                result.append({
                    "id": city_name,
                    "name": cfg.name,
                    "state": cfg.state,
                    "country": cfg.country,
                    "population": cfg.population,
                    "city_type": cfg.city_type,
                    "center": cfg.center,
                    "zoom": cfg.zoom,
                })
            except Exception:
                pass
    return result
