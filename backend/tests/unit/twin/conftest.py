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

    gdf, _, _ = build_district_boundaries(
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
OLD_E_ID = "census2011_district:27522"


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


def fixture_inputs(fx):
    from twin.places.build import BackboneInputs

    return BackboneInputs(
        lgd_states=fx / "lgd_states.csv",
        lgd_districts=fx / "lgd_districts.csv",
        soi_districts=fx / "soi_districts.geojson",
        soi_outline=fx / "soi_outline.geojson",
        census2011_districts=fx / "census2011_districts.geojson",
        aliases=fx / "aliases.csv",
    )


@pytest.fixture
def backbone_inputs(fx):
    return fixture_inputs(fx)


@pytest.fixture
def ctx_backbone(fx, tmp_paths):
    from app.data_registry import SOURCE_REGISTRY
    from twin.places.build import build_backbone, load_backbone

    build_backbone(fixture_inputs(fx), tmp_paths, "lgd-test")
    return load_backbone(
        tmp_paths, known_sources={s.id for s in SOURCE_REGISTRY} | {"dummy"},
        boundary_version="lgd-test",
    )


@pytest.fixture
def ctx_census(ctx_backbone, fx):
    import shutil

    d = ctx_backbone.paths.manual / "census2011"
    d.mkdir(parents=True)
    shutil.copy2(fx / "pca_district.csv", d / "pca_district.csv")
    return ctx_backbone


VIIRS_NAME = "VNL_v2_npp_2023_global_vcmslcfg_c202402081600.average_masked.dat.tif"


def write_viirs_tiff(path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, "w", driver="GTiff", height=20, width=20, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(70, 20, 0.5, 0.5),
    ) as dst:
        dst.write(np.ones((20, 20), dtype="float32"), 1)
    return path


def make_fixture_manual_paths(tmp_path, fx):
    """TwinPaths whose manual/ dir holds every fixture in the documented layout."""
    import shutil

    from twin.paths import TwinPaths

    paths = TwinPaths(tmp_path / "twin")
    m = paths.manual
    for rel, src in {
        "lgd/states.csv": "lgd_states.csv",
        "lgd/districts.csv": "lgd_districts.csv",
        "soi/district_boundaries.geojson": "soi_districts.geojson",
        "soi/india_outline.geojson": "soi_outline.geojson",
        "census2011/district_boundaries.geojson": "census2011_districts.geojson",
        "census2011/pca_district.csv": "pca_district.csv",
    }.items():
        (m / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fx / src, m / rel)
    write_viirs_tiff(m / "viirs" / VIIRS_NAME)
    paths.seed.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fx / "aliases.csv", paths.seed / "aliases.csv")
    return paths


@pytest.fixture
def fixture_manual_paths(tmp_path, fx):
    return make_fixture_manual_paths(tmp_path, fx)
