from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    id: str
    title: str
    summary: str
    source_type: str
    city: str | None = None
    country: str | None = "India"
    sectors: list[str] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    shock_types: list[str] = Field(default_factory=list)
    time_period: str | None = None
    observed_effects: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.55
    source_url: str | None = None
    citation: str | None = None
    relevance: float = 0.0
    matched_sectors: list[str] = Field(default_factory=list)


class EvidenceCoverage(BaseModel):
    city_match: str = "none"
    sector_match: str = "none"
    policy_match: str = "none"
    evidence_count: int = 0


class EvidencePack(BaseModel):
    scenario: str
    query_terms: list[str] = Field(default_factory=list)
    items: list[EvidenceItem] = Field(default_factory=list)
    coverage: EvidenceCoverage = Field(default_factory=EvidenceCoverage)
    overall_evidence_confidence: float = 0.0


class CoefficientAdjustment(BaseModel):
    sector: str
    baseline_coefficient: float
    evidence_adjusted_coefficient: float
    confidence: float
    sources: list[str] = Field(default_factory=list)
    reasoning: str
