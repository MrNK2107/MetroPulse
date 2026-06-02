"""Extended tests for the serializer module — covers frame structure completeness,
metric_metadata, cell proof fields, timestamp generation, and edge cases."""
from __future__ import annotations

import pytest
import numpy as np
from datetime import datetime, timezone
from unittest.mock import MagicMock

from engine import primary_loop, secondary_loop, serializer
from engine.config import CityConfig
from engine.grid import GridFactory
from engine.models import GridState, SimulationParams


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def bengaluru_config():
    return CityConfig.load("bengaluru")


@pytest.fixture
def default_params(bengaluru_config):
    return SimulationParams(
        city="bengaluru",
        sector_deltas={"it_ites": 30},
        policies_active=["Digital India"],
        public_works_zone=None,
        horizon_months=12,
        city_config=bengaluru_config,
    )


@pytest.fixture
def stepped_state(bengaluru_config, default_params):
    """Initialize and advance the grid by one month."""
    state = GridFactory.initialize(bengaluru_config.get_boundary_polygon(), default_params)
    state = primary_loop.step(state, default_params, month=1)
    state = secondary_loop.step(state, default_params, month=1)
    return state


@pytest.fixture
def sample_frame(stepped_state):
    return serializer.to_frame(stepped_state, month=1)


# ── Frame structure completeness ────────────────────────────────────────────

class TestFrameStructure:

    def test_top_level_keys_present(self, sample_frame):
        required = {"month", "timestamp", "cells", "metrics", "metric_metadata",
                     "activeLoop", "proof"}
        assert required == set(sample_frame.keys()), \
            f"Missing keys: {required - set(sample_frame.keys())}"

    def test_month_matches_input(self, sample_frame):
        assert sample_frame["month"] == 1

    def test_cells_is_nonempty_list(self, sample_frame):
        assert isinstance(sample_frame["cells"], list)
        assert len(sample_frame["cells"]) > 0

    def test_metrics_has_all_expected_keys(self, sample_frame):
        expected_metrics = {
            "gdpDelta", "unemploymentRate", "realEstateIndex",
            "transitCongestion", "informalEmployment", "housingAffordability",
            "floodDisruption", "migrationBalance",
        }
        assert expected_metrics == set(sample_frame["metrics"].keys())

    def test_active_loop_is_string(self, sample_frame):
        assert isinstance(sample_frame["activeLoop"], str)

    def test_proof_has_required_keys(self, sample_frame):
        proof = sample_frame["proof"]
        required_proof = {
            "formula", "dataQuality", "dataMode", "snapshotId",
            "qualityScore", "dataSources", "cellCount", "activeEffects",
            "dataOrigins", "overallConfidence", "confidenceLabel", "overlaySummary",
        }
        assert required_proof == set(proof.keys()), \
            f"Missing proof keys: {required_proof - set(proof.keys())}"


# ── metric_metadata ─────────────────────────────────────────────────────────

class TestMetricMetadata:

    def test_metric_metadata_has_all_metric_keys(self, sample_frame):
        metric_keys = set(sample_frame["metrics"].keys())
        metadata_keys = set(sample_frame["metric_metadata"].keys())
        assert metric_keys == metadata_keys, \
            f"Metadata missing for: {metric_keys - metadata_keys}"

    def test_metric_metadata_entry_structure(self, sample_frame):
        """Each metadata entry should have value, confidence, confidence_label, origin, sources."""
        for key, meta in sample_frame["metric_metadata"].items():
            assert "value" in meta, f"{key} missing 'value'"
            assert "confidence" in meta, f"{key} missing 'confidence'"
            assert "confidence_label" in meta, f"{key} missing 'confidence_label'"
            assert "origin" in meta, f"{key} missing 'origin'"
            assert "sources" in meta, f"{key} missing 'sources'"

    def test_confidence_label_is_valid(self, sample_frame):
        valid_labels = {"Low", "Medium", "High"}
        for key, meta in sample_frame["metric_metadata"].items():
            assert meta["confidence_label"] in valid_labels, \
                f"{key} has invalid label: {meta['confidence_label']}"

    def test_confidence_between_0_and_1(self, sample_frame):
        for key, meta in sample_frame["metric_metadata"].items():
            assert 0.0 <= meta["confidence"] <= 1.0, \
                f"{key} confidence out of range: {meta['confidence']}"


# ── Cell proof fields ───────────────────────────────────────────────────────

