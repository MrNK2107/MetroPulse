import pytest

from tests.unit.twin.conftest import fixture_inputs
from twin.paths import TwinPaths
from twin.places.build import build_backbone, load_backbone
from twin.store.parquet_store import read_current


def test_build_backbone_end_to_end(fx, tmp_paths):
    rep = build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    assert rep.unmatched_boundaries == [] and rep.districts == 8
    assert rep.states == 4 and rep.fuzzy_matches == []
    assert rep.districts_without_boundary == 0
    # build_backbone never switches CURRENT; the caller does once its gates pass
    assert "places" not in read_current(tmp_paths)
    with pytest.raises(FileNotFoundError):
        load_backbone(tmp_paths)
    ctx = load_backbone(tmp_paths, boundary_version="lgd-test")
    assert ctx.places_version == "lgd-test"
    assert {"district", "state", "country"} <= set(ctx.boundaries)
    assert ctx.crosswalk is not None and len(ctx.crosswalk) > 0
    d = tmp_paths.places_dir("lgd-test")
    for name in ("places.parquet", "aliases.parquet", "crosswalk_census2011.parquet",
                 "h3_index.parquet", "boundaries_district.parquet",
                 "boundaries_district.geojson", "places_digest.txt"):
        assert (d / name).exists(), name


def test_districts_without_census2011_link(fx, tmp_paths):
    rep = build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    assert rep.districts_without_census2011_link == 2  # Newpur and Gurugram


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
    gdf, dropped = _load_census2011(p)
    ids = set(gdf.place_id)
    assert dropped == 0
    assert "census2011_district:07005" in ids
    assert "census2011_district:27522" in ids


def test_report_diagnostics_on_fixtures(fx, tmp_paths):
    from twin.places.build import places_digest

    rep = build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    assert rep.census_code_disagreements == 0
    assert rep.census2011_polygons_without_code == 0
    # 2011 Mumbai pokes 0.002 deg past the clipped current Mumbai into a dropped sliver
    assert rep.min_coverage_ratio == pytest.approx(1 / 1.002, rel=1e-3)
    d = tmp_paths.places_dir("lgd-test")
    assert rep.places_version == "lgd-test"
    assert rep.places_digest == (d / "places_digest.txt").read_text() == places_digest(d)


def test_census_code_disagreement_counted(fx, tmp_path, tmp_paths):
    import dataclasses

    lgd = tmp_path / "districts.csv"
    lgd.write_text((fx / "lgd_districts.csv").read_text().replace("Patna,226", "Patna,228"))
    inputs = dataclasses.replace(fixture_inputs(fx), lgd_districts=lgd)
    assert build_backbone(inputs, tmp_paths, "lgd-test").census_code_disagreements == 1


def test_2011_polygon_without_code_dropped_and_counted(fx, tmp_path, tmp_paths):
    import dataclasses
    import json

    d = json.loads((fx / "census2011_districts.geojson").read_text())
    extra = json.loads(json.dumps(d["features"][0]))
    extra["properties"]["DT_CEN_CD"] = None
    d["features"].append(extra)
    p = tmp_path / "c.geojson"
    p.write_text(json.dumps(d))
    inputs = dataclasses.replace(fixture_inputs(fx), census2011_districts=p)
    with pytest.warns(UserWarning, match="1 Census 2011 polygon"):
        rep = build_backbone(inputs, tmp_paths, "lgd-test")
    assert rep.census2011_polygons_without_code == 1


def test_rebuilding_same_version_with_changed_places_changes_dataset_version(fx, tmp_path, tmp_paths):
    import dataclasses
    import json
    import shutil

    from app.data_registry import SOURCE_REGISTRY
    from twin.pipeline.base import run_pipeline
    from twin.pipeline.census2011 import Census2011Adapter

    (tmp_paths.manual / "census2011").mkdir(parents=True)
    shutil.copy2(fx / "pca_district.csv", tmp_paths.manual / "census2011" / "pca_district.csv")
    known = {s.id for s in SOURCE_REGISTRY}

    def build_and_run(inputs):
        build_backbone(inputs, tmp_paths, "lgd-test")
        ctx = load_backbone(tmp_paths, known, boundary_version="lgd-test")
        return run_pipeline(Census2011Adapter(), ctx).dataset_version

    base = fixture_inputs(fx)
    v1 = build_and_run(base)
    assert build_and_run(base) == v1  # identical rebuild reuses the dataset

    src = json.loads((fx / "soi_districts.geojson").read_text())
    newpur = next(f for f in src["features"] if f["properties"]["DISTRICT"] == "NEWPUR")
    newpur["geometry"]["coordinates"] = [[[77, 15], [78.2, 15], [78.2, 16], [77, 16], [77, 15]]]
    soi = tmp_path / "soi.geojson"
    soi.write_text(json.dumps(src))
    v2 = build_and_run(dataclasses.replace(base, soi_districts=soi))
    assert v2 != v1

    # LGD renames Newpur; an alias keeps the SoI feature matched; places content changes
    lgd = tmp_path / "districts.csv"
    lgd.write_text((fx / "lgd_districts.csv").read_text().replace("Newpur", "Navapur"))
    al = tmp_path / "aliases.csv"
    al.write_text((fx / "aliases.csv").read_text() + "newpur,navapur,10\n")
    v3 = build_and_run(dataclasses.replace(base, lgd_districts=lgd, aliases=al))
    assert v3 not in (v1, v2)
