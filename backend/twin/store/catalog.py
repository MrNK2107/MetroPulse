"""Indicator catalogue stored as Parquet; fuzzy search (M2 swaps in embeddings)."""
from __future__ import annotations

from dataclasses import asdict

import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz.utils import default_process

from twin.paths import TwinPaths
from twin.pipeline.base import Indicator

_MIN_SCORE = 60


def _file(paths: TwinPaths):
    return paths.published / "catalog" / "indicators.parquet"


def list_indicators(paths: TwinPaths) -> list[Indicator]:
    f = _file(paths)
    if not f.exists():
        return []
    df = pd.read_parquet(f)
    return [
        Indicator(r.id, r.name, r.description, r.unit, tuple(r.domains), r.source_id)
        for r in df.itertuples(index=False)
    ]


def upsert_indicators(paths: TwinPaths, indicators: list[Indicator]) -> None:
    merged = {i.id: i for i in list_indicators(paths)}
    merged.update({i.id: i for i in indicators})
    rows = [{**asdict(i), "domains": list(i.domains)} for i in merged.values()]
    df = pd.DataFrame(rows, columns=["id", "name", "description", "unit", "domains", "source_id"])
    f = _file(paths)
    f.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(f, index=False)


def search_indicators(paths: TwinPaths, query: str, limit: int = 10) -> list[Indicator]:
    scored = [
        (fuzz.WRatio(query, f"{i.name} {i.description}", processor=default_process), i) for i in list_indicators(paths)
    ]
    hits = sorted((s for s in scored if s[0] >= _MIN_SCORE), key=lambda s: -s[0])
    return [i for _, i in hits[:limit]]
