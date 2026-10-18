"""India Twin read API: place resolution, observations with receipts, boundaries, indicators."""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.data_registry import SOURCE_REGISTRY
from twin.paths import TwinPaths
from twin.pipeline.base import Indicator
from twin.places.build import load_backbone
from twin.places.resolver import PlaceResolver, load_aliases
from twin.store.catalog import list_indicators
from twin.store.parquet_store import query_observations, read_current

router = APIRouter()

NOT_BUILT = "twin data not built — run scripts/twin_build.py build"
BOUNDARY_LEVELS = ("country", "state", "district")
_SOURCES = {s.id: s for s in SOURCE_REGISTRY}


class TwinNotBuilt(Exception):
    pass


@dataclass
class TwinContext:
    paths: TwinPaths
    places: pd.DataFrame
    resolver: PlaceResolver
    indicators: list[Indicator]
    current: dict[str, str]

    @property
    def places_version(self) -> str:
        return self.current["places"]


_cache: dict[str, Any] = {"key": None, "ctx": None}
_lock = threading.Lock()


def get_twin_paths() -> TwinPaths:
    return TwinPaths.default()


def get_twin_context(paths: TwinPaths = Depends(get_twin_paths)) -> TwinContext:
    """Cached per (path, CURRENT.json mtime); rebuilt when the twin is republished."""
    try:
        key = (str(paths.root), paths.current_file.stat().st_mtime_ns)
    except OSError:
        raise TwinNotBuilt from None
    with _lock:
        if _cache["key"] == key:
            return _cache["ctx"]
        try:
            bb = load_backbone(paths, known_sources=set(_SOURCES))
            current = read_current(paths)
            aliases = load_aliases_parquet(paths, current["places"])
        except (FileNotFoundError, KeyError):
            raise TwinNotBuilt from None
        ctx = TwinContext(
            paths=paths,
            places=bb.places,
            resolver=PlaceResolver(bb.places, aliases),
            indicators=sorted(list_indicators(paths), key=lambda i: i.id),
            current=current,
        )
        _cache.update(key=key, ctx=ctx)
        return ctx


def load_aliases_parquet(paths: TwinPaths, version: str) -> pd.DataFrame:
    return pd.read_parquet(paths.places_dir(version) / "aliases.parquet")


def _envelope(data: Any, meta: dict | None = None, error: str | None = None) -> dict:
    return {"success": error is None, "data": data, "error": error, "meta": meta or {}}


def _fail(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content=_envelope(None, error=message))


def install_error_handlers(app) -> None:
    @app.exception_handler(TwinNotBuilt)
    async def _not_built(_request, _exc):
        return _fail(503, NOT_BUILT)


def _none(v):
    return None if v is None or (isinstance(v, float) and v != v) or v is pd.NA else v


@router.get("/places/resolve")
async def resolve_place(
    q: str = Query(..., min_length=1, max_length=100),
    level: str | None = Query(None, max_length=30),
    state: str | None = Query(None, max_length=10),
    ctx: TwinContext = Depends(get_twin_context),
):
    res = ctx.resolver.resolve(q, level=level, state_code=state)
    return _envelope({"matches": [asdict(m) for m in res.matches], "ambiguous": res.ambiguous})


def _ref(places: pd.DataFrame, place_id) -> dict | None:
    pid = _none(place_id)
    if pid is None:
        return None
    row = places[places["place_id"] == pid]
    if row.empty:
        return None
    return {"place_id": pid, "name": row.iloc[0]["name"]}


@router.get("/places/{place_id}")
async def get_place(place_id: str, ctx: TwinContext = Depends(get_twin_context)):
    rows = ctx.places[ctx.places["place_id"] == place_id]
    if rows.empty:
        return _fail(404, f"unknown place: {place_id}")
    r = rows.iloc[0]
    state = r["place_id"] if r["level"] == "state" else None
    if r["level"] == "district":
        state = r["parent_id"]
    return _envelope({
        "place_id": r["place_id"],
        "name": r["name"],
        "level": r["level"],
        "parent": _ref(ctx.places, r["parent_id"]),
        "state": _ref(ctx.places, state),
    })


@router.get("/places/{place_id}/observations")
async def place_observations(place_id: str, ctx: TwinContext = Depends(get_twin_context)):
    if not (ctx.places["place_id"] == place_id).any():
        return _fail(404, f"unknown place: {place_id}")
    names = {s.id: s.name for s in SOURCE_REGISTRY}
    obs = query_observations(ctx.paths, place_ids=[place_id], source_names=names)
    latest: dict[str, Any] = {}
    if not obs.empty:
        obs = obs.assign(_p=obs["period"].astype(str)).sort_values("_p")
        latest = {r["indicator"]: r for _, r in obs.iterrows()}  # last (newest) wins

    data = []
    for ind in ctx.indicators:
        row = latest.get(ind.id)
        sid = row["source_id"] if row is not None else ind.source_id
        src = _SOURCES.get(sid)
        data.append({
            "indicator": ind.id,
            "name": ind.name,
            "unit": ind.unit,
            "period": None if row is None else _none(row["period"]),
            "value": None if row is None else _none(row["value"]),
            "trust_label": None if row is None else _none(row["trust_label"]),
            "receipt": {
                "source_id": sid,
                "source_name": src.name if src else sid,
                "dataset_version": (
                    row["dataset_version"] if row is not None else ctx.current.get(sid)
                ),
                "license": src.license if src else None,
                "url": src.url if src else None,
            },
        })
    return _envelope(data, {"places_version": ctx.places_version})


@router.get("/boundaries/{level}")
async def boundaries(level: str, ctx: TwinContext = Depends(get_twin_context)):
    """Simplified GeoJSON FeatureCollection for one level.

    Deliberate exception to the {success, data, error, meta} envelope: GeoJSON is a
    file-like asset that the map loads directly. `level` is checked against a fixed
    set and never used to build a path otherwise.
    """
    if level not in BOUNDARY_LEVELS:
        return _fail(404, f"unknown boundary level: {level}")
    f = ctx.paths.places_dir(ctx.places_version) / f"boundaries_{level}.geojson"
    if not f.exists():
        return _fail(404, f"boundaries for {level} not available")
    return Response(
        content=f.read_bytes(),
        media_type="application/geo+json",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/indicators")
async def indicators(ctx: TwinContext = Depends(get_twin_context)):
    return _envelope([
        {**asdict(i), "domains": list(i.domains)} for i in ctx.indicators
    ])
