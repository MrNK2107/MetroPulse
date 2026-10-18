import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from twin.pipeline.base import run_pipeline
from twin.pipeline.viirs import ViirsAdapter

NAME = "VNL_v2_npp_2023_global_vcmslcfg_c202402081600.average_masked.dat.tif"
# 0.5 deg pixels: Aurangabad 4, Patna 4 minus NaN and negative pixels = 2, Gaya 6,
# Sambhajinagar 4, Mumbai 4, Newpur 4, Lakshadweep 1 (all_touched fallback).
EXPECTED_SUM = 4 + 2 + 6 + 4 + 4 + 4 + 1


def _write(path, arr):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, "w", driver="GTiff", height=20, width=20, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(70, 20, 0.5, 0.5),
    ) as dst:
        dst.write(arr, 1)
    return path


@pytest.fixture
def tiff(ctx_backbone):
    arr = np.ones((20, 20), dtype="float32")
    arr[8, 4] = np.nan  # inside Patna (lon 72-73, lat 15-16)
    arr[9, 5] = -5.0
    return _write(ctx_backbone.paths.manual / "viirs" / NAME, arr)


def _by_name(ctx, obs):
    names = ctx.boundaries["district"].set_index("place_id")["name"]
    return obs.assign(name=obs.place_id.map(names)).set_index("name").value


def test_zonal_sum_per_district(ctx_backbone, tiff):
    obs = ViirsAdapter().parse([tiff], ctx_backbone)
    assert set(obs.place_id) == set(ctx_backbone.boundaries["district"].place_id)
    assert (obs.value >= 0).all() and obs.period.eq("2023").all()


def test_negative_and_nan_pixels_ignored(ctx_backbone, tiff):
    obs = ViirsAdapter().parse([tiff], ctx_backbone)
    assert obs.value.sum() == pytest.approx(EXPECTED_SUM)
    assert _by_name(ctx_backbone, obs)["Patna"] == pytest.approx(2.0)


def test_sub_pixel_district_gets_value(ctx_backbone, tiff):
    obs = ViirsAdapter().parse([tiff], ctx_backbone)
    assert _by_name(ctx_backbone, obs)["Lakshadweep"] > 0


def test_multiple_years_rejected(ctx_backbone, tiff):
    _write(tiff.with_name(NAME.replace("_2023_", "_2022_")), np.ones((20, 20), "float32"))
    adapter = ViirsAdapter()
    files = adapter.input_files(ctx_backbone.paths.manual)
    assert len(files) == 2
    with pytest.raises(ValueError):
        adapter.parse(files, ctx_backbone)


def test_validate_and_publish_through_pipeline(ctx_backbone, tiff):
    res = run_pipeline(ViirsAdapter(), ctx_backbone)
    assert res.published and res.report.ok
    assert res.report.stats["total"] == pytest.approx(EXPECTED_SUM)
    assert res.dataset_version.startswith("viirs@2023#")
