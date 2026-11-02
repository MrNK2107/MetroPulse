"""Area-weighted crosswalk from Census 2011 districts to current districts."""
from __future__ import annotations

import warnings
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
    each old_id sums to 1. coverage is the pre-renormalisation sum of the kept
    area_weights for that old_id (1.0 = the old district is fully covered by new
    districts; lower means area fell outside them or into dropped slivers). Also returns piece_area (m2, EPSG:6933 area of the
    old/new piece, after the sliver drop; used to weight "mean") and piece_pop
    (population of the piece from pop_weights, NaN when not provided). Input
    geometries are repaired with make_valid first. `pop_weights` (optional; columns old_id, new_id,
    population = population inside each old/new piece) gives pop_weight =
    piece population / old total, over the retained pieces; otherwise NaN.
    """
    o = old[["place_id", "geometry"]].rename(columns={"place_id": "old_id"}).to_crs(AREA_CRS)
    o["geometry"] = o.geometry.make_valid()
    n = new[["place_id", "geometry"]].rename(columns={"place_id": "new_id"}).to_crs(AREA_CRS)
    n["geometry"] = n.geometry.make_valid()
    pieces = gpd.overlay(o, n, how="intersection", keep_geom_type=True)
    pieces["area"] = pieces.geometry.area
    pieces = pieces[pieces["area"] > 0]
    old_area = o.set_index("old_id").geometry.area
    pieces["area_weight"] = pieces["area"] / pieces["old_id"].map(old_area)
    pieces = pieces[pieces["area_weight"] >= sliver]
    pieces["coverage"] = pieces.groupby("old_id")["area_weight"].transform("sum")
    pieces["area_weight"] = pieces["area_weight"] / pieces.groupby("old_id")["area_weight"].transform("sum")
    out = pieces[["old_id", "new_id", "area_weight", "coverage", "area"]].rename(
        columns={"area": "piece_area"}
    ).reset_index(drop=True)

    out["pop_weight"] = np.nan
    out["piece_pop"] = np.nan
    if pop_weights is not None:
        pop = pop_weights[["old_id", "new_id", "population"]]
        out = out.merge(pop, on=["old_id", "new_id"], how="left")
        pop_v = out["population"].fillna(0.0)
        total = pop_v.groupby(out["old_id"]).transform("sum")
        out["pop_weight"] = (pop_v / total.where(total > 0)).astype(float)
        out["piece_pop"] = pop_v.astype(float)
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
      pieces only) with each piece weighted by its piece_area (area mode) or
      piece_pop (pop mode); all-null gives null.
    Non-null observations whose old id has no crosswalk rows cannot be mapped:
    they are dropped, a warning is emitted, and out.attrs["unmapped_old_ids"]
    (sorted list) and out.attrs["unmapped_totals"] ({indicator: summed value})
    record them (both empty when everything mapped).
    """
    if method not in ("sum", "mean"):
        raise ValueError(f"unknown method: {method!r}")
    wcol = {"area": "area_weight", "pop": "pop_weight"}[weight]
    mcol = {"area": "piece_area", "pop": "piece_pop"}[weight]
    keys = [c for c in obs.columns if c not in ("place_id", "value")]
    x = xwalk.assign(**({} if mcol in xwalk else {mcol: np.nan}))[
        ["old_id", "new_id", wcol, mcol]
    ].rename(columns={wcol: "w", mcol: "mw"})
    m = obs.merge(x, left_on="place_id", right_on="old_id", how="left")

    unmapped = m[m["new_id"].isna() & m["value"].notna()]
    ids = sorted(unmapped["place_id"].unique().tolist())
    totals = unmapped.groupby("indicator")["value"].sum().to_dict()
    if ids:
        warnings.warn(
            f"{len(ids)} old id(s) with non-null values have no crosswalk rows "
            f"and were dropped: {ids}",
            stacklevel=2,
        )
    m = m[m["new_id"].notna()].copy()

    if method == "sum":
        ok = m["value"].notna() & m["w"].notna()
        m["num"] = (m["value"] * m["w"]).where(ok)
        m["den"] = m["w"].where(ok)
    else:
        ok = m["value"].notna() & m["mw"].notna()
        m["num"] = (m["value"] * m["mw"]).where(ok)
        m["den"] = m["mw"].where(ok)
    m["cnt"] = ok.astype(int)

    agg = m.groupby(keys + ["new_id"], dropna=False, sort=True).agg(
        num=("num", "sum"),
        den=("den", "sum"),
        cnt=("cnt", "sum"),
        n_sources=("old_id", "nunique"),
        max_weight=("w", "max"),
    ).reset_index()
    if method == "sum":
        agg["value"] = agg["num"].where(agg["cnt"] > 0)
    else:
        agg["value"] = (agg["num"] / agg["den"].where(agg["den"] > 0)).where(agg["cnt"] > 0)
    agg = agg.rename(columns={"new_id": "place_id"})
    out = agg[list(obs.columns) + ["n_sources", "max_weight"]].reset_index(drop=True)
    out.attrs["unmapped_old_ids"] = ids
    out.attrs["unmapped_totals"] = {k: float(v) for k, v in totals.items()}
    return out
