"""Orchestrates the places backbone build into a versioned places directory."""
from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import pandas as pd

from twin.paths import TwinPaths
from twin.pipeline.base import PLACES_DIGEST_FILE, PipelineContext
from twin.places.boundaries import build_district_boundaries, dissolve_levels, write_boundaries
from twin.places.crosswalk import build_crosswalk
from twin.places.h3link import build_h3_index
from twin.places.lgd import load_lgd
from twin.places.resolver import PlaceResolver, load_aliases
from twin.store.atomic import publish_dir
from twin.store.parquet_store import read_current

# DataMeet-style attribute names in the 2011 census district file.
CENSUS2011_COLUMNS = {"state_code": "ST_CEN_CD", "district_code": "DT_CEN_CD", "name": "DISTRICT"}
_LEVELS = ("district", "state", "country")
# Files whose bytes make up places_digest.txt, in this order. Dataset versions hash the
# digest, so rebuilding the same boundary version with changed places gives new versions.
DIGEST_FILES = ("crosswalk_census2011.parquet", "boundaries_district.parquet", "places.parquet")


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
    # Boundary features accepted by fuzzy name match, (source name, LGD name): review these.
    fuzzy_matches: list[tuple[str, str]] = field(default_factory=list)
    districts_without_census2011_link: int = 0
    # Current (LGD) districts that ended up with no boundary geometry.
    districts_without_boundary: int = 0
    # Current districts whose LGD census2011_code disagrees with the crosswalk: their
    # max-weight 2011 source is not census2011_district:<state><code>, or they have a
    # census code but no crosswalk row. Diagnostic only; apportioning is unchanged.
    census_code_disagreements: int = 0
    # Min over 2011 districts of the kept (pre-renormalisation) area-weight sum;
    # 1.0 means every 2011 district is fully covered by current districts.
    min_coverage_ratio: float = 0.0
    # 2011 polygons dropped because their state or district code was missing.
    census2011_polygons_without_code: int = 0
    places_version: str = ""
    places_digest: str = ""


def _missing(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or (isinstance(v, str) and not v.strip())


def _code(col: pd.Series, width: int) -> pd.Series:
    """Census code column -> zero-padded string; tolerates ints, floats (10.0) and strings."""
    def one(v) -> str:
        if isinstance(v, float):
            if v != int(v):
                raise ValueError(f"invalid census code: {v!r}")
            v = int(v)
        return str(v).strip().zfill(width)
    return col.map(one)


def _load_census2011(path: Path) -> tuple[gpd.GeoDataFrame, int]:
    """2011 polygons keyed census2011_district:<SS><DDD>, and how many were dropped for a missing code."""
    c = CENSUS2011_COLUMNS
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    missing = gdf[c["state_code"]].map(_missing) | gdf[c["district_code"]].map(_missing)
    dropped = int(missing.sum())
    if dropped:
        warnings.warn(
            f"{dropped} Census 2011 polygon(s) without a state/district code were dropped",
            stacklevel=2,
        )
        gdf = gdf[~missing]
    st = _code(gdf[c["state_code"]], 2)
    dt = _code(gdf[c["district_code"]], 3)
    gdf = gdf.assign(place_id="census2011_district:" + st + dt)
    return gdf[["place_id", "geometry"]], dropped


def places_digest(places_dir: Path) -> str:
    """sha256 over the bytes of DIGEST_FILES (in that order) inside a places directory."""
    h = hashlib.sha256()
    for name in DIGEST_FILES:
        h.update((Path(places_dir) / name).read_bytes())
    return h.hexdigest()


def _census_code_disagreements(places: pd.DataFrame, crosswalk: pd.DataFrame) -> int:
    d = places[(places["level"] == "district") & places["census2011_code"].notna()]
    expected = (
        "census2011_district:" + d["state_code"].astype(str).str.zfill(2)
        + d["census2011_code"].astype(str).str.zfill(3)
    )
    top = (
        crosswalk.sort_values(["new_id", "area_weight", "old_id"])
        .groupby("new_id")["old_id"].last()
    )
    actual = d["place_id"].map(top)
    return int((actual.isna() | (actual != expected)).sum())


def _min_coverage(old: gpd.GeoDataFrame, crosswalk: pd.DataFrame) -> float:
    if old.empty:
        return 0.0
    cov = crosswalk.groupby("old_id")["coverage"].first()
    return float(old["place_id"].map(cov).fillna(0.0).min())


def build_backbone(inputs: BackboneInputs, paths: TwinPaths, boundary_version: str) -> BackboneReport:
    """Build and publish places/<boundary_version>, including places_digest.txt.

    Does NOT touch CURRENT.json: the caller decides, after its own gates, whether the
    build goes live (set_current / set_current_many with key "places").
    """
    places = load_lgd(inputs.lgd_states, inputs.lgd_districts, boundary_version)
    aliases = load_aliases(inputs.aliases)
    resolver = PlaceResolver(places, aliases)

    districts, unmatched, fuzzy = build_district_boundaries(
        inputs.soi_districts, inputs.soi_outline, places, resolver
    )
    levels = dissolve_levels(districts, places)
    old, without_code = _load_census2011(inputs.census2011_districts)
    crosswalk = build_crosswalk(old, districts)
    h3_index = build_h3_index(districts)

    def _write(tmp: Path) -> None:
        places.to_parquet(tmp / "places.parquet", index=False)
        aliases.to_parquet(tmp / "aliases.parquet", index=False)
        write_boundaries(levels, tmp)
        crosswalk.to_parquet(tmp / "crosswalk_census2011.parquet", index=False)
        h3_index.to_parquet(tmp / "h3_index.parquet", index=False)
        (tmp / PLACES_DIGEST_FILE).write_text(places_digest(tmp), encoding="utf-8")

    final = publish_dir(paths.places_dir(boundary_version), _write)
    digest = (final / PLACES_DIGEST_FILE).read_text(encoding="utf-8")

    district_ids = set(places.loc[places["level"] == "district", "place_id"])
    with_boundary = set(districts["place_id"])
    return BackboneReport(
        districts=len(district_ids),
        states=int((places["level"] == "state").sum()),
        unmatched_boundaries=list(unmatched),
        fuzzy_matches=list(fuzzy),
        districts_without_census2011_link=len(district_ids - set(crosswalk["new_id"])),
        districts_without_boundary=len(district_ids - with_boundary),
        census_code_disagreements=_census_code_disagreements(places, crosswalk),
        min_coverage_ratio=_min_coverage(old, crosswalk),
        census2011_polygons_without_code=without_code,
        places_version=boundary_version,
        places_digest=digest,
    )


def load_backbone(
    paths: TwinPaths,
    known_sources: set[str] | None = None,
    boundary_version: str | None = None,
) -> PipelineContext:
    """Load a places version: `boundary_version` when given, else CURRENT's 'places'."""
    version = boundary_version or read_current(paths).get("places")
    d = paths.places_dir(version) if version else None
    if not version or not (d / "places.parquet").exists():
        raise FileNotFoundError(
            f"places backbone not built (places version {version!r} not found); "
            "run build_backbone first"
        )
    boundaries = {lv: gpd.read_parquet(d / f"boundaries_{lv}.parquet") for lv in _LEVELS}
    return PipelineContext(
        paths=paths,
        places=pd.read_parquet(d / "places.parquet"),
        boundaries=boundaries,
        crosswalk=pd.read_parquet(d / "crosswalk_census2011.parquet"),
        known_sources=set(known_sources) if known_sources else set(),
        places_version=version,
    )
