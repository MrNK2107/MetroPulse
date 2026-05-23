from pydantic import BaseModel, Field
from typing import Any


class FDIParams(BaseModel):
    tech: float = Field(default=0.0, ge=-100.0, le=100.0)
    manufacturing: float = Field(default=0.0, ge=-100.0, le=100.0)
    realEstate: float = Field(default=0.0, ge=-100.0, le=100.0)


class SimulationParams(BaseModel):
    fdi: FDIParams
    publicWorksZone: dict[str, Any] | None = None
    horizonMonths: int = Field(default=12, ge=6, le=60)


class HexCellState(BaseModel):
    h3Index: str
    economicActivity: float
    delta: float
    jobDensity: float
    realEstateIndex: float
    congestion: float


class AggregateMetrics(BaseModel):
    gdpDelta: float
    unemploymentRate: float
    realEstateIndex: float
    transitCongestion: float


class SimulationFrame(BaseModel):
    month: int
    timestamp: str
    cells: list[HexCellState]
    metrics: AggregateMetrics
