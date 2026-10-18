"""Census 2011 PCA district adapter, apportioned onto current districts."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from twin.pipeline.base import Indicator, PipelineContext, ValidationReport
from twin.places.crosswalk import apply_crosswalk
from twin.store.schema import OBSERVATION_COLUMNS

SOURCE_ID = "census2011-pca-district"
_COLUMNS = {
    "population_total": ("TOT_P", "Total population", "Total persons enumerated in Census 2011"),
    "population_male": ("TOT_M", "Male population", "Male persons enumerated in Census 2011"),
    "population_female": ("TOT_F", "Female population", "Female persons enumerated in Census 2011"),
    "literates_total": ("P_LIT", "Literates", "Literate persons in Census 2011"),
    "workers_total": ("TOT_WORK_P", "Total workers", "Total workers in Census 2011"),
}
_TOLERANCE = 1e-4  # 0.01%


def _code(series: pd.Series, width: int) -> pd.Series:
    """Zero-pad census codes; tolerates text ('10'), numbers (10) and floats (10.0)."""
    n = pd.to_numeric(series.astype(str).str.strip(), errors="coerce")
    return n.map(lambda v: f"{int(v):0{width}d}" if pd.notna(v) else None)


class Census2011Adapter:
    source_id = SOURCE_ID
    transform_version = "census2011-v1"
    indicators = [
        Indicator(i, name, desc, "persons", ("population",), SOURCE_ID)
        for i, (_, name, desc) in _COLUMNS.items()
    ]

    def input_files(self, manual_dir: Path) -> list[Path]:
        return sorted((Path(manual_dir) / "census2011").glob("pca_district*.csv"))

    def observed_period(self, files: list[Path]) -> str:
        return "2011"

    def parse(self, files: list[Path], ctx: PipelineContext) -> pd.DataFrame:
        """The INDIA row's TOT_P is stashed in obs.attrs["india_total"] for validate."""
        raw = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)
        level = raw["Level"].str.strip().str.upper()
        total = raw["TRU"].str.strip().str.lower() == "total"
        india = raw[(level == "INDIA") & total]
        india_total = float(pd.to_numeric(india["TOT_P"]).iloc[0]) if len(india) else None

        d = raw[(level == "DISTRICT") & total]
        old_id = "census2011_district:" + _code(d["State"], 2) + _code(d["District"], 3)
        frames = []
        for ind, (col, _, _) in _COLUMNS.items():
            frames.append(pd.DataFrame({
                "indicator": ind, "place_id": old_id.to_numpy(), "period": "2011",
                "value": pd.to_numeric(d[col]).astype(float).to_numpy(), "unit": "persons",
                "source_id": SOURCE_ID, "dataset_version": "", "trust_label": "fact",
            }))
        old = pd.concat(frames, ignore_index=True)
        out = apply_crosswalk(old, ctx.crosswalk, "sum", weight="area")
        out["trust_label"] = ((out["n_sources"] == 1) & (out["max_weight"] >= 0.999)).map(
            {True: "fact", False: "pattern"}
        )
        attrs = {
            "india_total": india_total,
            "unmapped_old_ids": out.attrs.get("unmapped_old_ids", []),
        }
        out = out[list(OBSERVATION_COLUMNS)].reset_index(drop=True)
        out.attrs.update(attrs)
        return out

    def validate(self, obs: pd.DataFrame, ctx: PipelineContext) -> ValidationReport:
        problems: list[str] = []
        pop = obs[(obs["indicator"] == "population_total") & obs["value"].notna()]
        total = float(pop["value"].sum())
        india = obs.attrs.get("india_total")
        if india is None:
            problems.append("no INDIA row with TOT_P found in input")
        elif abs(total - india) > _TOLERANCE * india:
            problems.append(
                f"national population_total {total:,.0f} differs from INDIA row TOT_P "
                f"{india:,.0f} by more than 0.01%"
            )
        unmapped = obs.attrs.get("unmapped_old_ids", [])
        if unmapped:
            problems.append(f"old census ids with no crosswalk link: {unmapped}")

        have = set(pop["place_id"])
        districts = ctx.places.loc[ctx.places["level"] == "district", "place_id"]
        without = sorted(set(districts) - have)
        linked = set(ctx.crosswalk["new_id"]) if ctx.crosswalk is not None else set()
        missing_linked = sorted(set(without) & linked)
        if missing_linked:
            problems.append(f"crosswalk-linked districts without population_total: {missing_linked}")
        return ValidationReport(
            ok=not problems,
            problems=problems,
            stats={
                "national_population_total": total,
                "districts_with_value": float(len(have)),
                "districts_without_value": without,
            },
        )
