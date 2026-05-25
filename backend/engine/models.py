"""Scenario-first MetroPulse models.

The WebSocket API uses Pydantic models. The hot simulation path uses small
dataclasses and NumPy arrays so the monthly loop remains deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field


SECTOR_NAMES: list[str] = [
    "it_ites",
    "manufacturing",
    "real_estate",
    "trade_hospitality",
    "transport_logistics",
    "informal",
    "public_admin",
]

SECTOR_LABELS: dict[str, str] = {
    "it_ites": "IT/ITES",
    "manufacturing": "Manufacturing",
    "real_estate": "Real Estate",
    "trade_hospitality": "Trade & Hospitality",
    "transport_logistics": "Transport & Logistics",
    "informal": "Informal Economy",
    "public_admin": "Public Administration",
}

SECTOR_INDEX: dict[str, int] = {name: i for i, name in enumerate(SECTOR_NAMES)}
N_SECTORS = len(SECTOR_NAMES)

PIPELINE_STAGES = (
    "parsing",
    "predicting",
    "simulating",
    "retrieving",
    "synthesizing",
    "done",
)


class StartScenarioMessage(BaseModel):
    type: Literal["START"]
    scenario: str = Field(min_length=4, max_length=2000)


class ParsedScenario(BaseModel):
    city: str
    sector_deltas: dict[str, float] = Field(default_factory=dict)
    policies_active: list[str] = Field(default_factory=list)
    public_works_zone: dict[str, Any] | None = None
    horizon_months: int = Field(default=24)
    causal_chain: str = ""
    keywords: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    assumptions: list[str] = Field(default_factory=list)


class SectorPrediction(BaseModel):
    direction: Literal["up", "down", "stable"] = "stable"
    magnitude: Literal["low", "moderate", "high"] = "low"
    confidence: Literal["high", "medium", "low"] = "medium"
    rationale: str = ""


class Prediction(BaseModel):
    employment_impact: dict[str, SectorPrediction] = Field(default_factory=dict)
    real_estate_impact: dict[str, Any] = Field(default_factory=dict)
    transit_impact: dict[str, Any] = Field(default_factory=dict)
    most_affected_areas: list[str] = Field(default_factory=list)
    counter_intuitive: list[str] = Field(default_factory=list)
    overall_confidence: Literal["high", "medium", "low"] = "medium"
    reasoning: str = ""


class CityProfile(BaseModel):
    id: str
    city: str
    state: str = ""
    population: int = 0
    key_sectors: list[str] = Field(default_factory=list)
    gdp_estimate_crores: int = 0
    known_challenges: list[str] = Field(default_factory=list)
    special_zones: list[str] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    sector_weights: dict[str, float] = Field(default_factory=dict)
    spatial_notes: str = ""
    center: list[float] = Field(default_factory=list)
    zoom: int = 10
    data_quality: str = "estimated"


class CaseStudy(BaseModel):
    id: str = ""
    title: str
    city: str
    year: int
    description: str
    outcome: str = ""
    source: str = ""
    source_type: str = "government"
    tags: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0


@dataclass
class SimulationParams:
    city: str
    sector_deltas: dict[str, float]
    policies_active: list[str]
    public_works_zone: dict[str, Any] | None
    horizon_months: int
    city_config: Any
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "sector_deltas": self.sector_deltas,
            "policies_active": self.policies_active,
            "public_works_zone": self.public_works_zone,
            "horizon_months": self.horizon_months,
            "assumptions": self.assumptions,
        }


@dataclass
class GridState:
    h3_indices: list[str]
    cell_centers: np.ndarray
    K: np.ndarray
    E_formal: np.ndarray
    E_informal: np.ndarray
    R: np.ndarray
    T: np.ndarray
    H: np.ndarray
    F: np.ndarray
    M: np.ndarray
    baselines: dict[str, np.ndarray | float]
    slum_flag: np.ndarray
    sector_weights: np.ndarray
    constants: dict[str, float]
    city_center: tuple[float, float]
    neighbor_pairs: list[tuple[int, int, float]] | None = None
    neighbor_i_idx: np.ndarray | None = None
    neighbor_j_idx: np.ndarray | None = None
    neighbor_weights: np.ndarray | None = None
    zone_flags: dict[str, np.ndarray] = field(default_factory=dict)
    last_delta_k: np.ndarray | None = None
    last_delta_e: np.ndarray | None = None
    active_effects: list[str] = field(default_factory=list)
    public_dist_cache: dict[int, np.ndarray] = field(default_factory=dict)

    @property
    def n_cells(self) -> int:
        return len(self.h3_indices)

    @property
    def n_sectors(self) -> int:
        return self.K.shape[1]


class HexCellState(BaseModel):
    h3Index: str
    economicActivity: float
    delta: float
    jobDensity: float
    jobDensityInformal: float
    realEstateIndex: float
    congestion: float
    housingAffordability: float
    floodRisk: float
    migrationPressure: float
    visualCue: str
    proof: str


class AggregateMetrics(BaseModel):
    gdpDelta: float
    unemploymentRate: float
    realEstateIndex: float
    transitCongestion: float
    informalEmployment: float
    housingAffordability: float
    floodDisruption: float
    migrationBalance: float


class SimulationFrame(BaseModel):
    month: int
    timestamp: str
    cells: list[HexCellState]
    metrics: AggregateMetrics
    activeLoop: str
    proof: dict[str, Any] = Field(default_factory=dict)


# ── NL Conversation WebSocket messages ─────────────────────────────────────


class InputResponseMessage(BaseModel):
    type: Literal["INPUT_RESPONSE"] = "INPUT_RESPONSE"
    text: str
