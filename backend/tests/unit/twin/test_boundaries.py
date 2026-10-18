import json

import geopandas as gpd

from twin.places.boundaries import build_district_boundaries, dissolve_levels, write_boundaries


def test_every_lgd_district_gets_geometry_and_misspelling_matches(fx, places, resolver):
    gdf, unmatched, _ = build_district_boundaries(fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver)
    assert unmatched == []
    assert set(gdf.place_id) == set(places[places.level == "district"].place_id)


def test_clip_removes_area_outside_outline(fx, places, resolver):
    gdf, _, _ = build_district_boundaries(fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver)
    outline = gpd.read_file(fx / "soi_outline.geojson").union_all()
    assert gdf.geometry.apply(lambda g: g.difference(outline).area).max() < 1e-9
    assert set(gdf.geometry.geom_type) == {"MultiPolygon"}


def test_dissolve_and_write(tmp_path, fx, places, resolver):
    gdf, _, _ = build_district_boundaries(fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver)
    levels = dissolve_levels(gdf, places)
    assert len(levels["country"]) == 1
    assert len(levels["state"]) == 4
    write_boundaries(levels, tmp_path)
    fc = json.loads((tmp_path / "boundaries_district.geojson").read_text())
    assert {"place_id", "name"} <= set(fc["features"][0]["properties"])
    assert (tmp_path / "boundaries_state.parquet").exists()


def test_unresolvable_district_is_reported(tmp_path, fx, places, resolver):
    src = json.loads((fx / "soi_districts.geojson").read_text())
    src["features"][0]["properties"]["DISTRICT"] = "ZZZZ NOWHERE"
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps(src))
    gdf, unmatched, _ = build_district_boundaries(p, fx / "soi_outline.geojson", places, resolver)
    assert unmatched == ["ZZZZ NOWHERE"]
    assert len(gdf) == 7


def _written_districts(tmp_path, fx, places, resolver):
    gdf, _, _ = build_district_boundaries(fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver)
    write_boundaries(dissolve_levels(gdf, places), tmp_path)
    return gpd.read_file(tmp_path / "boundaries_district.geojson")


def test_written_geojson_keeps_shared_borders(tmp_path, fx, places, resolver):
    out = _written_districts(tmp_path, fx, places, resolver)
    raw = json.loads((tmp_path / "boundaries_district.geojson").read_text())
    assert {f["geometry"]["type"] for f in raw["features"]} == {"MultiPolygon"}
    by_name = out.set_index("name").geometry
    for a, b in [("Gaya", "Aurangabad"), ("Mumbai", "Chhatrapati Sambhajinagar")]:
        ga, gb = by_name[a], by_name[b]
        assert ga.intersection(gb).area < 1e-9
        assert ga.intersection(gb).length > 0
        assert abs(ga.union(gb).area - (ga.area + gb.area)) < 1e-9


def test_bowtie_geometry_is_repaired(tmp_path, fx, places, resolver):
    src = json.loads((fx / "soi_districts.geojson").read_text())
    src["features"][0]["geometry"]["coordinates"] = [[[72, 15], [73, 16], [73, 15], [72, 16], [72, 15]]]
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps(src))
    gdf, unmatched, _ = build_district_boundaries(p, fx / "soi_outline.geojson", places, resolver)
    assert unmatched == []
    assert gdf.geometry.is_valid.all()
    assert not gdf.geometry.is_empty.any()


def test_multipart_district_dissolves_to_one_row(tmp_path, fx, places, resolver):
    src = json.loads((fx / "soi_districts.geojson").read_text())
    dup = json.loads(json.dumps(src["features"][0]))
    dup["geometry"]["coordinates"] = [[[72, 17], [73, 17], [73, 18], [72, 18], [72, 17]]]
    src["features"].append(dup)
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps(src))
    gdf, unmatched, _ = build_district_boundaries(p, fx / "soi_outline.geojson", places, resolver)
    assert unmatched == []
    assert len(gdf) == 8 and gdf.place_id.is_unique
    assert len(gdf) == len(places[places.level == "district"])


def _with_features(tmp_path, fx, edit):
    src = json.loads((fx / "soi_districts.geojson").read_text())
    edit(src["features"])
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps(src))
    return p


def _feature(features, name):
    return next(f for f in features if f["properties"]["DISTRICT"] == name)


def test_single_digit_state_matches_via_alias(fx, places, resolver):
    gdf, unmatched, fuzzy = build_district_boundaries(
        fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver
    )
    gurugram = places[(places.level == "district") & (places.name == "Gurugram")].iloc[0]
    assert gurugram.parent_id == "state:06" and gurugram.state_code == "06"
    assert gurugram.place_id in set(gdf.place_id)
    assert unmatched == [] and fuzzy == []


def test_accepted_fuzzy_match_is_listed_for_review(tmp_path, fx, places, resolver):
    def edit(fs):
        _feature(fs, "NEWPUR")["properties"]["DISTRICT"] = "NEWPURR"

    p = _with_features(tmp_path, fx, edit)
    gdf, unmatched, fuzzy = build_district_boundaries(p, fx / "soi_outline.geojson", places, resolver)
    assert unmatched == [] and fuzzy == [("NEWPURR", "Newpur")]
    assert "district:999" in set(gdf.place_id)


def test_fuzzy_match_colliding_with_exact_is_refused(tmp_path, fx, places, resolver):
    def edit(fs):
        extra = json.loads(json.dumps(_feature(fs, "PATNA")))
        extra["properties"]["DISTRICT"] = "PATNA CITY"
        extra["geometry"]["coordinates"] = [[[72, 17], [73, 17], [73, 18], [72, 18], [72, 17]]]
        fs.append(extra)

    p = _with_features(tmp_path, fx, edit)
    gdf, unmatched, fuzzy = build_district_boundaries(p, fx / "soi_outline.geojson", places, resolver)
    assert sorted(unmatched) == ["PATNA", "PATNA CITY"] and fuzzy == []
    assert "district:217" not in set(gdf.place_id)


def test_east_west_pair_fuzzy_to_one_place_is_refused(tmp_path, fx, places, resolver):
    def edit(fs):
        west = _feature(fs, "PATNA")
        east = json.loads(json.dumps(west))
        west["properties"]["DISTRICT"] = "WEST PATNA"
        east["properties"]["DISTRICT"] = "EAST PATNA"
        east["geometry"]["coordinates"] = [[[72, 17], [73, 17], [73, 18], [72, 18], [72, 17]]]
        fs.append(east)

    p = _with_features(tmp_path, fx, edit)
    gdf, unmatched, fuzzy = build_district_boundaries(p, fx / "soi_outline.geojson", places, resolver)
    assert sorted(unmatched) == ["EAST PATNA", "WEST PATNA"] and fuzzy == []