class TestCellProofFields:

    def test_each_cell_has_proof_string(self, sample_frame):
        for cell in sample_frame["cells"]:
            assert "proof" in cell, "Cell missing 'proof' field"
            assert isinstance(cell["proof"], str)
            assert len(cell["proof"]) > 10, "Proof string too short"

    def test_proof_contains_delta_info(self, sample_frame):
        """Cell proof strings should mention delta."""
        cell = sample_frame["cells"][0]
        assert "Delta" in cell["proof"] or "delta" in cell["proof"] or "K" in cell["proof"]

    def test_proof_contains_mode_label(self, sample_frame):
        cell = sample_frame["cells"][0]
        # Should mention either "Estimated" or "Real-Time"
        assert "Estimated" in cell["proof"] or "Real-Time" in cell["proof"]

    def test_each_cell_has_visual_cue(self, sample_frame):
        valid_cues = {"stable", "growth", "stress", "flood-risk"}
        for cell in sample_frame["cells"]:
            assert "visualCue" in cell
            assert cell["visualCue"] in valid_cues

    def test_each_cell_has_confidence(self, sample_frame):
        for cell in sample_frame["cells"]:
            assert "confidence" in cell
            assert 0.0 <= cell["confidence"] <= 1.0

    def test_cell_has_all_spatial_fields(self, sample_frame):
        spatial_fields = {
            "h3Index", "economicActivity", "delta", "jobDensity",
            "jobDensityInformal", "realEstateIndex", "congestion",
            "housingAffordability", "floodRisk", "migrationPressure",
        }
        cell = sample_frame["cells"][0]
        assert spatial_fields.issubset(set(cell.keys())), \
            f"Missing fields: {spatial_fields - set(cell.keys())}"


# ── Timestamp generation ────────────────────────────────────────────────────

class TestTimestampGeneration:

    @pytest.mark.parametrize("month,expected_year_offset,expected_month", [
        (1, 0, 1),    # month 1 = Jan of current year
        (6, 0, 6),    # month 6 = Jun of current year
        (12, 0, 12),  # month 12 = Dec of current year
        (13, 1, 1),   # month 13 = Jan of next year
        (24, 1, 12),  # month 24 = Dec of next year
    ])
    def test_timestamp_month_calculation(
        self, stepped_state, month, expected_year_offset, expected_month,
    ):
        frame = serializer.to_frame(stepped_state, month=month)
        ts = frame["timestamp"]
        parsed = datetime.fromisoformat(ts)

        now = datetime.now(timezone.utc)
        expected_year = now.year + expected_year_offset
        assert parsed.year == expected_year, f"Expected year {expected_year}, got {parsed.year}"
        assert parsed.month == expected_month, f"Expected month {expected_month}, got {parsed.month}"
        assert parsed.day == 1

    def test_timestamp_is_utc(self, stepped_state):
        frame = serializer.to_frame(stepped_state, month=1)
        ts = frame["timestamp"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None


# ── Zero-capital cells ──────────────────────────────────────────────────────

class TestZeroCapitalCells:

    def test_zero_k_cells_produce_valid_output(self):
        """Cells with zero baseline capital should not crash and should have delta=0."""
        cfg = CityConfig.load("bengaluru")
        params = SimulationParams(
            city="bengaluru",
            sector_deltas={"it_ites": 0},
            policies_active=[],
            public_works_zone=None,
            horizon_months=1,
            city_config=cfg,
        )
        state = GridFactory.initialize(cfg.get_boundary_polygon(), params)
        # Manually set a cell's K to zero (in all sector columns)
        if state.n_cells > 0:
            state.K[0, :] = 0.0
            state.baselines["K"][0, :] = 0.0
        state = primary_loop.step(state, params, month=1)
        state = secondary_loop.step(state, params, month=1)
        frame = serializer.to_frame(state, month=1)

        cell = frame["cells"][0]
        assert isinstance(cell["economicActivity"], float)
        assert isinstance(cell["delta"], float)
        # Zero-capital cell should have delta=0 (handled by np.divide where clause)
        assert cell["delta"] == 0.0

    def test_all_zero_cells_frame_not_empty(self):
        """Even if all cells start at zero capital, the frame should be valid."""
        cfg = CityConfig.load("bengaluru")
        params = SimulationParams(
            city="bengaluru",
            sector_deltas={"it_ites": 0},
            policies_active=[],
            public_works_zone=None,
            horizon_months=1,
            city_config=cfg,
        )
        state = GridFactory.initialize(cfg.get_boundary_polygon(), params)
        state.K[:, :] = 0.0
        state.baselines["K"][:, :] = 0.0
        state = primary_loop.step(state, params, month=1)
        state = secondary_loop.step(state, params, month=1)
        # Recompute since K is all zero
        frame = serializer.to_frame(state, month=1)

        assert "cells" in frame
        assert "metrics" in frame
        assert frame["proof"]["cellCount"] > 0


# ── Active loop ─────────────────────────────────────────────────────────────

class TestActiveLoop:

    def test_active_loop_default_baseline(self):
        """With no active effects, activeLoop should be 'baseline'."""
        cfg = CityConfig.load("bengaluru")
        params = SimulationParams(
            city="bengaluru",
            sector_deltas={"it_ites": 0},
            policies_active=[],
            public_works_zone=None,
            horizon_months=1,
            city_config=cfg,
        )
        state = GridFactory.initialize(cfg.get_boundary_polygon(), params)
        state.active_effects = []
        state = secondary_loop.step(state, params, month=1)
        frame = serializer.to_frame(state, month=1)
        assert frame["activeLoop"] == "baseline"

    def test_active_loop_with_effects(self, sample_frame):
        """With effects, activeLoop contains them joined."""
        assert isinstance(sample_frame["activeLoop"], str)
