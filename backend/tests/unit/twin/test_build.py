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
    assert rep.districts_without_census2011_link == 2  # Newpur + Chhatrapati Sambhajinagar (no 2011 geometry in fixture)


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
