"""Survey of India boundaries: match to LGD places, clip to the outline, dissolve, write."""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import MultiPolygon, Polygon

from twin.places.resolver import PlaceResolver

# Shapefile attribute name -> canonical name. Change only this if the real file differs.
SOI_DISTRICT_COLUMNS: dict[str, str] = {"DISTRICT": "district_name", "STATE": "state_name"}

DEFAULT_SIMPLIFY_M: dict[str, float] = {"district": 300, "state": 800, "country": 1500}
METRIC_CRS = "EPSG:7755"


def _to_multipolygon(geom):
    if geom is None or geom.is_empty:
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, MultiPolygon):
        return geom
    polys = [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]
    for g in getattr(geom, "geoms", []):
        if isinstance(g, MultiPolygon):
            polys.extend(g.geoms)
    return MultiPolygon(polys)


def _multi(series: gpd.GeoSeries) -> gpd.GeoSeries:
    return gpd.GeoSeries([_to_multipolygon(g) for g in series], index=series.index, crs=series.crs)


class BoundaryResult(NamedTuple):
    districts: gpd.GeoDataFrame
    # Source district names that could not be matched to exactly one LGD district.
    unmatched: list[str]
    # Accepted fuzzy matches as (source name, LGD place name), for owner review.
    fuzzy_matches: list[tuple[str, str]]


def build_district_boundaries(
    districts_path: Path,
    outline_path: Path,
    places: pd.DataFrame,
    resolver: PlaceResolver,
) -> BoundaryResult:
    """Match SoI district features to LGD districts, repair, clip to the outline, dissolve.

    Several features may share a place_id (multipart districts) only when none of them
    was a fuzzy match: a fuzzy match whose place_id is also claimed by another feature
    is refused, and every feature claiming that place_id goes to `unmatched`.
    """
    src = gpd.read_file(districts_path).rename(columns=SOI_DISTRICT_COLUMNS)
    if src.crs is None:
        src = src.set_crs(4326)
    src = src.to_crs(4326)
    outline = gpd.read_file(outline_path).to_crs(4326)

    place_ids: list[str | None] = []
    methods: list[str | None] = []
    state_cache: dict[str, str | None] = {}
    for state_name, district_name in zip(src["state_name"], src["district_name"]):
        if state_name not in state_cache:
            sr = resolver.resolve(str(state_name), level="state")
            state_cache[state_name] = (
                sr.matches[0].state_code if sr.matches and not sr.ambiguous else None
            )
        state_code = state_cache[state_name]
        pid, method = None, None
        if state_code is not None:
            dr = resolver.resolve(str(district_name), level="district", state_code=state_code)
            if dr.matches and not dr.ambiguous:
                pid, method = dr.matches[0].place_id, dr.matches[0].method
        place_ids.append(pid)
        methods.append(method)

    m = pd.DataFrame({"name": src["district_name"].astype(str).to_numpy(),
                      "place_id": place_ids, "method": methods})
    claimed = m.groupby("place_id")["name"].transform("size")
    fuzzy_pids = set(m.loc[m["method"] == "fuzzy", "place_id"])
    clash = m["place_id"].isin(fuzzy_pids) & (claimed > 1)
    m.loc[clash, "place_id"] = None
    unmatched = m.loc[m["place_id"].isna(), "name"].tolist()
    names = places.set_index("place_id")["name"]
    fz = m[(m["method"] == "fuzzy") & m["place_id"].notna()]
    fuzzy_matches = list(zip(fz["name"], fz["place_id"].map(names)))

    src["place_id"] = m["place_id"].to_numpy()
    src = src[src["place_id"].notna()]
    repaired = src.geometry.make_valid()
    clipped = repaired.intersection(outline.union_all())
    out = gpd.GeoDataFrame(
        {"place_id": src["place_id"].to_numpy()},
        geometry=clipped.to_numpy(),
        crs=4326,
    )
    out = out[~out.geometry.is_empty]
    # Multipart districts arrive as several features: one row per place_id.
    out = out.dissolve(by="place_id").reset_index()
    out["geometry"] = _multi(out.geometry)
    out = out[["place_id", "geometry"]].reset_index(drop=True)
    return BoundaryResult(out, unmatched, fuzzy_matches)


def dissolve_levels(districts: gpd.GeoDataFrame, places: pd.DataFrame) -> dict[str, gpd.GeoDataFrame]:
    names = places.set_index("place_id")["name"]
    parents = places.set_index("place_id")["parent_id"]
    district = districts[["place_id", "geometry"]].copy()
    district["name"] = district["place_id"].map(names)
    district["_state"] = district["place_id"].map(parents)

    state = district[["_state", "geometry"]].dissolve(by="_state").reset_index().rename(columns={"_state": "place_id"})
    state["name"] = state["place_id"].map(names)
    state = state[["place_id", "name", "geometry"]]
    state["geometry"] = _multi(state.geometry)

    country_row = places[places.level == "country"].iloc[0]
    country = gpd.GeoDataFrame(
        {"place_id": [country_row.place_id], "name": [country_row["name"]]},
        geometry=[_to_multipolygon(district.union_all())],
        crs=4326,
    )
    district = district.rename(columns={"_state": "parent_id"})
    district = district[["place_id", "name", "parent_id", "geometry"]].reset_index(drop=True)
    return {"district": district, "state": state.reset_index(drop=True), "country": country}


def write_boundaries(
    levels: dict[str, gpd.GeoDataFrame],
    out_dir: Path,
    simplify_m: dict[str, float] | None = None,
) -> None:
    tol = simplify_m or DEFAULT_SIMPLIFY_M
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for level, gdf in levels.items():
        gdf.to_parquet(out_dir / f"boundaries_{level}.parquet")

    # Simplify districts as a coverage (shared borders stay shared), then derive the
    # state and country layers from the simplified districts so all levels agree.
    districts = levels["district"]
    metric = districts.geometry.to_crs(METRIC_CRS)
    simple = shapely.coverage_simplify(metric.to_numpy(), tol["district"])
    simple_d = gpd.GeoDataFrame(
        {
            "place_id": districts["place_id"].to_numpy(),
            "name": districts["name"].to_numpy(),
            "parent_id": districts["parent_id"].to_numpy(),
        },
        geometry=gpd.GeoSeries(simple, crs=METRIC_CRS).to_crs(4326).to_numpy(),
        crs=4326,
    )
    simple_d["geometry"] = _multi(simple_d.geometry)

    state_names = levels["state"].set_index("place_id")["name"]
    simple_s = simple_d[["parent_id", "geometry"]].dissolve(by="parent_id").reset_index()
    simple_s = simple_s.rename(columns={"parent_id": "place_id"})
    simple_s["name"] = simple_s["place_id"].map(state_names)
    simple_s["geometry"] = _multi(simple_s.geometry)

    country = levels["country"].iloc[0]
    simple_c = gpd.GeoDataFrame(
        {"place_id": [country["place_id"]], "name": [country["name"]]},
        geometry=[_to_multipolygon(simple_d.union_all())],
        crs=4326,
    )
    for level, gdf in (("district", simple_d), ("state", simple_s), ("country", simple_c)):
        slim = gdf[["place_id", "name", "geometry"]]
        (out_dir / f"boundaries_{level}.geojson").write_text(slim.to_json(), encoding="utf-8")
