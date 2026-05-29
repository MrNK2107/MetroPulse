import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import get_db
from app.routes.health import router as health_router
from app.routes.regions import router as regions_router
from app.routes.simulations import router as simulations_router
from app.routes.case_studies import router as case_studies_router
from app.routes.realtime import router as realtime_router
from app.ws.simulation import router as ws_router

logger = logging.getLogger(__name__)


def _all_city_ids() -> list[str]:
    """Get all available city IDs from YAML configs."""
    from engine.config import list_available_cities
    return [c["id"] for c in list_available_cities()]


async def _ingestion_loop(db: object) -> None:
    """Background loop that periodically ingests data for ALL cities."""
    from app.realtime import run_ingestion_cycle

    cities = _all_city_ids()

    # Run once at startup for all cities (staggered)
    for city in cities:
        try:
            await run_ingestion_cycle(db, city)
        except Exception as e:
            logger.warning("Initial ingestion failed for %s: %s", city, e)
        await asyncio.sleep(2)  # stagger to avoid hammering APIs

    # Then run on a cycle: ingest one city every news_refresh_seconds / num_cities
    city_idx = 0
    while True:
        await asyncio.sleep(settings.news_refresh_seconds)
        try:
            city = cities[city_idx % len(cities)]
            await run_ingestion_cycle(db, city)
            city_idx += 1
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Scheduled ingestion failed for %s: %s", cities[city_idx % len(cities)], e)
            city_idx += 1


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await get_db()
    if settings.seed_case_studies_on_startup:
        try:
            await db.seed_case_studies()
        except Exception:
            pass  # non-fatal: keyword fallback still works

    ingestion_task = asyncio.create_task(_ingestion_loop(db))

    yield

    ingestion_task.cancel()
    try:
        await ingestion_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="MetroPulse API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(regions_router, prefix="/api", tags=["regions"])
app.include_router(simulations_router, prefix="/api", tags=["simulations"])
app.include_router(case_studies_router, prefix="/api", tags=["case-studies"])
app.include_router(realtime_router, prefix="/api", tags=["realtime-data"])
app.include_router(ws_router, tags=["websocket"])
