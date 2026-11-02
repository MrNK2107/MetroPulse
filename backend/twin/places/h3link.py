"""Link district polygons to H3 cells (centre-in-polygon, with a tiny-district fallback)."""

from __future__ import annotations

import geopandas as gpd
import h3
import pandas as pd


def _polygon_cells(geometry, res: int) -> list[str]:
    shape = h3.geo_to_h3shape(geometry.__geo_interface__)
    return sorted(h3.h3shape_to_cells(shape, res))


def _fallback_cell(geometry, res: int, owners: pd.Series) -> tuple[str, bool]:
    """Return (cell, steals). `steals` is True when the cell is owned but may be taken over."""
    point = geometry.representative_point()
    cell = h3.latlng_to_cell(point.y, point.x, res)  # shapely: x=lng, y=lat
    if cell not in owners.index:
        return cell, False
    owner = owners[cell]
    if (owners == owner).sum() >= 2:
        return cell, True
    for k in range(1, 4):
        free = [c for c in sorted(h3.grid_ring(cell, k)) if c not in owners.index]
        if free:
            return free[0], False
    raise ValueError(f"no free H3 cell near {cell} at res {res}")


def _link_one_res(districts: gpd.GeoDataFrame, res: int) -> pd.DataFrame:
    ordered = districts.sort_values("place_id", kind="stable")
    frames = [
        pd.DataFrame({"cell": _polygon_cells(geom, res), "place_id": pid})
        for pid, geom in zip(ordered["place_id"], ordered.geometry)
        if geom is not None and not geom.is_empty
    ]
    base = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        {"cell": pd.Series(dtype=str), "place_id": pd.Series(dtype=str)}
    )
    base = base.drop_duplicates("cell", keep="first")
    owners = base.set_index("cell")["place_id"]

    have = set(owners.values)
    for pid, geom in zip(ordered["place_id"], ordered.geometry):
        if pid in have or geom is None or geom.is_empty:
            continue
        cell, _ = _fallback_cell(geom, res, owners)
        owners = owners.copy()
        owners[cell] = pid
        have.add(pid)

    out = owners.rename_axis("cell").reset_index()
    out["res"] = res
    return out[["cell", "res", "place_id"]]


def build_h3_index(
    districts: gpd.GeoDataFrame, resolutions: tuple[int, ...] = (5, 7)
) -> pd.DataFrame:
    """Map each district to H3 cells; every (cell, res) is owned by at most one district."""
    parts = [_link_one_res(districts, res) for res in resolutions]
    out = pd.concat(parts, ignore_index=True)
    out = out.sort_values(["res", "place_id", "cell"], kind="stable").reset_index(drop=True)
    out["res"] = out["res"].astype(int)
    return out
