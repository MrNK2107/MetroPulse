"""Resolve free-text place names to place rows: exact, alias, then fuzzy."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
from rapidfuzz import fuzz, process

from twin.places.normalize import normalize_name

FUZZY_CUTOFF = 90.0


@dataclass
class PlaceMatch:
    place_id: str
    name: str
    level: str
    state_code: str | None
    score: float
    method: Literal["exact", "alias", "fuzzy"]


@dataclass
class Resolution:
    matches: list[PlaceMatch]
    ambiguous: bool


def load_aliases(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "state_code" not in df.columns:
        df["state_code"] = ""
    df["alias"] = df["alias"].map(normalize_name)
    df["canonical"] = df["canonical"].map(normalize_name)
    df["state_code"] = df["state_code"].str.strip().replace("", pd.NA)
    return df[["alias", "canonical", "state_code"]].reset_index(drop=True)


class PlaceResolver:
    def __init__(self, places: pd.DataFrame, aliases: pd.DataFrame):
        self._places = places.reset_index(drop=True)
        self._aliases = aliases.reset_index(drop=True)

    def _scope(self, level: str | None, state_code: str | None) -> pd.DataFrame:
        p = self._places
        mask = pd.Series(True, index=p.index)
        if level is not None:
            mask &= p["level"] == level
        if state_code is not None:
            mask &= p["state_code"] == state_code
        return p[mask]

    def _alias_targets(self, norm: str, scope: pd.DataFrame) -> pd.DataFrame:
        a = self._aliases[self._aliases["alias"] == norm]
        if a.empty:
            return scope.iloc[0:0]
        pieces = []
        for canonical, st in zip(a["canonical"], a["state_code"]):
            hit = scope["name_norm"] == canonical
            if not pd.isna(st):
                hit &= scope["state_code"] == st
            pieces.append(scope[hit])
        return pd.concat(pieces)

    @staticmethod
    def _to_matches(rows: pd.DataFrame, scores, method: str) -> list[PlaceMatch]:
        out = []
        for (_, r), s in zip(rows.iterrows(), scores):
            sc = r["state_code"]
            out.append(
                PlaceMatch(
                    place_id=r["place_id"],
                    name=r["name"],
                    level=r["level"],
                    state_code=None if pd.isna(sc) else str(sc),
                    score=float(s),
                    method=method,  # type: ignore[arg-type]
                )
            )
        return out

    def resolve(
        self,
        text: str,
        level: str | None = None,
        state_code: str | None = None,
        limit: int = 5,
    ) -> Resolution:
        norm = normalize_name(text)
        if not norm:
            return Resolution([], False)
        scope = self._scope(level, state_code)

        exact = scope[scope["name_norm"] == norm]
        alias = self._alias_targets(norm, scope)
        matches = self._to_matches(exact, [100.0] * len(exact), "exact")
        seen = {m.place_id for m in matches}
        alias = alias[~alias["place_id"].isin(seen)].drop_duplicates("place_id")
        matches += self._to_matches(alias, [100.0] * len(alias), "alias")

        if not matches and not scope.empty:
            found = process.extract(
                norm,
                scope["name_norm"].tolist(),
                scorer=fuzz.WRatio,
                score_cutoff=FUZZY_CUTOFF,
                limit=limit,
            )
            if found:
                idx = [i for _, _, i in found]
                matches = self._to_matches(
                    scope.iloc[idx], [s for _, s, _ in found], "fuzzy"
                )

        matches.sort(key=lambda m: -m.score)
        matches = matches[:limit]
        ambiguous = False
        if len(matches) > 1:
            top = [m for m in matches if m.score == matches[0].score]
            ambiguous = len(top) > 1 and len({m.state_code for m in top}) > 1
        return Resolution(matches, ambiguous)
