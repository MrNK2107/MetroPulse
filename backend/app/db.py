from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID, uuid4

from engine.config import CityConfig, list_available_cities
from engine.models import CaseStudy, CityProfile

logger = logging.getLogger(__name__)

LOCAL_CASE_STUDIES: list[CaseStudy] = [
    CaseStudy(
        id="bengaluru-it-infra",
        title="Bengaluru IT Boom and Infrastructure Stress",
        city="Bengaluru",
        year=2023,
        description="IT/ITES growth increased employment and land values while worsening congestion and water stress.",
        outcome="Tech growth boosted high-skill jobs but strained mobility and housing affordability.",
        source="Karnataka economic survey and urban mobility reporting",
        tags=["it_ites", "congestion", "housing"],
        sectors=["it_ites", "real_estate"],
        policies=["Digital India"],
    ),
    CaseStudy(
        id="hyderabad-pharma-sez",
        title="Hyderabad Pharma and Genome Valley SEZ Expansion",
        city="Hyderabad",
        year=2022,
        description="Pharma cluster investment around Genome Valley concentrated industrial employment and supplier activity.",
        outcome="SEZ-linked manufacturing growth produced localized employment gains and logistics demand.",
        source="Telangana industry department reports",
        tags=["manufacturing", "sez", "pharma"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["SEZ Notification", "Make in India"],
    ),
    CaseStudy(
        id="delhi-metro-property",
        title="Delhi Metro Expansion and Property Value Effects",
        city="Delhi NCR",
        year=2024,
        description="Metro access improved labor mobility and increased property premiums near stations.",
        outcome="Transit investment raised adjacent land values while redistributing commuting pressure.",
        source="Urban transport academic studies",
        tags=["transport_logistics", "real_estate", "metro"],
        sectors=["transport_logistics", "real_estate"],
        policies=["Smart City Mission"],
    ),
    CaseStudy(
        id="mumbai-mill-land",
        title="Mumbai Mill Land to Real Estate Transformation",
        city="Mumbai",
        year=2018,
        description="Former industrial land shifted toward commercial and high-end real-estate activity.",
        outcome="Manufacturing decline coincided with real-estate appreciation and affordability stress.",
        source="Mumbai planning and housing studies",
        tags=["manufacturing", "real_estate", "housing"],
        sectors=["manufacturing", "real_estate"],
        policies=["RERA Compliance"],
    ),
    CaseStudy(
        id="chennai-port-corridor",
        title="Chennai Port-Led Industrial Corridor Growth",
        city="Chennai",
        year=2023,
        description="Port and auto-sector activity shaped logistics corridors and formal manufacturing employment.",
        outcome="Transport investment amplified manufacturing gains but increased corridor congestion.",
        source="Tamil Nadu industry and port trust reports",
        tags=["manufacturing", "transport_logistics", "port"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="pune-it-corridor",
        title="Pune IT Corridor and Hinjewadi Growth",
        city="Pune",
        year=2023,
        description="IT parks along Hinjewadi and Kharadi corridors drove employment but created east-west mobility imbalance.",
        outcome="IT employment growth concentrated in western suburbs, worsening commute times for eastern residents.",
        source="Pune metropolitan development authority reports",
        tags=["it_ites", "transport", "housing"],
        sectors=["it_ites", "transport_logistics"],
        policies=["Digital India", "Smart City Mission"],
    ),
    CaseStudy(
        id="jaipur-tourism-heritage",
        title="Jaipur Heritage Tourism and Real Estate Pressure",
        city="Jaipur",
        year=2022,
        description="UNESCO World Heritage designation boosted tourism but increased commercial pressure on old city areas.",
        outcome="Tourism growth raised hospitality employment while straining heritage zone infrastructure.",
        source="Rajasthan tourism department reports",
        tags=["trade_hospitality", "real_estate", "heritage"],
        sectors=["trade_hospitality", "real_estate"],
        policies=["Smart City Mission"],
    ),
    CaseStudy(
        id="lucknow-metro-informal",
        title="Lucknow Metro and Informal Economy Displacement",
        city="Lucknow",
        year=2023,
        description="Metro construction displaced street vendors and informal workers from key corridors.",
        outcome="Transit formalization improved mobility but reduced informal livelihood access in transit zones.",
        source="UP urban development studies",
        tags=["transport_logistics", "informal", "displacement"],
        sectors=["transport_logistics", "informal"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    CaseStudy(
        id="kolkata-port-logistics",
        title="Kolkata Port Modernization and Logistics Corridor",
        city="Kolkata",
        year=2021,
        description="Kolkata Port Trust modernization increased container throughput but added heavy truck traffic to urban areas.",
        outcome="Port efficiency gains were offset by corridor congestion and air quality concerns.",
        source="Kolkata Port Trust annual reports",
        tags=["transport_logistics", "manufacturing", "congestion"],
        sectors=["transport_logistics", "manufacturing"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="ahmedabad-textile-decline",
        title="Ahmedabad Textile Mill Decline and Urban Renewal",
        city="Ahmedabad",
        year=2019,
        description="Decline of textile mills in eastern Ahmedabad led to large-scale land conversion to commercial and residential use.",
        outcome="Mill land redevelopment increased real estate values but displaced working-class communities.",
        source="Gujarat urban development studies",
        tags=["manufacturing", "real_estate", "informal"],
        sectors=["manufacturing", "real_estate"],
        policies=["RERA Compliance"],
    ),
    CaseStudy(
        id="chandigarh-planned-infrastructure",
        title="Chandigarh Planned City Infrastructure Resilience",
        city="Chandigarh",
        year=2024,
        description="Chandigarh's planned sector-grid layout provided better infrastructure resilience but limited affordable housing supply.",
        outcome="Planning advantages in transit and green space coexist with housing affordability challenges for migrants.",
        source="Chandigarh administration planning reports",
        tags=["housing", "transport", "planning"],
        sectors=["real_estate", "public_admin"],
        policies=["AMRUT", "PM Awas Yojana"],
    ),
    CaseStudy(
        id="bhubaneswar-smart-city",
        title="Bhubaneswar Smart City Mission Implementation",
        city="Bhubaneswar",
        year=2023,
        description="Bhubaneswar won India's Smart City Challenge and invested in integrated command center and transit upgrades.",
        outcome="Smart infrastructure improved city services but benefits concentrated in central zones.",
        source="Bhubaneswar Smart City Limited reports",
        tags=["smart_city", "transport", "digital"],
        sectors=["public_admin", "transport_logistics"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    CaseStudy(
        id="pmay-national-housing",
        title="PM Awas Yojana Affordable Housing Outcomes",
        city="Hyderabad",
        year=2023,
        description="PMAY subsidies increased affordable housing construction in peri-urban areas across Indian cities.",
        outcome="Housing supply increased but locations often lacked transit connectivity and employment access.",
        source="Ministry of Housing and Urban Affairs reports",
        tags=["housing", "affordable", "policy"],
        sectors=["real_estate", "informal"],
        policies=["PM Awas Yojana"],
    ),
    CaseStudy(
        id="amrut-water-sanitation",
        title="AMRUT Water and Sanitation Infrastructure Outcomes",
        city="Chennai",
        year=2022,
        description="AMRUT funded water supply augmentation and sewerage network expansion in 500 cities.",
        outcome="Infrastructure improved but maintenance capacity varied widely across municipal corporations.",
        source="AMRUT annual reports and CAG audits",
        tags=["water", "sanitation", "infrastructure"],
        sectors=["public_admin"],
        policies=["AMRUT"],
    ),
    CaseStudy(
        id="make-in-india-corridors",
        title="Make in India Manufacturing Corridor Development",
        city="Ahmedabad",
        year=2024,
        description="Delhi-Mumbai Industrial Corridor and DMIC nodes attracted manufacturing investment along transport routes.",
        outcome="Corridor manufacturing created formal jobs but increased freight traffic on urban peripheries.",
        source="DMICDC project reports",
        tags=["manufacturing", "corridor", "logistics"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["Make in India", "SEZ Notification"],
    ),
]


class DatabaseClient:
    """Supabase-backed DB with in-memory fallback when credentials are missing."""

    def __init__(self):
        self._saved: list[dict[str, Any]] = []
        self._client: Any = None

    async def connect(self):
        from app.config import settings
        if settings.supabase_url and settings.supabase_key:
            try:
                from supabase import create_client
                self._client = create_client(settings.supabase_url, settings.supabase_key)
                logger.info("Connected to Supabase at %s", settings.supabase_url)
            except Exception as e:
                logger.warning("Failed to connect to Supabase, using in-memory fallback: %s", e)
                self._client = None
        else:
            logger.info("No Supabase credentials configured, using in-memory storage")

    async def close(self):
        self._client = None

    async def list_regions(self) -> list[dict[str, Any]]:
        return list_available_cities()

    async def get_region_profile(self, region_id: str) -> dict[str, Any] | None:
        try:
            cfg = CityConfig.load(region_id)
        except FileNotFoundError:
            return None
        profile = CityProfile(
            id=region_id,
            city=cfg.name,
            state=cfg.state,
            population=cfg.population,
            key_sectors=sorted(cfg.sector_weights, key=cfg.sector_weights.get, reverse=True)[:4],
            gdp_estimate_crores=int(cfg.baselines.get("gdp_estimate_crores", 0)),
            known_challenges=_known_challenges(cfg.city_type),
            special_zones=[zone.get("name", "Zone") for zone in cfg.special_zones],
            sector_weights=cfg.sector_weights,
            spatial_notes=f"{cfg.name} uses estimated H3 baselines from city center distance, sector weights, flood/slum proxies, and configured policy zones.",
            center=cfg.center,
            zoom=cfg.zoom,
            data_quality="estimated",
        )
        return profile.model_dump()

    async def get_region_boundary(self, region_id: str) -> dict[str, Any] | None:
        try:
            cfg = CityConfig.load(region_id)
            return cfg.get_boundary_polygon()
        except Exception:
            return None

    async def get_baseline(self, region_id: UUID | str) -> dict[str, Any] | None:
        rid = str(region_id)
        try:
            cfg = CityConfig.load(rid)
        except FileNotFoundError:
            return None
        return {
            "region_id": rid,
            "gdp_index": 1.0,
            "unemployment": cfg.baselines.get("unemployment_rate", 0.05),
            "real_estate_idx": 1.0,
            "transit_load": 0.5,
            "data_quality": "estimated",
        }

    async def list_simulations(self, page: int = 1, per_page: int = 20) -> list[dict[str, Any]]:
        if self._client:
            start = (page - 1) * per_page
            result = await asyncio.to_thread(
                lambda: self._client.table("simulations")
                .select("id,region_id,params,horizon_months,result_summary,created_at")
                .order("created_at", desc=True)
                .range(start, start + per_page - 1)
                .execute()
            )
            return result.data
        start = (page - 1) * per_page
        return self._saved[start : start + per_page]

    async def get_simulation(self, simulation_id: UUID) -> dict[str, Any] | None:
        if self._client:
            result = await asyncio.to_thread(
                lambda: self._client.table("simulations")
                .select("*")
                .eq("id", str(simulation_id))
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        return next((item for item in self._saved if item["id"] == str(simulation_id)), None)

    async def save_simulation(
        self,
        region_id: UUID | None,
        params: dict[str, Any],
        horizon_months: int,
        result_summary: dict[str, Any],
        cell_states: list[dict[str, Any]],
    ) -> str:
        sim_id = str(uuid4())
        record = {
            "id": sim_id,
            "region_id": str(region_id) if region_id else params.get("city"),
            "params": params,
            "horizon_months": horizon_months,
            "result_summary": result_summary,
            "cell_states": cell_states,
        }
        if self._client:
            await asyncio.to_thread(
                lambda: self._client.table("simulations").insert(record).execute()
            )
        else:
            self._saved.append(record)
        return sim_id

    async def seed_case_studies(self) -> None:
        """Upsert all local case studies to Supabase with embeddings."""
        if not self._client:
            return
        from app.config import settings
        for case in LOCAL_CASE_STUDIES:
            record = {
                "id": case.id,
                "title": case.title,
                "city": case.city,
                "year": case.year,
                "description": case.description,
                "outcome": case.outcome,
                "source": case.source,
                "tags": case.tags,
                "sectors": case.sectors,
                "policies": case.policies,
            }
            try:
                await asyncio.to_thread(
                    lambda r=record: self._client.table("case_studies").upsert(r).execute()
                )
            except Exception as e:
                logger.warning("Failed to seed case study %s: %s", case.id, e)

    async def search_case_studies(
        self,
        keywords: list[str] | str,
        city: str | None = None,
        sector: str | None = None,
        policy: str | None = None,
        top_k: int = 5,
    ) -> list[CaseStudy]:
        if isinstance(keywords, str):
            words = set(keywords.lower().split())
        else:
            words = {str(word).lower() for word in keywords}
        if sector:
            words.add(sector.lower())
        if policy:
            words.add(policy.lower())

        scored: list[CaseStudy] = []
        for case in LOCAL_CASE_STUDIES:
            haystack = " ".join(
                [case.city, case.title, case.description, *case.tags, *case.sectors, *case.policies]
            ).lower()
            score = sum(1 for word in words if word and word.replace("_", " ") in haystack)
            if city and city.lower().replace("_", " ") in haystack:
                score += 3
            if score > 0:
                scored.append(case.model_copy(update={"relevance_score": float(score)}))
        return sorted(scored, key=lambda c: c.relevance_score, reverse=True)[:top_k]

    async def list_case_studies(
        self,
        city: str | None = None,
        sector: str | None = None,
        policy: str | None = None,
    ) -> list[dict[str, Any]]:
        studies = await self.search_case_studies([], city=city, sector=sector, policy=policy, top_k=50)
        if not city and not sector and not policy:
            studies = LOCAL_CASE_STUDIES
        return [study.model_dump() for study in studies]


def _known_challenges(city_type: str) -> list[str]:
    if "it" in city_type or "tech" in city_type:
        return ["traffic congestion", "housing affordability", "infrastructure stress"]
    if "port" in city_type:
        return ["logistics congestion", "flood exposure", "industrial land pressure"]
    if "manufacturing" in city_type or "pharma" in city_type:
        return ["industrial corridor pressure", "formal-informal job transition", "logistics demand"]
    return ["migration pressure", "basic services", "housing affordability"]


_db: DatabaseClient | None = None


async def get_db() -> DatabaseClient:
    global _db
    if _db is None:
        _db = DatabaseClient()
        await _db.connect()
    return _db
