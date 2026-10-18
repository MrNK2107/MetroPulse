"""Versioned Parquet dataset store with a CURRENT.json pointer per source."""
from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd

from twin.paths import TwinPaths
from twin.store.schema import OBSERVATION_COLUMNS

_FILE = "observations.parquet"


def write_dataset(paths: TwinPaths, source_id: str, dataset_version: str,
                  obs: pd.DataFrame) -> Path:
    d = paths.dataset_dir(source_id, dataset_version)
    d.mkdir(parents=True, exist_ok=True)
    out = obs.copy()
    out["dataset_version"] = dataset_version
    out[list(OBSERVATION_COLUMNS)].to_parquet(d / _FILE, index=False)
    return d


def is_published(paths: TwinPaths, source_id: str, dataset_version: str) -> bool:
    return (paths.dataset_dir(source_id, dataset_version) / _FILE).exists()


def read_current(paths: TwinPaths) -> dict[str, str]:
    if not paths.current_file.exists():
        return {}
    return dict(json.loads(paths.current_file.read_text(encoding="utf-8")))


def set_current(paths: TwinPaths, source_id: str, dataset_version: str) -> None:
    cur = read_current(paths)
    cur[source_id] = dataset_version
    paths.published.mkdir(parents=True, exist_ok=True)
    tmp = paths.current_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cur, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, paths.current_file)


def query_observations(
    paths: TwinPaths,
    place_ids: list[str] | None = None,
    indicators: list[str] | None = None,
    source_names: dict[str, str] | None = None,
) -> pd.DataFrame:
    cols = [*OBSERVATION_COLUMNS, "source_name"]
    files = [
        (paths.dataset_dir(s, v) / _FILE).as_posix()
        for s, v in read_current(paths).items()
        if is_published(paths, s, v)
    ]
    if not files:
        return pd.DataFrame({c: pd.Series(dtype="object") for c in cols})
    where, params = [], [files]
    if place_ids is not None:
        where.append("place_id IN (SELECT unnest(?))")
        params.append(list(place_ids))
    if indicators is not None:
        where.append("indicator IN (SELECT unnest(?))")
        params.append(list(indicators))
    sql = "SELECT * FROM read_parquet(?)"
    if where:
        sql += " WHERE " + " AND ".join(where)
    con = duckdb.connect()
    try:
        df = con.execute(sql, params).df()
    finally:
        con.close()
    names = source_names or {}
    df["source_name"] = df["source_id"].map(lambda s: names.get(s, s))
    return df[cols]
