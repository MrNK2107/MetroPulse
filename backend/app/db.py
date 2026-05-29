from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4, uuid5

from app.realtime import build_demo_manifest, snapshot_quality
from app.realtime_models import SnapshotData, SnapshotQuality, SourceStatus
from engine.config import CityConfig, list_available_cities
from engine.models import CaseRetrievalAudit, CaseStudy, CaseStudyMatchContext, CityProfile, ParsedScenario

logger = logging.getLogger(__name__)

CASE_STUDY_NAMESPACE = UUID("2d9a2fb0-1442-4d70-a455-03d4f6f9a637")
CASE_STUDY_EMBEDDING_DIMENSIONS = 1536


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
            return _valid_embedding(response.data[0].embedding, provider, model)

        if provider == "gemini" and settings.gemini_api_key:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.embed_content,
                    model=model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=CASE_STUDY_EMBEDDING_DIMENSIONS
                    ),
                ),
                timeout=10.0,
            )
            return _valid_embedding(response.embeddings[0].values, provider, model)

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
                return _valid_embedding(resp.json()["embedding"], provider, model)

    except Exception as e:
        logger.warning("Embedding generation failed (%s): %s", provider, e)

    return None


def _case_study_db_id(slug: str) -> str:
    """Map stable app slugs onto the UUID primary key used by Supabase."""
    return str(uuid5(CASE_STUDY_NAMESPACE, slug))


