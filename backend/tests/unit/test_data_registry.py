from app.data_registry import (
    SOURCE_REGISTRY,
    city_dataset_manifest,
    list_national_cities,
)


def test_registry_covers_major_and_capital_cities():
    cities = list_national_cities()
    ids = {city["id"] for city in cities}
    assert len(cities) >= 60
    assert {"mumbai", "delhi_ncr", "bengaluru", "aizawl", "kavaratti", "port_blair"} <= ids


def test_registry_is_honest_about_simulation_readiness():
    cities = {city["id"]: city for city in list_national_cities()}
    assert cities["bengaluru"]["simulationReady"] is True
    assert cities["aizawl"]["simulationReady"] is False
    assert cities["aizawl"]["population"] is None
    assert cities["aizawl"]["coverageLabel"] == "limited"


def test_dataset_manifest_has_explicit_fallback_and_sources():
    manifest = city_dataset_manifest("bengaluru")
    assert manifest is not None
    assert manifest["fallbackOrder"] == ["city", "district", "state", "national", "synthetic"]
    assert set(manifest["domains"]) == {
        "population", "economy", "land_use", "mobility", "housing", "climate", "environment"
    }
    assert len(SOURCE_REGISTRY) >= 10

