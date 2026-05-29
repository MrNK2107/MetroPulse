from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field


DataDomain = Literal["mobility", "jobs", "land_value", "census", "news"]
FreshnessStatus = Literal["fresh", "stale", "missing", "demo", "static"]
SnapshotStatus = Literal["fresh", "degraded", "unavailable", "demo"]


class SourceStatus(BaseModel):
    domain: DataDomain
    source: str
    observed_at: datetime | None = None
    fetched_at: datetime | None = None
    freshness: FreshnessStatus
    confidence: float = Field(ge=0.0, le=1.0)
    cadence_seconds: int
    license: str = "public/free where available"
    notes: str = ""


class SnapshotQuality(BaseModel):
    status: SnapshotStatus
    quality_score: float = Field(ge=0.0, le=1.0)
    source_manifest: dict[str, SourceStatus]
    message: str


@dataclass
class SnapshotData:
    id: str
    city: str
    snapshot_at: datetime
    status: SnapshotStatus
    quality_score: float
    source_manifest: dict[str, SourceStatus]
    h3_cells: dict[str, dict[str, float]] = field(default_factory=dict)
    aggregate_metrics: dict[str, float] = field(default_factory=dict)

    @property
    def is_realtime(self) -> bool:
        return self.status in {"fresh", "degraded"}

    def manifest_for_json(self) -> dict[str, dict[str, Any]]:
        return {
            domain: status.model_dump(mode="json")
            for domain, status in self.source_manifest.items()
        }


@dataclass
class SnapshotArrays:
    K: np.ndarray | None = None
    E_formal: np.ndarray | None = None
    E_informal: np.ndarray | None = None
    R: np.ndarray | None = None
    T: np.ndarray | None = None
    H: np.ndarray | None = None
    F: np.ndarray | None = None
    M: np.ndarray | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
