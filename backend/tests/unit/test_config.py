"""Tests for engine/config.py — CityConfig loading, boundary generation, and city listing."""
from __future__ import annotations

import pytest
import math

from engine.config import CityConfig, UrbanAnchor, list_available_cities


# ── Known cities ─────────────────────────────────────────────────────────────

ALL_CITIES = [
    "ahmedabad", "bengaluru", "bhubaneswar", "chandigarh", "chennai",
    "delhi_ncr", "hyderabad", "jaipur", "kolkata", "lucknow",
    "mumbai", "pune",
]


# ── Parameterized CityConfig.load() ─────────────────────────────────────────

class TestCityConfigLoad:

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_load_succeeds_for_each_city(self, city_name):
        cfg = CityConfig.load(city_name)
        assert cfg is not None
        assert isinstance(cfg, CityConfig)
        assert len(cfg.name) > 0

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_loaded_city_has_name_and_state(self, city_name):
        cfg = CityConfig.load(city_name)
        assert cfg.name, f"{city_name}: name is empty"
        assert cfg.state, f"{city_name}: state is empty"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_loaded_city_has_center(self, city_name):
        cfg = CityConfig.load(city_name)
        assert isinstance(cfg.center, list)
        assert len(cfg.center) == 2
        lat, lng = cfg.center
        assert 6.0 <= lat <= 38.0, f"{city_name}: lat {lat} out of India range"
        assert 68.0 <= lng <= 98.0, f"{city_name}: lng {lng} out of India range"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_loaded_city_has_positive_population(self, city_name):
        cfg = CityConfig.load(city_name)
        assert cfg.population > 0, f"{city_name}: population is {cfg.population}"


# ── FileNotFoundError for missing city ──────────────────────────────────────

class TestMissingCity:

    def test_load_raises_for_nonexistent_city(self):
        with pytest.raises(FileNotFoundError, match="City config not found"):
            CityConfig.load("atlantis_nonexistent")

    def test_load_raises_for_empty_string(self):
        with pytest.raises((FileNotFoundError, ValueError)):
            CityConfig.load("")

    def test_load_raises_for_wrong_case(self):
        """City names are lowercase; uppercase should fail."""
        with pytest.raises(FileNotFoundError):
            CityConfig.load("MUMBAI")


# ── get_boundary_polygon() ──────────────────────────────────────────────────

class TestBoundaryPolygon:

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_returns_valid_geojson_polygon(self, city_name):
        cfg = CityConfig.load(city_name)
        polygon = cfg.get_boundary_polygon()

        assert polygon["type"] == "Polygon"
        assert "coordinates" in polygon
        assert isinstance(polygon["coordinates"], list)
        assert len(polygon["coordinates"]) == 1  # single ring

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_polygon_ring_is_closed(self, city_name):
        """GeoJSON polygon ring should be closed (first == last point)."""
        cfg = CityConfig.load(city_name)
        polygon = cfg.get_boundary_polygon()
        ring = polygon["coordinates"][0]
        assert ring[0] == ring[-1], f"{city_name}: ring not closed"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_polygon_has_65_points(self, city_name):
        """64 segments + 1 closing point = 65."""
        cfg = CityConfig.load(city_name)
        polygon = cfg.get_boundary_polygon()
        ring = polygon["coordinates"][0]
        assert len(ring) == 65, f"{city_name}: expected 65 points, got {len(ring)}"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_polygon_coords_are_lng_lat_pairs(self, city_name):
        cfg = CityConfig.load(city_name)
        polygon = cfg.get_boundary_polygon()
        for point in polygon["coordinates"][0]:
            lng, lat = point
            assert isinstance(lng, float)
            assert isinstance(lat, float)

    def test_mega_city_larger_radius(self):
        """Cities with population > 10M should have 18km radius."""
        mumbai = CityConfig.load("mumbai")
        poly = mumbai.get_boundary_polygon()
        center_lat = mumbai.center[0]
        ring = poly["coordinates"][0]
        # ring[0] is at angle=0 (due east), so lng is max
        east_lng = ring[0][0]
        dlng = abs(east_lng - mumbai.center[1])
        expected_dlng = 18.0 / (111.32 * math.cos(math.radians(center_lat)))
        assert abs(dlng - expected_dlng) < 0.01

    def test_small_city_smaller_radius(self):
        """Cities with population <= 10M should have 14km radius."""
        chandigarh = CityConfig.load("chandigarh")
        assert chandigarh.population <= 10_000_000
        poly = chandigarh.get_boundary_polygon()
        center_lat = chandigarh.center[0]
        ring = poly["coordinates"][0]
        east_lng = ring[0][0]
        dlng = abs(east_lng - chandigarh.center[1])
        expected_dlng = 14.0 / (111.32 * math.cos(math.radians(center_lat)))
        assert abs(dlng - expected_dlng) < 0.01


