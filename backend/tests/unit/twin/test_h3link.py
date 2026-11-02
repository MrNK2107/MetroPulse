import geopandas as gpd
import h3
from shapely.geometry import MultiPolygon, box

from twin.places.h3link import build_h3_index


def test_every_district_has_cells_at_each_res(districts):
    idx = build_h3_index(districts)
    for res in (5, 7):
        assert set(idx[idx.res == res].place_id) == set(districts.place_id)


def test_tiny_island_district_gets_a_cell(districts_with_island):
    idx = build_h3_index(districts_with_island, (5,))
    assert (idx.place_id == "district:island").sum() == 1


def test_cells_unique_per_res(districts):
    idx = build_h3_index(districts)
    assert not idx.duplicated(["cell", "res"]).any()


def test_output_deterministic_and_columns(districts_with_island):
    a = build_h3_index(districts_with_island)
    b = build_h3_index(districts_with_island)
    assert list(a.columns) == ["cell", "res", "place_id"]
    assert a.equals(b)
    assert not a.duplicated(["cell", "res"]).any()


def test_fallback_cell_taken_from_larger_district_only_if_it_keeps_another():
    res = 5
    big = box(78.0, 17.0, 80.0, 19.0)
    cell = h3.latlng_to_cell(18.0, 79.0, res)
    lat, lng = h3.cell_to_latlng(cell)
    eps = 0.001
    tiny = box(lng - eps, lat - eps, lng + eps, lat + eps)
    gdf = gpd.GeoDataFrame(
        {"place_id": ["district:big", "district:tiny"]},
        geometry=[MultiPolygon([big]), MultiPolygon([tiny])],
        crs=4326,
    )
    idx = build_h3_index(gdf, (res,))
    owner = idx.set_index("cell").place_id
    assert owner[cell] == "district:tiny"
    assert (idx.place_id == "district:big").sum() > 0
    assert (idx.place_id == "district:tiny").sum() == 1

    # Owner has only that one cell: tiny must take an adjacent unowned cell.
    solo = MultiPolygon([box(lng - 0.01, lat - 0.01, lng + 0.01, lat + 0.01)])
    gdf2 = gpd.GeoDataFrame(
        {"place_id": ["district:solo", "district:tiny"]},
        geometry=[solo, MultiPolygon([tiny])],
        crs=4326,
    )
    idx2 = build_h3_index(gdf2, (res,))
    owner2 = idx2.set_index("cell").place_id
    assert owner2[cell] == "district:solo"
    tiny_cells = idx2[idx2.place_id == "district:tiny"].cell.tolist()
    assert len(tiny_cells) == 1 and tiny_cells[0] in h3.grid_ring(cell, 1)
