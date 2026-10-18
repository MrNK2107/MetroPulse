"""Pipeline framework: raw capture, validation, versioned publish."""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import geopandas as gpd
import pandas as pd

from twin.paths import TwinPaths
from twin.store.schema import validate_observations


@dataclass
class Indicator:
    id: str
    name: str
    description: str
    unit: str
    domains: tuple[str, ...]
    source_id: str


@dataclass
class ValidationReport:
    ok: bool
    problems: list[str] = field(default_factory=list)
    stats: dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineContext:
    paths: TwinPaths
    places: pd.DataFrame
    boundaries: dict[str, gpd.GeoDataFrame]
    crosswalk: pd.DataFrame | None
    known_sources: set[str] = field(default_factory=set)


class SourceAdapter(Protocol):
    source_id: str
    indicators: list[Indicator]
    transform_version: str

    def input_files(self, manual_dir: Path) -> list[Path]: ...
    def observed_period(self, files: list[Path]) -> str: ...
    def parse(self, files: list[Path], ctx: PipelineContext) -> pd.DataFrame: ...
    def validate(self, obs: pd.DataFrame, ctx: PipelineContext) -> ValidationReport: ...


@dataclass
class PublishResult:
    dataset_version: str
    published: bool
    reused: bool
    report: ValidationReport


def _sha256(files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()


def run_pipeline(adapter: SourceAdapter, ctx: PipelineContext) -> PublishResult:
    from twin.store import catalog, parquet_store

    sid = adapter.source_id
    if sid not in ctx.known_sources:
        raise KeyError(f"unknown source: {sid}")
    files = sorted(adapter.input_files(ctx.paths.manual), key=lambda p: p.name)
    sha = _sha256(files)
    version = f"{sid}@{adapter.observed_period(files)}#{sha[:12]}"

    if parquet_store.is_published(ctx.paths, sid, version):
        parquet_store.set_current(ctx.paths, sid, version)
        return PublishResult(version, True, True, ValidationReport(ok=True))

    raw_dir = ctx.paths.raw / sid / sha[:12]
    raw_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, raw_dir / f.name)
    (raw_dir / "manifest.json").write_text(json.dumps({
        "files": [f.name for f in files],
        "sizes": {f.name: f.stat().st_size for f in files},
        "sha256": sha,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "transform_version": adapter.transform_version,
    }, indent=2), encoding="utf-8")

    obs = adapter.parse(files, ctx)
    schema_problems = validate_observations(obs)
    adapter_report = adapter.validate(obs, ctx)
    report = ValidationReport(
        ok=not schema_problems and adapter_report.ok,
        problems=[*schema_problems, *adapter_report.problems],
        stats=adapter_report.stats,
    )
    if not report.ok:
        return PublishResult(version, False, False, report)

    out_dir = parquet_store.write_dataset(ctx.paths, sid, version, obs)
    (out_dir / "report.json").write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    catalog.upsert_indicators(ctx.paths, adapter.indicators)
    parquet_store.set_current(ctx.paths, sid, version)
    return PublishResult(version, True, False, report)