# ── list_available_cities() ─────────────────────────────────────────────────

class TestListAvailableCities:

    def test_returns_12_cities(self):
        cities = list_available_cities()
        assert len(cities) == 12

    def test_each_city_has_required_keys(self):
        cities = list_available_cities()
        required_keys = {"id", "name", "state", "country", "population", "city_type", "center", "zoom"}
        for city in cities:
            assert required_keys.issubset(set(city.keys())), \
                f"{city.get('id')}: missing keys {required_keys - set(city.keys())}"

    def test_city_ids_match_known_list(self):
        cities = list_available_cities()
        ids = sorted(c["id"] for c in cities)
        assert ids == sorted(ALL_CITIES)

    def test_all_cities_are_india(self):
        cities = list_available_cities()
        for city in cities:
            assert city["country"] == "India"


# ── Urban anchors ────────────────────────────────────────────────────────────

class TestUrbanAnchors:

    def test_mumbai_has_multiple_anchors(self):
        cfg = CityConfig.load("mumbai")
        assert len(cfg.urban_anchors) > 1, "Mumbai should have multiple urban anchors"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_every_city_has_at_least_one_anchor(self, city_name):
        cfg = CityConfig.load(city_name)
        assert len(cfg.urban_anchors) >= 1, f"{city_name} has no urban anchors"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_anchors_are_urban_anchor_instances(self, city_name):
        cfg = CityConfig.load(city_name)
        for anchor in cfg.urban_anchors:
            assert isinstance(anchor, UrbanAnchor)

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_anchors_have_valid_coordinates(self, city_name):
        cfg = CityConfig.load(city_name)
        for anchor in cfg.urban_anchors:
            assert isinstance(anchor.lat, float), f"{city_name}/{anchor.name}: lat not float"
            assert isinstance(anchor.lng, float), f"{city_name}/{anchor.name}: lng not float"
            assert 6.0 <= anchor.lat <= 38.0
            assert 68.0 <= anchor.lng <= 98.0

    def test_mumbai_anchors_have_weights(self):
        cfg = CityConfig.load("mumbai")
        for anchor in cfg.urban_anchors:
            assert 0.0 < anchor.weight <= 1.0, \
                f"{anchor.name}: weight {anchor.weight} out of range"

    def test_anchor_type_is_valid(self):
        valid_types = {"cbd", "commercial", "industrial", "residential", "transport"}
        cfg = CityConfig.load("mumbai")
        for anchor in cfg.urban_anchors:
            assert anchor.type in valid_types, \
                f"{anchor.name}: invalid type '{anchor.type}'"


# ── Sector weights sum to 1.0 ───────────────────────────────────────────────

class TestSectorWeights:

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_sector_weights_sum_to_one(self, city_name):
        cfg = CityConfig.load(city_name)
        total = sum(cfg.sector_weights.values())
        assert abs(total - 1.0) < 0.01, \
            f"{city_name}: sector_weights sum to {total}, expected ~1.0"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_sector_weights_all_positive(self, city_name):
        cfg = CityConfig.load(city_name)
        for sector, weight in cfg.sector_weights.items():
            assert weight >= 0, f"{city_name}/{sector}: negative weight {weight}"

    @pytest.mark.parametrize("city_name", ALL_CITIES)
    def test_sector_weights_have_all_7_sectors(self, city_name):
        cfg = CityConfig.load(city_name)
        expected_sectors = {
            "it_ites", "manufacturing", "real_estate", "trade_hospitality",
            "transport_logistics", "informal", "public_admin",
        }
        assert expected_sectors == set(cfg.sector_weights.keys()), \
            f"{city_name}: missing sectors {expected_sectors - set(cfg.sector_weights.keys())}"


# ── Edge cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_caching_returns_same_instance(self):
        """lru_cache should return the same object for the same city."""
        cfg1 = CityConfig.load("mumbai")
        cfg2 = CityConfig.load("mumbai")
        assert cfg1 is cfg2

    def test_different_cities_are_different_objects(self):
        cfg_m = CityConfig.load("mumbai")
        cfg_b = CityConfig.load("bengaluru")
        assert cfg_m is not cfg_b
        assert cfg_m.name != cfg_b.name
