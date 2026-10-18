import pytest

from tests.unit.twin.conftest import fixture_inputs
from twin.paths import TwinPaths
from twin.places.build import build_backbone, load_backbone
from twin.store.parquet_store import read_current


def test_build_backbone_end_to_end(fx, tmp_paths):
    rep = build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    assert rep.unmatched_boundaries == [] and rep.districts == 7
    assert rep.districts_without_boundary == 0
    ctx = load_backbone(tmp_paths)
    assert {"district", "state", "country"} <= set(ctx.boundaries)
    assert ctx.crosswalk is not None and len(ctx.crosswalk) > 0
    assert read_current(tmp_paths)["places"] == "lgd-test"
    d = tmp_paths.places_dir("lgd-test")
    for name in ("places.parquet", "aliases.parquet", "crosswalk_census2011.parquet",
                 "h3_index.parquet", "boundaries_district.parquet",
                 "boundaries_district.geojson"):
        assert (d / name).exists(), name


def test_districts_without_census2011_link(fx, tmp_paths):
    rep = build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    assert rep.districts_without_census2011_link == 1  # Newpur only


def test_load_backbone_not_built(tmp_path):
    with pytest.raises(FileNotFoundError, match="backbone"):
        load_backbone(TwinPaths(tmp_path / "empty"))


def test_rebuild_replaces_dir_cleanly(fx, tmp_paths):
    build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    d = tmp_paths.places_dir("lgd-test")
    (d / "stale.txt").write_text("x")
    build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    assert not (d / "stale.txt").exists()
    assert (d / "places.parquet").exists()
    assert [p.name for p in d.parent.iterdir()] == ["lgd-test"]


def test_integer_census_codes_are_zero_padded(fx, tmp_path):
    import json

    from twin.places.build import _load_census2011

    d = json.loads((fx / "census2011_districts.geojson").read_text())
    for f in d["features"]:
        f["properties"]["ST_CEN_CD"] = int(f["properties"]["ST_CEN_CD"])
        f["properties"]["DT_CEN_CD"] = int(f["properties"]["DT_CEN_CD"])
    d["features"][0]["properties"].update(ST_CEN_CD=7, DT_CEN_CD=5.0)
    p = tmp_path / "c.geojson"
    p.write_text(json.dumps(d))
    ids = set(_load_census2011(p).place_id)
    assert "census2011_district:07005" in ids
    assert "census2011_district:27522" in ids
