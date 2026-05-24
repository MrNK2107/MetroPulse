from __future__ import annotations

import functools
import json
import os
from dataclasses import dataclass, field
from typing import Any

import yaml

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


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

    @classmethod
    @functools.lru_cache(maxsize=32)
    def load(cls, city_name: str) -> CityConfig:
        yaml_path = os.path.join(DATA_DIR, "cities", f"{city_name}.yaml")
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"City config not found: {yaml_path}")
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    @functools.lru_cache(maxsize=32)
    def load_geojson(cls, city_name: str) -> dict[str, Any]:
        geojson_path = os.path.join(DATA_DIR, "cities", f"{city_name}.geojson")
        if not os.path.exists(geojson_path):
            raise FileNotFoundError(f"City boundary not found: {geojson_path}")
        with open(geojson_path, "r") as f:
            return json.load(f)

    def get_boundary_polygon(self) -> dict[str, Any]:
        geojson = self.load_geojson(self.name.lower().replace(" ", "_"))
        features = geojson.get("features", [])
        if features:
            return features[0]["geometry"]
        raise ValueError(f"No features in GeoJSON for {self.name}")


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
