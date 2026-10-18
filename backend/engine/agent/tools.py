from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from engine.config import CityConfig
from engine.models import ParsedScenario, SECTOR_LABELS, SECTOR_NAMES
from engine.nl_engine.router import IntentRouter

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "summary": self.summary,
        }


class AgentTools:
    def __init__(
        self,
        intent_router: IntentRouter | None = None,
        db=None,
        city_configs: dict[str, CityConfig] | None = None,
    ) -> None:
        self._router = intent_router or IntentRouter()
        self._db = db
        self._city_configs = city_configs or {}

    async def parse_scenario(self, text: str) -> ToolResult:
        try:
            parsed, confidence = await self._router.route(text)
            active = {s: d for s, d in parsed.sector_deltas.items() if abs(d) > 0}
            summary = (
                f"City: {parsed.city}, "
                f"Sectors: {', '.join(f'{SECTOR_LABELS.get(s,s)} {d:+.0f}%' for s,d in active.items()) or 'none'}, "
                f"Policies: {', '.join(parsed.policies_active) or 'none'}, "
                f"Horizon: {parsed.horizon_months}m, Confidence: {confidence:.2f}"
            )
            return ToolResult(
                success=True,
                data=parsed.model_dump(),
                summary=summary,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def query_case_studies(self, keywords: list[str], city: str = "", top_k: int = 3) -> ToolResult:
        if self._db is None:
            return ToolResult(success=False, error="Database not available")
        try:
            studies = await self._db.search_case_studies(keywords, city=city, top_k=top_k)
            if not studies:
                return ToolResult(success=True, data=[], summary="No matching case studies found.")
            summaries = []
            for s in studies:
                summaries.append(f"- {s.title} ({s.city}, {s.year}): {s.description[:200]}")
            return ToolResult(
                success=True,
                data=[s.model_dump() for s in studies],
                summary="Relevant precedents:\n" + "\n".join(summaries),
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def get_city_profile(self, city: str) -> ToolResult:
        cfg = self._city_configs.get(city)
        if cfg is None:
            try:
                cfg = CityConfig.load(city)
                self._city_configs[city] = cfg
            except Exception as e:
                return ToolResult(success=False, error=f"City '{city}' not found: {e}")
        weights = {SECTOR_LABELS.get(s, s): f"{w*100:.0f}%" for s, w in (cfg.sector_weights or {}).items() if w > 0}
        zones = [z.get("name", "") for z in (cfg.special_zones or [])]
        baselines = cfg.baselines or {}
        profile = {
            "name": cfg.name,
            "state": getattr(cfg, "state", ""),
            "type": getattr(cfg, "city_type", "generic"),
            "population": getattr(cfg, "population", 0),
            "gdp_crores": baselines.get("gdp_estimate_crores", 0),
            "unemployment": baselines.get("unemployment_rate", 0),
            "sector_weights": weights,
            "special_zones": zones,
        }
        weight_str = ", ".join(f"{k}={v}" for k, v in weights.items())
        return ToolResult(
            success=True,
            data=profile,
            summary=(
                f"{cfg.name}: {profile['type']}, pop {profile['population']:,}, "
                f"GDP {profile['gdp_crores']:,.0f}cr, unemployment {profile['unemployment']:.1%}. "
                f"Key sectors: {weight_str}"
            ),
        )

    async def list_cities(self) -> ToolResult:
        from engine.config import list_available_cities
        cities = list_available_cities()
        names = [c["name"] for c in cities]
        return ToolResult(
            success=True,
            data=names,
            summary=f"Available cities: {', '.join(names)}",
        )

    async def compare_sectors(self, city: str, sector_changes: dict[str, float]) -> ToolResult:
        cfg = self._city_configs.get(city)
        if cfg is None:
            try:
                cfg = CityConfig.load(city)
            except Exception as e:
                return ToolResult(success=False, error=str(e))
        weights = cfg.sector_weights or {}
        comparisons = []
        for sector in SECTOR_NAMES:
            delta = sector_changes.get(sector, 0)
            if abs(delta) > 0:
                weight = weights.get(sector, 0)
                impact = delta * weight
                comparisons.append({
                    "sector": SECTOR_LABELS.get(sector, sector),
                    "delta_pct": delta,
                    "weight_pct": round(weight * 100, 1),
                    "weighted_impact": round(impact, 2),
                })
        comparisons.sort(key=lambda x: abs(x["weighted_impact"]), reverse=True)
        return ToolResult(
            success=True,
            data=comparisons,
            summary="Sector impact breakdown:\n" + "\n".join(
                f"  {c['sector']}: {c['delta_pct']:+.0f}% (weight {c['weight_pct']}%, weighted {c['weighted_impact']:+.2f})"
                for c in comparisons
            ),
        )

    def get_tool_descriptions(self) -> str:
        return """AVAILABLE TOOLS:

1. parse_scenario(text: str)
   Parse a natural language urban scenario into structured parameters (city, sector changes, policies).
   Use this to understand what the user wants.

2. query_case_studies(keywords: list[str], city: str = "", top_k: int = 3)
   Search historical Indian urban case studies for relevant precedents.
   Use this to find evidence for or against a policy approach.

3. get_city_profile(city: str)
   Get detailed economic profile of a city (GDP, unemployment, sector weights, special zones).
   Use this to understand a city's economic context.

4. list_cities()
   List all available cities in the simulation platform.

5. compare_sectors(city: str, sector_changes: dict[str, float])
   Quick pre-simulation analysis showing which sectors would be most impacted by changes.
   Use this before committing to a full simulation run."""
