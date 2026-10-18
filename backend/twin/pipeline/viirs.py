"""VIIRS annual nightlights adapter: per-district zonal sum of radiance."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.mask

from twin.pipeline.base import Indicator, PipelineContext, ValidationReport
from twin.store.schema import OBSERVATION_COLUMNS

SOURCE_ID = "viirs"
INDICATOR_ID = "nightlights_radiance_sum"
UNIT = "nW/cm²/sr·px"
_YEAR_RE = re.compile(r"_(\d{4})_")


def _year(path: Path) -> str:
    m = _YEAR_RE.search(path.name)
    if not m:
        raise ValueError(f"cannot parse year from VIIRS filename: {path.name}")
    return m.group(1)


def _zonal_sum(src: rasterio.DatasetReader, geom) -> float:
    """Sum of non-NaN, non-negative pixels under geom; all_touched fallback if no pixel centre falls inside."""
    for all_touched in (False, True):
        try:
            arr, _ = rasterio.mask.mask(
                src, [geom], crop=True, all_touched=all_touched, filled=False
            )
        except ValueError:  # shape does not overlap the raster
            return 0.0
        covered = ~np.ma.getmaskarray(arr)
        if covered.any():
            data = np.where(covered, np.ma.getdata(arr).astype("float64"), 0.0)
            nodata = src.nodata
            if nodata is not None and not np.isnan(nodata):
                data = np.where(data == nodata, 0.0, data)
            data = np.nan_to_num(data, nan=0.0)
            return float(np.clip(data, 0.0, None).sum())
    return 0.0


class ViirsAdapter:
    source_id = SOURCE_ID
    transform_version = "viirs-zonal-v1"
    indicators = [
        Indicator(
            INDICATOR_ID,
            "Nightlights radiance (sum)",
            "Sum of VIIRS annual average-masked nighttime radiance over each district, "
            "a proxy for economic activity, not GDP.",
            UNIT,
            ("economy",),
            SOURCE_ID,
        )
    ]

    def input_files(self, manual_dir: Path) -> list[Path]:
        return sorted((Path(manual_dir) / "viirs").glob("VNL_*_*average_masked*.tif"))

    def observed_period(self, files: list[Path]) -> str:
        years = {_year(f) for f in files}
        if len(years) != 1 or len(files) != 1:
            raise ValueError(f"expected exactly one VIIRS file/year per run, got {[f.name for f in files]}")
        return years.pop()

    def parse(self, files: list[Path], ctx: PipelineContext) -> pd.DataFrame:
        year = self.observed_period(files)
        districts = ctx.boundaries["district"]
        with rasterio.open(files[0]) as src:
            geoms = districts.geometry
            if src.crs is not None and districts.crs is not None and districts.crs != src.crs:
                geoms = geoms.to_crs(src.crs)
            values = [_zonal_sum(src, g) for g in geoms]
        out = pd.DataFrame({
            "indicator": INDICATOR_ID,
            "place_id": districts["place_id"].to_numpy(),
            "period": year,
            "value": np.asarray(values, dtype=float),
            "unit": UNIT,
            "source_id": SOURCE_ID,
            "dataset_version": "",
            "trust_label": "fact",
        })
        return out[list(OBSERVATION_COLUMNS)].reset_index(drop=True)

    def validate(self, obs: pd.DataFrame, ctx: PipelineContext) -> ValidationReport:
        problems: list[str] = []
        districts = set(ctx.boundaries["district"]["place_id"])
        ok_rows = obs[obs["value"].notna() & (obs["value"] >= 0)]
        bad = sorted(districts - set(ok_rows["place_id"]))
        if bad:
            problems.append(f"districts without a non-null value >= 0: {bad}")
        total = float(obs["value"].sum())
        if not total > 0:
            problems.append("total nightlights radiance is not positive")
        return ValidationReport(ok=not problems, problems=problems, stats={"total": total})