def _valid_embedding(
    embedding: list[float] | tuple[float, ...],
    provider: str,
    model: str,
) -> list[float] | None:
    values = list(embedding)
    if len(values) != CASE_STUDY_EMBEDDING_DIMENSIONS:
        logger.warning(
            "Embedding from %s/%s has %d dimensions; expected %d. Skipping vector.",
            provider,
            model,
            len(values),
            CASE_STUDY_EMBEDDING_DIMENSIONS,
        )
        return None
    return values

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
        self._snapshots: dict[str, SnapshotData] = {}
        self._client: Any = None
        self.last_case_retrieval = CaseRetrievalAudit()

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

    async def list_data_sources(self, city: str = "bengaluru") -> list[dict[str, Any]]:
        snapshot = await self.get_latest_snapshot(city)
        quality = snapshot_quality(snapshot)
        return [source.model_dump(mode="json") for source in quality.source_manifest.values()]

    async def get_latest_snapshot(self, city: str = "bengaluru") -> SnapshotData | None:
        city_key = city.lower().replace(" ", "_")
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("city_snapshots")
                    .select("*")
                    .eq("city", city_key)
                    .order("snapshot_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    return _snapshot_from_row(result.data[0])
            except Exception as e:
                logger.warning("Latest city snapshot lookup failed, using local fallback: %s", e)
        return self._snapshots.get(city_key)

    async def get_snapshot_quality(self, snapshot_id: str, city: str = "bengaluru") -> SnapshotQuality:
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("city_snapshots")
                    .select("*")
                    .eq("id", snapshot_id)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    return snapshot_quality(_snapshot_from_row(result.data[0]))
            except Exception as e:
                logger.warning("Snapshot quality lookup failed, using local fallback: %s", e)
        snapshot = self._snapshots.get(city.lower().replace(" ", "_"))
        if snapshot and snapshot.id == snapshot_id:
            return snapshot_quality(snapshot)
        return snapshot_quality(None)

    async def save_raw_observation(
        self,
        source_id: str,
        city: str,
        payload: dict[str, Any],
        observed_at: datetime | None = None,
        status: str = "ok",
        source_domain: str = "news",
    ) -> None:
        from app.realtime import payload_hash

        resolved_source_id = await self._resolve_data_source_id(source_id, source_domain)

        record = {
            "source_id": resolved_source_id,
            "city": city.lower().replace(" ", "_"),
            "observed_at": (observed_at or datetime.now(timezone.utc)).isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "payload_hash": payload_hash(payload),
            "status": status,
        }
        if self._client:
            try:
                await asyncio.to_thread(
                    lambda: self._client.table("raw_observations").insert(record).execute()
                )
            except Exception as e:
                logger.warning("Supabase save_raw_observation failed (table may not exist): %s", e)

    async def _resolve_data_source_id(self, source_name_or_id: str, domain: str) -> str:
        if not self._client:
            return source_name_or_id
        try:
            result = await asyncio.to_thread(
                lambda: self._client.table("data_sources")
                .select("id")
                .eq("name", source_name_or_id)
                .eq("domain", domain)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]["id"]

            record = {
                "name": source_name_or_id,
                "domain": domain,
                "auth_type": "none",
                "update_cadence_sec": 86_400,
                "enabled": True,
            }
            created = await asyncio.to_thread(
                lambda: self._client.table("data_sources")
                .insert(record)
                .execute()
            )
            if created.data:
                logger.info("Created data source row for %s/%s", domain, source_name_or_id)
                return created.data[0]["id"]
        except Exception as e:
            logger.warning("Could not resolve data source %s/%s: %s", domain, source_name_or_id, e)
        return source_name_or_id

    async def save_city_snapshot(self, snapshot: SnapshotData) -> None:
        self._snapshots[snapshot.city] = snapshot
        if self._client:
            record = {
                "id": snapshot.id,
                "city": snapshot.city,
                "snapshot_at": snapshot.snapshot_at.isoformat(),
                "h3_cells": snapshot.h3_cells,
                "aggregate_metrics": snapshot.aggregate_metrics,
                "source_manifest": snapshot.manifest_for_json(),
                "quality_score": snapshot.quality_score,
                "status": snapshot.status,
            }
            try:
                await asyncio.to_thread(
                    lambda: self._client.table("city_snapshots").upsert(record).execute()
                )
            except Exception as e:
                logger.warning(
                    "Supabase save_city_snapshot failed (table may not exist), using in-memory only: %s", e
                )

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
        embedding_available = True
        for case in LOCAL_CASE_STUDIES:
            record = {
                "id": _case_study_db_id(case.id),
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
            if embedding_available:
                embed_text = f"{case.title} {case.description} {' '.join(case.tags)} {' '.join(case.sectors)} {' '.join(case.policies)}"
                embedding = await self._generate_embedding(embed_text)
                if embedding:
                    record["embedding"] = embedding
                else:
                    embedding_available = False
                    logger.info("Case study embeddings unavailable; seeding remaining rows without vectors")
            try:
                await asyncio.to_thread(
                    lambda r=record: self._client.table("case_studies").upsert(r).execute()
                )
            except Exception as e:
                logger.warning("Failed to seed case study %s: %s", case.id, e)

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for text using configured provider."""
        return await generate_embedding(text)

    async def search_case_studies(
        self,
        keywords: list[str] | str,
        city: str | None = None,
        sector: str | None = None,
        policy: str | None = None,
        top_k: int = 5,
        context: CaseStudyMatchContext | None = None,
    ) -> list[CaseStudy]:
        context = context or build_case_study_context(
            city=city,
            sectors=[sector] if sector else [],
            policies=[policy] if policy else [],
            keywords=keywords,
        )
        words = {_normal_token(word) for word in context.keywords if _normal_token(word)}

        # Try pgvector semantic search if Supabase is available
        if self._client and words:
            query_text = " ".join(words)
            embedding = await self._generate_embedding(query_text)
            if embedding:
                try:
                    match_count = max(top_k * 4, 20)
                    rpc_args = {
                        "query_embedding": embedding,
                        "match_count": match_count,
                        "filter_city": _city_lookup_value(context.city),
                        "filter_sectors": context.sectors or None,
                        "filter_policies": context.policies or None,
                    }
                    result = await asyncio.to_thread(
                        lambda emb=embedding: self._client.rpc(
                            "match_case_studies",
                            rpc_args,
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
                        ranked = self._rank_case_studies(studies, context, top_k)
                        if ranked:
                            return ranked
                except Exception as e:
                    logger.warning("pgvector search failed, falling back to keyword: %s", e)

        return self._rank_case_studies(LOCAL_CASE_STUDIES, context, top_k)

    def _rank_case_studies(
        self,
        studies: list[CaseStudy],
        context: CaseStudyMatchContext,
        top_k: int,
    ) -> list[CaseStudy]:
        ranked: list[CaseStudy] = []
        weak_count = 0
        for case in studies:
            matched = _score_case_study(case, context)
            if matched.relevance_tier == "weak":
                weak_count += 1
                continue
            ranked.append(matched)

        ranked.sort(
            key=lambda c: (
                0 if c.relevance_tier == "exact" else 1,
                -c.relevance_score,
                c.city,
                c.title,
            )
        )
        result = ranked[:top_k]
        self.last_case_retrieval = CaseRetrievalAudit(
            query_city=context.city,
            query_sectors=context.sectors,
            query_policies=context.policies,
            returned_count=len(result),
            omitted_weak_count=weak_count,
            retrieval_mode="strict",
        )
        return result

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


def build_case_study_context(
    parsed: ParsedScenario | None = None,
    original_query: str = "",
    city: str | None = None,
    sectors: list[str] | None = None,
    policies: list[str] | None = None,
    keywords: list[str] | str | None = None,
) -> CaseStudyMatchContext:
    if parsed:
        city = parsed.city
        sectors = [
            sector
            for sector, delta in sorted(
                parsed.sector_deltas.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )
            if abs(delta) > 0
        ]
        policies = list(parsed.policies_active)
        base_keywords: list[str] = list(parsed.keywords)
        sector_directions = {
            sector: "positive" if delta > 0 else "negative" if delta < 0 else "mixed"
            for sector, delta in parsed.sector_deltas.items()
            if abs(delta) > 0
        }
    else:
        base_keywords = []
        sector_directions = {}

    if isinstance(keywords, str):
        base_keywords.extend(keywords.split())
    elif keywords:
        base_keywords.extend(str(word) for word in keywords)
    if original_query:
        base_keywords.extend(original_query.split())
    if city:
        base_keywords.append(city)
    base_keywords.extend(sectors or [])
    base_keywords.extend(policies or [])

    return CaseStudyMatchContext(
        city=city,
        sectors=_unique([_normal_sector(sector) for sector in (sectors or []) if sector]),
        policies=_unique([policy for policy in (policies or []) if policy]),
        keywords=_unique([word for word in base_keywords if word]),
        sector_directions=sector_directions,
    )


def _score_case_study(case: CaseStudy, context: CaseStudyMatchContext) -> CaseStudy:
    query_city = _normal_city(context.city)
    case_city = _normal_city(case.city)
    matched_city = bool(query_city and (query_city == case_city or query_city in case_city or case_city in query_city))
    query_sectors = {_normal_sector(sector) for sector in context.sectors}
    case_sectors = {_normal_sector(sector) for sector in case.sectors}
    query_policies = {_normal_policy(policy) for policy in context.policies}
    case_policies = {_normal_policy(policy) for policy in case.policies}
    matched_sectors = sorted(query_sectors & case_sectors)
    matched_policies = [
        policy
        for policy in case.policies
        if _normal_policy(policy) in query_policies
    ]
    haystack = " ".join([case.city, case.title, case.description, *case.tags, *case.sectors, *case.policies]).lower()
    keyword_hits = {
        token
        for token in (_normal_token(word) for word in context.keywords)
        if len(token) > 2 and token.replace("_", " ") in haystack
    }

    has_topic_filter = bool(query_sectors or query_policies)
    has_topic_match = bool(matched_sectors or matched_policies)
    primary_sectors = set(context.sectors[:1])
    tier: str = "weak"
    reasons: list[str] = []
    score = 0.0

    if matched_city:
        reasons.append("Same city")
    for sector in matched_sectors:
        reasons.append(_sector_label(sector))
    reasons.extend(matched_policies)

    if has_topic_filter:
        if matched_city and has_topic_match:
            tier = "exact"
            score = 100.0
        elif matched_policies or (set(matched_sectors) & primary_sectors):
            tier = "related"
            score = 55.0
        elif matched_city and len(keyword_hits) >= 2:
            tier = "related"
            score = 45.0
    elif matched_city:
        tier = "exact"
        score = 70.0

    if tier != "weak":
        score += len(matched_sectors) * 12.0
        score += len(matched_policies) * 16.0
        score += min(len(keyword_hits), 6) * 2.0
        if case.relevance_score:
            score += min(float(case.relevance_score), 1.0) * 5.0

    return case.model_copy(update={
        "relevance_score": score,
        "match_reasons": _unique(reasons),
        "relevance_tier": tier,
        "matched_city": matched_city,
        "matched_sectors": matched_sectors,
        "matched_policies": matched_policies,
    })


def _normal_city(value: str | None) -> str:
    if not value:
        return ""
    return value.lower().replace(" ", "_").replace("-", "_")


def _city_lookup_value(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("_", " ")


def _normal_sector(value: str) -> str:
    return value.lower().replace(" ", "_").replace("&", "and")


def _normal_policy(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _normal_token(value: str) -> str:
    return value.lower().strip(".,:;!?()[]{}'\"")


def _sector_label(value: str) -> str:
    return value.replace("_", " ").title().replace("It Ites", "IT/ITES")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _snapshot_from_row(row: dict[str, Any]) -> SnapshotData:
    manifest: dict[str, SourceStatus] = {}
    raw_manifest = row.get("source_manifest") or {}
    if isinstance(raw_manifest, dict):
        for domain, payload in raw_manifest.items():
            if isinstance(payload, dict):
                try:
                    manifest[domain] = SourceStatus(**payload)
                except Exception:
                    continue
    if not manifest:
        manifest = build_demo_manifest()
    snapshot_at = _parse_dt(row.get("snapshot_at")) or datetime.now(timezone.utc)
    h3_cells = row.get("h3_cells") or {}
    if isinstance(h3_cells, list):
        h3_cells = {
            str(cell.get("h3Index") or cell.get("h3_index")): cell
            for cell in h3_cells
            if isinstance(cell, dict) and (cell.get("h3Index") or cell.get("h3_index"))
        }
    return SnapshotData(
        id=str(row.get("id") or uuid4()),
        city=str(row.get("city") or "bengaluru"),
        snapshot_at=snapshot_at,
        status=row.get("status") or ("degraded" if row.get("quality_score", 0) < 0.8 else "fresh"),
        quality_score=float(row.get("quality_score") or 0.0),
        source_manifest=manifest,
        h3_cells=h3_cells if isinstance(h3_cells, dict) else {},
        aggregate_metrics=row.get("aggregate_metrics") or {},
    )


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
