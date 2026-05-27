from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID, uuid4

from engine.config import CityConfig, list_available_cities
from engine.models import CaseStudy, CityProfile

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> list[float] | None:
    """Generate an embedding vector for the given text using the configured provider."""
    from app.config import settings

    provider = settings.resolved_embedding_provider.lower()
    model = settings.resolved_embedding_model

    try:
        if provider == "openai" and settings.openai_api_key:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await asyncio.wait_for(
                client.embeddings.create(input=text, model=model),
                timeout=10.0,
            )
            return response.data[0].embedding

        if provider == "gemini" and settings.gemini_api_key:
            from google import genai

            client = genai.Client(api_key=settings.gemini_api_key)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.embed_content,
                    model=model,
                    contents=text,
                ),
                timeout=10.0,
            )
            return response.embeddings[0].values

        if provider == "ollama":
            import httpx

            base_url = settings.ollama_base_url or "http://localhost:11434"
            async with httpx.AsyncClient() as http:
                resp = await http.post(
                    f"{base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return resp.json()["embedding"]

    except Exception as e:
        logger.warning("Embedding generation failed (%s): %s", provider, e)

    return None

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
                from supabase.lib.client_options import SyncClientOptions
                import httpx

                # Pre-configure httpx client to avoid deprecated timeout/verify params
                http_client = httpx.Client(timeout=30.0, verify=True)
                options = SyncClientOptions(
                    postgrest_client_timeout=30.0,
                    httpx_client=http_client,
                )
                self._client = create_client(
                    settings.supabase_url,
                    settings.supabase_key,
                    options=options,
                )
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
        start = (page - 1) * per_page
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("simulations")
                    .select("id,region_id,params,horizon_months,result_summary,created_at")
                    .order("created_at", desc=True)
                    .range(start, start + per_page - 1)
                    .execute()
                )
                return result.data
            except Exception:
                logger.debug("Supabase list_simulations failed, using in-memory fallback")
        return self._saved[start : start + per_page]

    async def get_simulation(self, simulation_id: UUID) -> dict[str, Any] | None:
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("simulations")
                    .select("*")
                    .eq("id", str(simulation_id))
                    .limit(1)
                    .execute()
                )
                return result.data[0] if result.data else None
            except Exception:
                logger.debug("Supabase get_simulation failed, using in-memory fallback")
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
        # Skip if already seeded
        try:
            existing = await asyncio.to_thread(
                lambda: self._client.table("case_studies").select("id", count="exact").limit(1).execute()
            )
            if existing.count and existing.count > 0:
                logger.info("case_studies already seeded (%d rows), skipping", existing.count)
                return
        except Exception:
            pass
        logger.info("Seeding case_studies with embeddings...")
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
            # Generate embedding for semantic search
            embed_text = f"{case.title} {case.description} {' '.join(case.tags)} {' '.join(case.sectors)} {' '.join(case.policies)}"
            embedding = await self._generate_embedding(embed_text)
            if embedding:
                record["embedding"] = embedding
            try:
                await asyncio.to_thread(
                    lambda r=record: self._client.table("case_studies").upsert(r).execute()
                )
            except Exception as e:
                logger.warning("Failed to seed case study %s: %s", case.id, e)

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for text using configured provider."""
        try:
            from app.config import settings
            import httpx

            provider = (settings.embedding_provider or settings.llm_provider or "").lower()

            if provider == "openai" and settings.openai_api_key:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                        json={"input": text, "model": settings.embedding_model or "text-embedding-3-small"},
                    )
                    resp.raise_for_status()
                    return resp.json()["data"][0]["embedding"]

            if provider == "gemini" and settings.gemini_api_key:
                model = settings.embedding_model or "text-embedding-004"
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={settings.gemini_api_key}",
                        json={"model": f"models/{model}", "content": {"parts": [{"text": text}]}},
                    )
                    resp.raise_for_status()
                    return resp.json()["embedding"]["values"]

            # Ollama or fallback — skip embedding
            logger.info("No embedding provider configured, skipping vector search")
            return None
        except Exception as e:
            logger.warning("Embedding generation failed: %s", e)
            return None

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

        # Try pgvector semantic search if Supabase is available
        if self._client and words:
            query_text = " ".join(words)
            embedding = await self._generate_embedding(query_text)
            if embedding:
                try:
                    result = await asyncio.to_thread(
                        lambda emb=embedding: self._client.rpc(
                            "match_case_studies",
                            {"query_embedding": emb, "match_count": top_k},
                        ).execute()
                    )
                    if result.data:
                        studies = []
                        for row in result.data:
                            studies.append(CaseStudy(
                                id=row.get("id", ""),
                                title=row.get("title", ""),
                                city=row.get("city", ""),
                                year=row.get("year", 0),
                                description=row.get("description", ""),
                                outcome=row.get("outcome", ""),
                                source=row.get("source", ""),
                                tags=row.get("tags", []),
                                sectors=row.get("sectors", []),
                                policies=row.get("policies", []),
                                relevance_score=row.get("similarity", 0.0),
                            ))
                        # Apply city/sector/policy filters
                        if city:
                            city_lower = city.lower().replace("_", " ")
                            studies = [s for s in studies if city_lower in s.city.lower()]
                        if sector:
                            studies = [s for s in studies if sector.lower() in " ".join(s.sectors).lower()]
                        if policy:
                            studies = [s for s in studies if policy.lower() in " ".join(s.policies).lower()]
                        if studies:
                            return studies[:top_k]
                except Exception as e:
                    logger.warning("pgvector search failed, falling back to keyword: %s", e)

        # Keyword fallback
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
