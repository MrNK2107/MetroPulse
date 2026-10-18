from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.twin import get_twin_paths
from tests.unit.twin.conftest import NEW_DISTRICT_ID, Y_ID, make_fixture_manual_paths

FX = Path(__file__).parents[1] / "fixtures" / "twin"


@pytest.fixture(scope="module")
def built_paths(tmp_path_factory):
    from scripts.twin_build import main

    paths = make_fixture_manual_paths(tmp_path_factory.mktemp("twinapi"), FX)
    assert main(["build", "--boundary-version", "lgd-test"], paths=paths) == 0
    return paths


@pytest.fixture
def client(built_paths):
    app.dependency_overrides[get_twin_paths] = lambda: built_paths
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def gaya_id():
    return Y_ID


@pytest.fixture
def district_without_census_id():
    return NEW_DISTRICT_ID


def test_resolve_ambiguous(client):
    body = client.get("/api/twin/places/resolve", params={"q": "Aurangabad", "level": "district"}).json()
    assert body["success"] and body["data"]["ambiguous"] is True


def test_observations_have_receipts(client, gaya_id):
    body = client.get(f"/api/twin/places/{gaya_id}/observations").json()
    assert body["meta"]["places_version"] == "lgd-test"
    rows = body["data"]
    pop = next(r for r in rows if r["indicator"] == "population_total")
    assert pop["value"] > 0 and pop["receipt"]["source_id"] == "census2011-pca-district"
    assert pop["receipt"]["license"]
    assert [r["indicator"] for r in rows] == sorted(r["indicator"] for r in rows)


def test_missing_value_is_null_not_zero(client, district_without_census_id):
    rows = client.get(f"/api/twin/places/{district_without_census_id}/observations").json()["data"]
    pop = next(r for r in rows if r["indicator"] == "population_total")
    assert pop["value"] is None and pop["period"] is None and pop["trust_label"] is None
    assert pop["receipt"]["dataset_version"]


def test_boundaries_geojson(client):
    r = client.get("/api/twin/boundaries/district")
    assert r.status_code == 200 and r.json()["type"] == "FeatureCollection"
    assert r.headers["cache-control"] == "public, max-age=86400"
    assert r.headers["content-type"].startswith("application/geo+json")
    assert client.get("/api/twin/boundaries/ward").status_code == 404


def test_unknown_place_404_envelope(client):
    r = client.get("/api/twin/places/district:99999")
    assert r.status_code == 404 and r.json()["success"] is False


def test_place_detail(client, gaya_id):
    d = client.get(f"/api/twin/places/{gaya_id}").json()["data"]
    assert d["name"] == "Gaya" and d["state"]["name"] == "Bihar"


def test_indicators_listed(client):
    ids = {i["id"] for i in client.get("/api/twin/indicators").json()["data"]}
    assert {"population_total", "nightlights_radiance_sum"} <= ids


def test_q_too_long_422(client):
    r = client.get("/api/twin/places/resolve", params={"q": "a" * 101})
    body = r.json()
    assert r.status_code == 422 and body["success"] is False
    assert isinstance(body["error"], str) and body["error"]
    assert body["data"] is None


def test_non_twin_422_keeps_default_shape(client):
    r = client.get("/api/data-sources")
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)


def test_503_when_not_built(tmp_path):
    from twin.paths import TwinPaths

    app.dependency_overrides[get_twin_paths] = lambda: TwinPaths(tmp_path / "empty")
    try:
        r = TestClient(app).get("/api/twin/indicators")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503 and r.json()["success"] is False
    assert r.json()["error"] == "twin data not built — run scripts/twin_build.py build"
