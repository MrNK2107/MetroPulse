"""Area-weighted crosswalk from Census 2011 districts to current districts."""
from __future__ import annotations

from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd

AREA_CRS = "EPSG:6933"  # equal-area


def build_crosswalk(
    old: gpd.GeoDataFrame,
    new: gpd.GeoDataFrame,
    pop_weights: pd.DataFrame | None = None,
    sliver: float = 0.005,
) -> pd.DataFrame:
    """Overlap old (2011) and new districts.

    Returns columns old_id, new_id, area_weight, pop_weight. area_weight is the
    share of the old district's area falling in the new one (computed in
    EPSG:6933); pieces below `sliver` are dropped and weights renormalised so
    each old_id sums to 1. `pop_weights` (optional; columns old_id, new_id,
    population = population inside each old/new piece) gives pop_weight =
    piece population / old total, over the retained pieces; otherwise NaN.
    """
    o = old[["place_id", "geometry"]].rename(columns={"place_id": "old_id"}).to_crs(AREA_CRS)
    n = new[["place_id", "geometry"]].rename(columns={"place_id": "new_id"}).to_crs(AREA_CRS)
    pieces = gpd.overlay(o, n, how="intersection", keep_geom_type=True)
    pieces["area"] = pieces.geometry.area
    pieces = pieces[pieces["area"] > 0]
    old_area = o.set_index("old_id").geometry.area
    pieces["area_weight"] = pieces["area"] / pieces["old_id"].map(old_area)
    pieces = pieces[pieces["area_weight"] >= sliver]
    pieces["area_weight"] = pieces["area_weight"] / pieces.groupby("old_id")["area_weight"].transform("sum")
    out = pieces[["old_id", "new_id", "area_weight"]].reset_index(drop=True)

    out["pop_weight"] = np.nan
    if pop_weights is not None:
        pop = pop_weights[["old_id", "new_id", "population"]]
        out = out.merge(pop, on=["old_id", "new_id"], how="left")
        pop_v = out["population"].fillna(0.0)
        total = pop_v.groupby(out["old_id"]).transform("sum")
        out["pop_weight"] = (pop_v / total.where(total > 0)).astype(float)
        out = out.drop(columns="population")
    return out.sort_values(["old_id", "new_id"]).reset_index(drop=True)


def apply_crosswalk(
    obs: pd.DataFrame,
    xwalk: pd.DataFrame,
    method: Literal["sum", "mean"],
    weight: Literal["area", "pop"] = "area",
) -> pd.DataFrame:
    """Re-key old-geography observations onto new districts.

    Keeps indicator, period, unit, source_id, dataset_version and trust_label
    from the input (trust_label is NOT changed here) with place_id = new_id,
    plus two extra columns for the caller to judge reliability:
      n_sources  - number of contributing old ids for that new district
      max_weight - largest single weight flowing into that new district
    "sum": sum of value * weight. Null pieces are skipped; a new district whose
      contributing pieces are ALL null is null (never 0).
    "mean": weighted mean over the non-null pieces (weights taken from those
      pieces only); all-null gives null.
    Old ids absent from the crosswalk are dropped.
    """
    if method not in ("sum", "mean"):
        raise ValueError(f"unknown method: {method!r}")
    wcol = {"area": "area_weight", "pop": "pop_weight"}[weight]
    keys = [c for c in obs.columns if c not in ("place_id", "value")]
    x = xwalk[["old_id", "new_id", wcol]].rename(columns={wcol: "w"})
    m = obs.merge(x, left_on="place_id", right_on="old_id", how="inner")
    m["wv"] = m["value"] * m["w"]
    has = m["value"].notna() & m["w"].notna()
    m["w_ok"] = m["w"].where(has)
    m["wv"] = m["wv"].where(has)

    g = m.groupby(keys + ["new_id"], dropna=False, sort=True)
    agg = g.agg(
        wv=("wv", lambda s: s.sum(min_count=1)),
        w_ok=("w_ok", "sum"),
        n_sources=("old_id", "nunique"),
        max_weight=("w", "max"),
    ).reset_index()
    if method == "sum":
        agg["value"] = agg["wv"]
    else:
        agg["value"] = agg["wv"] / agg["w_ok"].where(agg["w_ok"] > 0)
    agg = agg.rename(columns={"new_id": "place_id"})
    cols = [c for c in obs.columns] + ["n_sources", "max_weight"]
    return agg[cols].reset_index(drop=True)
