"""Optional sync of the published twin backbone and catalogue into Postgres/PostGIS."""
from __future__ import annotations

import json
import logging
import re

import geopandas as gpd
import pandas as pd
import psycopg2
from psycopg2.extras import Json, execute_values

from twin.paths import TwinPaths
from twin.store import catalog
from twin.store.parquet_store import read_current

log = logging.getLogger(__name__)

_LEVELS = ("district", "state", "country")

_PLACES_SQL = """
INSERT INTO twin_places (place_id, level, lgd_code, name, parent_id, state_code, boundary_version, geom)
VALUES %s
ON CONFLICT (place_id) DO UPDATE SET
  level = EXCLUDED.level, lgd_code = EXCLUDED.lgd_code, name = EXCLUDED.name,
  parent_id = EXCLUDED.parent_id, state_code = EXCLUDED.state_code,
  boundary_version = EXCLUDED.boundary_version, geom = EXCLUDED.geom
"""
_PLACES_TEMPLATE = "(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)))"

_INDICATORS_SQL = """
INSERT INTO twin_indicators (id, name, description, unit, domains, source_id)
VALUES %s
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name, description = EXCLUDED.description, unit = EXCLUDED.unit,
  domains = EXCLUDED.domains, source_id = EXCLUDED.source_id
"""

_VERSIONS_SQL = """
INSERT INTO dataset_versions (source_key, version, checksum, transform_version, observed_at, manifest)
VALUES %s
ON CONFLICT (source_key, version, checksum) DO UPDATE SET
  transform_version = EXCLUDED.transform_version, observed_at = EXCLUDED.observed_at,
  manifest = EXCLUDED.manifest
"""


def _none(v):
    return None if v is None or (isinstance(v, float) and v != v) else v


def _place_rows(paths: TwinPaths, version: str) -> list[tuple]:
    d = paths.places_dir(version)
    places = pd.read_parquet(d / "places.parquet")
    wkt: dict[str, str] = {}
    for lv in _LEVELS:
        f = d / f"boundaries_{lv}.parquet"
        if f.exists():
            gdf = gpd.read_parquet(f)
            wkt.update({pid: g.wkt for pid, g in zip(gdf["place_id"], gdf.geometry) if g is not None})
    return [
        (r.place_id, r.level, _none(r.lgd_code), r.name, _none(r.parent_id),
         _none(r.state_code), r.boundary_version, wkt.get(r.place_id))
        for r in places.itertuples(index=False)
    ]


def _version_rows(paths: TwinPaths) -> list[tuple]:
    rows = []
    for source_id, version in sorted(read_current(paths).items()):
        if source_id == "places":
            continue
        d = paths.dataset_dir(source_id, version)
        report_file = d / "report.json"
        if not report_file.exists():
            continue
        short = version.rsplit("#", 1)[-1]
        raw = paths.raw / source_id / short / "manifest.json"
        raw_manifest = json.loads(raw.read_text(encoding="utf-8")) if raw.exists() else {}
        period = re.search(r"@([^#]+)#", version)
        observed = f"{period.group(1)}-01-01" if period and re.fullmatch(r"\d{4}", period.group(1)) else None
        rows.append((
            source_id, version, raw_manifest.get("sha256", short),
            raw_manifest.get("transform_version", ""), observed,
            Json(json.loads(report_file.read_text(encoding="utf-8"))),
        ))
    return rows


def sync_to_postgres(paths: TwinPaths, dsn: str) -> dict[str, int]:
    """Upsert places, indicators and dataset_versions; returns row counts per table."""
    if not dsn:
        log.info("postgres sync skipped")
        return {}
    place_version = read_current(paths).get("places")
    places = _place_rows(paths, place_version) if place_version else []
    indicators = [
        (i.id, i.name, i.description, i.unit, list(i.domains), i.source_id)
        for i in catalog.list_indicators(paths)
    ]
    versions = _version_rows(paths)

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            if places:
                execute_values(cur, _PLACES_SQL, places, template=_PLACES_TEMPLATE)
            if indicators:
                execute_values(cur, _INDICATORS_SQL, indicators)
            if versions:
                execute_values(cur, _VERSIONS_SQL, versions)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"twin_places": len(places), "twin_indicators": len(indicators), "dataset_versions": len(versions)}
