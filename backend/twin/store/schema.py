"""Canonical observation schema and place-id helpers."""
from __future__ import annotations

from typing import Literal

import pandas as pd

OBSERVATION_COLUMNS: tuple[str, ...] = (
    "indicator", "place_id", "period", "value", "unit",
    "source_id", "dataset_version", "trust_label",
)

TrustLabel = Literal["fact", "pattern", "projection"]
TRUST_LABELS: frozenset[str] = frozenset({"fact", "pattern", "projection"})
PLACE_LEVELS: tuple[str, ...] = (
    "country", "state", "district", "census2011_district", "h3r5", "h3r7",
)
KEY_COLUMNS: list[str] = ["indicator", "place_id", "period", "dataset_version"]


def place_id(level: str, code: str) -> str:
    return f"{level}:{code}"


def parse_place_id(pid: str) -> tuple[str, str]:
    level, sep, code = pid.partition(":")
    if not sep or not level or not code:
        raise ValueError(f"invalid place_id: {pid!r}")
    return level, code


def validate_observations(df: pd.DataFrame) -> list[str]:
    """Return a list of problems; empty means valid. Null values are allowed."""
    problems: list[str] = []
    missing = [c for c in OBSERVATION_COLUMNS if c not in df.columns]
    problems.extend(f"missing column: {c}" for c in missing)
    if "trust_label" in df.columns:
        bad = df.loc[~df["trust_label"].isin(TRUST_LABELS), "trust_label"]
        if len(bad):
            problems.append(f"invalid trust_label values: {sorted(map(str, bad.unique()))}")
    if all(c in df.columns for c in KEY_COLUMNS):
        n = int(df.duplicated(subset=KEY_COLUMNS).sum())
        if n:
            problems.append(f"duplicate keys on {tuple(KEY_COLUMNS)}: {n} row(s)")
    return problems
