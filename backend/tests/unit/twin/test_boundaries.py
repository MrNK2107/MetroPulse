import json

import geopandas as gpd

from twin.places.boundaries import build_district_boundaries, dissolve_levels, write_boundaries


def test_every_lgd_district_gets_geometry_and_misspelling_matches(fx, places, resolver):
    gdf, unmatched = build_district_boundaries(fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver)
    assert unmatched == []
    assert set(gdf.place_id) == set(places[places.level == "district"].place_id)


def test_clip_removes_area_outside_outline(fx, places, resolver):
    gdf, _ = build_district_boundaries(fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver)
    outline = gpd.read_file(fx / "soi_outline.geojson").union_all()
    assert gdf.geometry.apply(lambda g: g.difference(outline).area).max() < 1e-9
    assert set(gdf.geometry.geom_type) == {"MultiPolygon"}


def test_dissolve_and_write(tmp_path, fx, places, resolver):
    gdf, _ = build_district_boundaries(fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver)
    levels = dissolve_levels(gdf, places)
    assert len(levels["country"]) == 1
    assert len(levels["state"]) == 3
    write_boundaries(levels, tmp_path)
    fc = json.loads((tmp_path / "boundaries_district.geojson").read_text())
    assert {"place_id", "name"} <= set(fc["features"][0]["properties"])
    assert (tmp_path / "boundaries_state.parquet").exists()


def test_unresolvable_district_is_reported(tmp_path, fx, places, resolver):
    src = json.loads((fx / "soi_districts.geojson").read_text())
    src["features"][0]["properties"]["DISTRICT"] = "ZZZZ NOWHERE"
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps(src))
    gdf, unmatched = build_district_boundaries(p, fx / "soi_outline.geojson", places, resolver)
    assert unmatched == ["ZZZZ NOWHERE"]
    assert len(gdf) == 6
