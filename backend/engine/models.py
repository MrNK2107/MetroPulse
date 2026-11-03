"""Shared MetroPulse models: sector vocabulary, parsed scenarios and case studies.

Used by the agent's scenario parser (``engine.nl_engine``), its tools and ``app.db``.
"""

from __future__ import annotations

from typing import Any, Literal

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


class ParsedScenario(BaseModel):
    city: str
    sector_deltas: dict[str, float] = Field(default_factory=dict)
    policies_active: list[str] = Field(default_factory=list)
    public_works_zone: dict[str, Any] | None = None
    horizon_months: int = Field(default=24, ge=1, le=120)
    causal_chain: str = ""
    keywords: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    assumptions: list[str] = Field(default_factory=list)


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
    observed_effects: dict[str, Any] = Field(default_factory=dict)
    relevance_tags: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)
    relevance_tier: Literal["exact", "related", "weak"] = "weak"
    matched_city: bool = False
    matched_sectors: list[str] = Field(default_factory=list)
    matched_policies: list[str] = Field(default_factory=list)


class CaseStudyMatchContext(BaseModel):
    city: str | None = None
    sectors: list[str] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    sector_directions: dict[str, Literal["positive", "negative", "mixed"]] = Field(default_factory=dict)


class CaseRetrievalAudit(BaseModel):
    query_city: str | None = None
    query_sectors: list[str] = Field(default_factory=list)
    query_policies: list[str] = Field(default_factory=list)
    returned_count: int = 0
    omitted_weak_count: int = 0
    retrieval_mode: Literal["strict"] = "strict"
