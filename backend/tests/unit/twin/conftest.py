from pathlib import Path

import pytest


@pytest.fixture
def fx() -> Path:
    return Path(__file__).parents[2] / "fixtures" / "twin"


@pytest.fixture
def places(fx):
    from twin.places.lgd import load_lgd

    return load_lgd(fx / "lgd_states.csv", fx / "lgd_districts.csv", "lgd-test")


@pytest.fixture
def resolver(places, fx):
    from twin.places.resolver import PlaceResolver, load_aliases

    return PlaceResolver(places, load_aliases(fx / "aliases.csv"))


@pytest.fixture
def districts(fx, places, resolver):
    from twin.places.boundaries import build_district_boundaries

    gdf, _ = build_district_boundaries(
        fx / "soi_districts.geojson", fx / "soi_outline.geojson", places, resolver
    )
    return gdf


X_ID = "district:217"
Y_ID = "district:222"
Z_ID = "district:201"
NEW_DISTRICT_ID = "district:999"
OLD_A_ID = "census2011_district:10226"
OLD_B_ID = "census2011_district:10229"
OLD_C_ID = "census2011_district:27519"


@pytest.fixture
def old(fx):
    import geopandas as gpd

    gdf = gpd.read_file(fx / "census2011_districts.geojson")
    gdf["place_id"] = "census2011_district:" + gdf["ST_CEN_CD"] + gdf["DT_CEN_CD"]
    return gdf[["place_id", "geometry"]].set_crs(4326, allow_override=True)


@pytest.fixture
def new(districts):
    return districts


@pytest.fixture
def districts_with_island(districts):
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import MultiPolygon, box

    island = MultiPolygon([box(79.0, 18.0, 79.018, 18.018)])
    row = gpd.GeoDataFrame(
        {"place_id": ["district:island"]}, geometry=[island], crs=districts.crs
    )
    return gpd.GeoDataFrame(
        pd.concat([districts[["place_id", "geometry"]], row], ignore_index=True),
        crs=districts.crs,
    )


@pytest.fixture
def tmp_paths(tmp_path):
    from twin.paths import TwinPaths

    return TwinPaths(tmp_path / "twin")


@pytest.fixture
def ctx(tmp_paths, places, districts):
    from twin.pipeline.base import PipelineContext

    return PipelineContext(
        paths=tmp_paths, places=places, boundaries={"district": districts},
        crosswalk=None, known_sources={"dummy"},
    )
