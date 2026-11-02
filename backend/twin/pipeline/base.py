"""Pipeline framework: raw capture, validation, versioned publish."""
from __future__ import annotations

import hashlib
import json
import os
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
    # Boundary version the datasets are built against (the to-be-current places);
    # its places_digest.txt goes into every dataset version hash.
    places_version: str | None = None


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


HASH_CHUNK_BYTES = 4 * 1024 * 1024
# Inputs up to this size are copied into raw/; larger ones (e.g. the ~11.6 GB VIIRS
# global GeoTIFF) are hard-linked when possible, otherwise only referenced by path.
RAW_COPY_MAX_BYTES = 200 * 1024 * 1024
PLACES_DIGEST_FILE = "places_digest.txt"


def _hash_inputs(
    files: list[Path], transform_version: str, places_digest: str
) -> tuple[str, dict[str, str]]:
    """Version hash plus per-file sha256, reading each file once in HASH_CHUNK_BYTES chunks.

    Hashed content order: for each file (sorted by name) its name + NUL then its bytes;
    then NUL + transform_version; then NUL + places digest.
    """
    h = hashlib.sha256()
    per_file: dict[str, str] = {}
    for f in files:
        h.update(f.name.encode("utf-8") + b"\x00")
        fh = hashlib.sha256()
        with open(f, "rb") as stream:
            while chunk := stream.read(HASH_CHUNK_BYTES):
                h.update(chunk)
                fh.update(chunk)
        per_file[f.name] = fh.hexdigest()
    h.update(b"\x00" + transform_version.encode("utf-8"))
    h.update(b"\x00" + places_digest.encode("utf-8"))
    return h.hexdigest(), per_file


def _sha256(files: list[Path], transform_version: str, places_digest: str) -> str:
    return _hash_inputs(files, transform_version, places_digest)[0]


def read_places_digest(paths: TwinPaths, places_version: str | None) -> str:
    """Content digest of a built places version ("" when no places version is given)."""
    if not places_version:
        return ""
    f = paths.places_dir(places_version) / PLACES_DIGEST_FILE
    if not f.exists():
        raise FileNotFoundError(f"{f} missing; rebuild places version {places_version!r}")
    return f.read_text(encoding="utf-8").strip()


def _capture_raw(raw_dir: Path, files: list[Path], file_sha: dict[str, str]) -> list[dict]:
    """Record every input; copy small ones, hard-link (or just reference) large ones."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for f in files:
        size = f.stat().st_size
        dest = raw_dir / f.name
        entry = {"name": f.name, "size": size, "sha256": file_sha[f.name],
                 "copied": False, "hardlinked": False}
        if size <= RAW_COPY_MAX_BYTES:
            shutil.copy2(f, dest)
            entry["copied"] = True
        else:
            try:
                if dest.exists():
                    dest.unlink()
                os.link(f, dest)
                entry["hardlinked"] = True
            except OSError:
                entry["source_path"] = str(f.resolve())
        entries.append(entry)
    return entries


def run_pipeline(
    adapter: SourceAdapter, ctx: PipelineContext, set_current_on_publish: bool = True
) -> PublishResult:
    """Parse, validate and publish one source.

    With set_current_on_publish=False the dataset is written (or reused) but CURRENT.json
    is left alone, so the caller can switch places and datasets live together.
    """
    from twin.store import catalog, parquet_store

    sid = adapter.source_id
    if sid not in ctx.known_sources:
        raise KeyError(f"unknown source: {sid}")
    files = sorted(adapter.input_files(ctx.paths.manual), key=lambda p: p.name)
    places_digest = read_places_digest(ctx.paths, ctx.places_version)
    sha, file_sha = _hash_inputs(files, adapter.transform_version, places_digest)
    version = f"{sid}@{adapter.observed_period(files)}#{sha[:12]}"

    if parquet_store.is_published(ctx.paths, sid, version):
        catalog.upsert_indicators(ctx.paths, adapter.indicators)
        if set_current_on_publish:
            parquet_store.set_current(ctx.paths, sid, version)
        return PublishResult(version, True, True, ValidationReport(ok=True))

    raw_dir = ctx.paths.raw / sid / sha[:12]
    entries = _capture_raw(raw_dir, files, file_sha)
    (raw_dir / "manifest.json").write_text(json.dumps({
        "files": entries,
        "sha256": sha,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "transform_version": adapter.transform_version,
        "places_version": ctx.places_version,
        "places_digest": places_digest,
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

    report_json = {**asdict(report), "places_version": ctx.places_version,
                   "places_digest": places_digest}
    parquet_store.write_dataset(ctx.paths, sid, version, obs, report_json)
    catalog.upsert_indicators(ctx.paths, adapter.indicators)
    if set_current_on_publish:
        parquet_store.set_current(ctx.paths, sid, version)
    return PublishResult(version, True, False, report)
