"""Orchestrates the places backbone build into a versioned places directory."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import pandas as pd

from twin.paths import TwinPaths
from twin.pipeline.base import PipelineContext
from twin.places.boundaries import build_district_boundaries, dissolve_levels, write_boundaries
from twin.places.crosswalk import build_crosswalk
from twin.places.h3link import build_h3_index
from twin.places.lgd import load_lgd
from twin.places.resolver import PlaceResolver, load_aliases
from twin.store.atomic import publish_dir
from twin.store.parquet_store import read_current, set_current

# DataMeet-style attribute names in the 2011 census district file.
CENSUS2011_COLUMNS = {"state_code": "ST_CEN_CD", "district_code": "DT_CEN_CD", "name": "DISTRICT"}
_LEVELS = ("district", "state", "country")


@dataclass
class BackboneInputs:
    lgd_states: Path
    lgd_districts: Path
    soi_districts: Path
    soi_outline: Path
    census2011_districts: Path
    aliases: Path


@dataclass
class BackboneReport:
    districts: int
    states: int
    unmatched_boundaries: list[str] = field(default_factory=list)
    districts_without_census2011_link: int = 0
    # Current (LGD) districts that ended up with no boundary geometry.
    districts_without_boundary: int = 0


def _code(col: pd.Series, width: int) -> pd.Series:
    """Census code column -> zero-padded string; tolerates ints, floats (10.0) and strings."""
    def one(v) -> str:
        if isinstance(v, float):
            if v != v or v != int(v):
                raise ValueError(f"invalid census code: {v!r}")
            v = int(v)
        return str(v).strip().zfill(width)
    return col.map(one)


def _load_census2011(path: Path) -> gpd.GeoDataFrame:
    c = CENSUS2011_COLUMNS
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    st = _code(gdf[c["state_code"]], 2)
    dt = _code(gdf[c["district_code"]], 3)
    gdf["place_id"] = "census2011_district:" + st + dt
    return gdf[["place_id", "geometry"]]


def build_backbone(inputs: BackboneInputs, paths: TwinPaths, boundary_version: str) -> BackboneReport:
    places = load_lgd(inputs.lgd_states, inputs.lgd_districts, boundary_version)
    aliases = load_aliases(inputs.aliases)
    resolver = PlaceResolver(places, aliases)

    districts, unmatched = build_district_boundaries(
        inputs.soi_districts, inputs.soi_outline, places, resolver
    )
    levels = dissolve_levels(districts, places)
    old = _load_census2011(inputs.census2011_districts)
    crosswalk = build_crosswalk(old, districts)
    h3_index = build_h3_index(districts)

    def _write(tmp: Path) -> None:
        places.to_parquet(tmp / "places.parquet", index=False)
        aliases.to_parquet(tmp / "aliases.parquet", index=False)
        write_boundaries(levels, tmp)
        crosswalk.to_parquet(tmp / "crosswalk_census2011.parquet", index=False)
        h3_index.to_parquet(tmp / "h3_index.parquet", index=False)

    publish_dir(paths.places_dir(boundary_version), _write)
    set_current(paths, "places", boundary_version)

    district_ids = set(places.loc[places["level"] == "district", "place_id"])
    with_boundary = set(districts["place_id"])
    return BackboneReport(
        districts=len(district_ids),
        states=int((places["level"] == "state").sum()),
        unmatched_boundaries=list(unmatched),
        districts_without_census2011_link=len(district_ids - set(crosswalk["new_id"])),
        districts_without_boundary=len(district_ids - with_boundary),
    )


def load_backbone(paths: TwinPaths, known_sources: set[str] | None = None) -> PipelineContext:
    version = read_current(paths).get("places")
    d = paths.places_dir(version) if version else None
    if not version or not (d / "places.parquet").exists():
        raise FileNotFoundError(
            "places backbone not built (no CURRENT 'places' version); run build_backbone first"
        )
    boundaries = {lv: gpd.read_parquet(d / f"boundaries_{lv}.parquet") for lv in _LEVELS}
    return PipelineContext(
        paths=paths,
        places=pd.read_parquet(d / "places.parquet"),
        boundaries=boundaries,
        crosswalk=pd.read_parquet(d / "crosswalk_census2011.parquet"),
        known_sources=set(known_sources) if known_sources else set(),
    )
