"""Survey of India boundaries: match to LGD places, clip to the outline, dissolve, write."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
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


def build_district_boundaries(
    districts_path: Path,
    outline_path: Path,
    places: pd.DataFrame,
    resolver: PlaceResolver,
) -> tuple[gpd.GeoDataFrame, list[str]]:
    src = gpd.read_file(districts_path).rename(columns=SOI_DISTRICT_COLUMNS)
    if src.crs is None:
        src = src.set_crs(4326)
    src = src.to_crs(4326)
    outline = gpd.read_file(outline_path).to_crs(4326)

    place_ids: list[str | None] = []
    unmatched: list[str] = []
    state_cache: dict[str, str | None] = {}
    for state_name, district_name in zip(src["state_name"], src["district_name"]):
        if state_name not in state_cache:
            sr = resolver.resolve(str(state_name), level="state")
            state_cache[state_name] = (
                sr.matches[0].state_code if sr.matches and not sr.ambiguous else None
            )
        state_code = state_cache[state_name]
        pid = None
        if state_code is not None:
            dr = resolver.resolve(str(district_name), level="district", state_code=state_code)
            if dr.matches and not dr.ambiguous:
                pid = dr.matches[0].place_id
        place_ids.append(pid)
        if pid is None:
            unmatched.append(str(district_name))

    src["place_id"] = place_ids
    src = src[src["place_id"].notna()]
    clipped = src.geometry.intersection(outline.union_all())
    out = gpd.GeoDataFrame(
        {"place_id": src["place_id"].to_numpy()},
        geometry=_multi(clipped).to_numpy(),
        crs=4326,
    )
    out = out[~out.geometry.is_empty].reset_index(drop=True)
    return out, unmatched


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
    district = district[["place_id", "name", "geometry"]].reset_index(drop=True)
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
        metric = gdf.to_crs(METRIC_CRS)
        simple = metric.geometry.simplify(tol[level], preserve_topology=True).to_crs(4326)
        slim = gpd.GeoDataFrame(
            {"place_id": gdf["place_id"].to_numpy(), "name": gdf["name"].to_numpy()},
            geometry=simple.to_numpy(),
            crs=4326,
        )
        (out_dir / f"boundaries_{level}.geojson").write_text(slim.to_json(), encoding="utf-8")
