"""Load LGD state/district exports into the place hierarchy."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from twin.places.normalize import normalize_name, normalize_state_code
from twin.store.schema import place_id

# LGD export header -> our column name. Change only here if the export differs.
LGD_COLUMNS: dict[str, str] = {
    "State Code": "state_code",
    "State Name (In English)": "state_name",
    "District Code": "district_code",
    "District Name (In English)": "district_name",
    "Census 2011 Code": "census2011_code",
}

OUT_COLUMNS = [
    "place_id", "level", "lgd_code", "name", "name_norm",
    "parent_id", "state_code", "census2011_code", "boundary_version",
]


STATE_HEADERS = ("State Code", "State Name (In English)")
DISTRICT_HEADERS = ("State Code", "District Code", "District Name (In English)", "Census 2011 Code")


def _read(path: Path, expected: tuple[str, ...]) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    missing = [h for h in expected if h not in df.columns]
    if missing:
        raise ValueError(
            f"{Path(path).name}: missing LGD header(s) {missing}; "
            f"expected {list(expected)}, found {list(df.columns)}"
        )
    df = df.rename(columns=LGD_COLUMNS).apply(lambda c: c.str.strip())
    df["state_code"] = df["state_code"].map(normalize_state_code)
    return df


def _check_unique(df: pd.DataFrame, level: str) -> None:
    dup = df.loc[df["lgd_code"].duplicated(), "lgd_code"].unique()
    if len(dup):
        raise ValueError(f"duplicate {level} lgd_code: {sorted(dup)}")


def _level_frame(level, codes, names, parent_ids, state_codes, census, version):
    out = pd.DataFrame({
        "level": level,
        "lgd_code": codes.to_numpy(),
        "name": names.to_numpy(),
        "parent_id": parent_ids,
        "state_code": state_codes,
        "census2011_code": census,
        "boundary_version": version,
    })
    out["place_id"] = [place_id(level, c) for c in out["lgd_code"]]
    out["name_norm"] = out["name"].map(normalize_name)
    return out


def load_lgd(states_csv: Path, districts_csv: Path, boundary_version: str) -> pd.DataFrame:
    states = _read(states_csv, STATE_HEADERS)
    districts = _read(districts_csv, DISTRICT_HEADERS)
    states = states.rename(columns={"state_code": "lgd_code", "state_name": "name"})
    districts = districts.rename(columns={"district_code": "lgd_code", "district_name": "name"})
    _check_unique(states, "state")
    _check_unique(districts, "district")

    country = pd.DataFrame([{
        "place_id": place_id("country", "IN"), "level": "country", "lgd_code": "IN",
        "name": "India", "name_norm": normalize_name("India"), "parent_id": None,
        "state_code": None, "census2011_code": None, "boundary_version": boundary_version,
    }])
    st = _level_frame(
        "state", states["lgd_code"], states["name"],
        place_id("country", "IN"), states["lgd_code"].to_numpy(), None, boundary_version,
    )
    census = districts["census2011_code"].replace("", pd.NA).astype("string")
    di = _level_frame(
        "district", districts["lgd_code"], districts["name"],
        ("state:" + districts["state_code"]).to_numpy(), districts["state_code"].to_numpy(),
        census.to_numpy(), boundary_version,
    )
    out = pd.concat([country, st, di], ignore_index=True)[OUT_COLUMNS]
    out["census2011_code"] = out["census2011_code"].astype("string")
    return out
