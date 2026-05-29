from datetime import datetime, timezone

import numpy as np
import pytest

from app.core.provenance import DataOrigin, MetricProvenance
from app.rag import build_evidence_pack, coefficient_factors, extract_coefficient_adjustments
from app.simulation.confidence import derived_confidence, label_for_confidence
from app.simulation.overlay import generate_overlay
from app.realtime_models import SnapshotData, SourceStatus
from engine.config import CityConfig
from engine.grid import GridFactory
from engine.models import ParsedScenario, SECTOR_NAMES, SimulationParams
from engine.nl_engine.router import IntentRouter


def _snapshot(sentiment: float = -1.0) -> SnapshotData:
    now = datetime.now(timezone.utc)
    return SnapshotData(
        id="snap-news",
        city="mumbai",
        snapshot_at=now,
        status="fresh",
        quality_score=0.8,
        source_manifest={
            "news": SourceStatus(
                domain="news",
                source="Google News RSS",
                observed_at=now,
                fetched_at=now,
                freshness="fresh",
                confidence=0.8,
                cadence_seconds=3600,
            )
        },
        h3_cells={
            "_city_level_news": {
                "news_sentiment": sentiment,
                "news_pressure": 1.0,
            }
        },
    )


def test_overlay_converts_city_level_snapshot_to_h3_modifiers():
    cfg = CityConfig.load("mumbai")
    indices = ["88608b56c3fffff", "88608b56c7fffff"]
    overlay = generate_overlay(_snapshot(-1.0), indices, cfg)

    assert overlay
    assert set(overlay) == set(indices)
    first = overlay[indices[0]]
    assert first["economic_activity_multiplier"] < 1.0
    assert 0.85 <= first["economic_activity_multiplier"] <= 1.15
    assert 0.90 <= first["migration_pressure_multiplier"] <= 1.10
    assert first["origin"] == "real_time_context"
    assert "Google News RSS" in first["sources"]


def test_overlay_missing_snapshot_falls_back_safely():
    assert generate_overlay(None, ["88608b56c3fffff"], CityConfig.load("mumbai")) == {}


def test_realtime_snapshot_changes_grid_values_and_provenance():
    cfg = CityConfig.load("mumbai")
    boundary = cfg.get_boundary_polygon()
    base_params = SimulationParams(
        city="mumbai",
        sector_deltas={},
        policies_active=[],
        public_works_zone=None,
        horizon_months=6,
        city_config=cfg,
    )
    live_params = SimulationParams(
        city="mumbai",
        sector_deltas={},
        policies_active=[],
        public_works_zone=None,
        horizon_months=6,
        city_config=cfg,
        realtime_snapshot=_snapshot(-1.0),
    )

    base = GridFactory.initialize(boundary, base_params)
    live = GridFactory.initialize(boundary, live_params)

    assert not np.allclose(np.sum(base.K, axis=1), np.sum(live.K, axis=1))
    assert live.overlay_summary["applied"] is True
    assert live.data_origins["K"] == "real_time_context"


def test_confidence_clamps_and_labels():
    assert label_for_confidence(-10) == "Low"
    assert label_for_confidence(0.63) == "Medium"
    assert label_for_confidence(0.8) == "High"
    assert 0.0 <= derived_confidence(
        baseline_confidence=10,
        coefficient_confidence=10,
        realtime_overlay_confidence=10,
        rag_evidence_confidence=10,
    ) <= 1.0


def test_provenance_model_labels_fallback():
    provenance = MetricProvenance(
        origin=DataOrigin.FALLBACK,
        confidence=0.25,
        sources=["city_baseline_yaml"],
    )
    assert provenance.origin == DataOrigin.FALLBACK
    assert provenance.confidence == 0.25


@pytest.mark.asyncio
async def test_rag_retrieves_evidence_and_adjusts_coefficients():
    parsed, _ = await IntentRouter().route("What happens if petrol prices spike in Mumbai?")
    pack = build_evidence_pack(parsed, "What happens if petrol prices spike in Mumbai?")
    adjustments = extract_coefficient_adjustments(parsed.sector_deltas, pack)
    factors = coefficient_factors(adjustments)

    assert pack.items
    assert pack.overall_evidence_confidence > 0
    assert "transport_logistics" in adjustments
    assert "transport_logistics" in factors
    assert adjustments["transport_logistics"].sources


def test_rag_handles_empty_evidence_without_inventing_coefficients():
    parsed = ParsedScenario(
        city="mumbai",
        sector_deltas={sector: 0.0 for sector in SECTOR_NAMES},
        policies_active=[],
        causal_chain="Mumbai unspecified baseline",
        keywords=["mumbai"],
    )
    pack = build_evidence_pack(parsed, parsed.causal_chain)
    adjustments = extract_coefficient_adjustments(parsed.sector_deltas, pack)

    assert adjustments == {}
    assert pack.overall_evidence_confidence >= 0.0


class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, client, name):
        self.client = client
        self.name = name
        self.record = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, record):
        self.record = record
        return self

    def execute(self):
        if self.name == "data_sources" and self.record:
            self.client.created_source = {"id": "source-uuid", **self.record}
            return _FakeExecuteResult([self.client.created_source])
        if self.name == "data_sources":
            return _FakeExecuteResult([])
        if self.name == "raw_observations":
            self.client.raw_records.append(self.record)
            return _FakeExecuteResult([self.record])
        return _FakeExecuteResult([])


class _FakeSupabase:
    def __init__(self):
        self.created_source = None
        self.raw_records = []

    def table(self, name):
        return _FakeTable(self, name)


@pytest.mark.asyncio
async def test_raw_observation_resolves_connector_name_to_data_source_id():
    from app.db import DatabaseClient

    fake = _FakeSupabase()
    db = DatabaseClient()
    db._client = fake

    await db.save_raw_observation(
        source_id="Google News RSS",
        source_domain="news",
        city="mumbai",
        payload={"ok": True},
    )

    assert fake.created_source["name"] == "Google News RSS"
    assert fake.raw_records[0]["source_id"] == "source-uuid"
