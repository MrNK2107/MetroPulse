import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import get_db
from app.logging_setup import setup_logging
from app.middleware import CorrelationIdMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from app.routes.health import router as health_router
from app.routes.regions import router as regions_router
from app.routes.case_studies import router as case_studies_router
from app.routes.realtime import router as realtime_router
from app.routes.twin import install_error_handlers as install_twin_error_handlers
from app.routes.twin import router as twin_router
from app.ws.agent import router as agent_ws_router

logger = logging.getLogger(__name__)

# JSON request logs at LOG_LEVEL, and token / search-text redaction on uvicorn's
# loggers. Runs at import, i.e. when uvicorn loads the app, after uvicorn has
# configured its own loggers.
setup_logging(settings.log_level)


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
        if not cities:
            await asyncio.sleep(900)
            continue
        city = cities[city_idx % len(cities)]
        city_idx += 1
        try:
            await run_ingestion_cycle(db, city)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Scheduled ingestion failed for %s: %s", city, e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.realtime import get_http_client
    db = await get_db()
    if settings.seed_case_studies_on_startup:
        try:
            await db.seed_case_studies()
        except Exception as e:
            logger.warning("Case study seeding failed: %s", e)

    # Warm up the shared HTTP client for all connectors
    await get_http_client()

    ingestion_task = asyncio.create_task(_ingestion_loop(db))

    yield

    ingestion_task.cancel()
    try:
        await ingestion_task
    except asyncio.CancelledError:
        pass

    from app.realtime import close_http_client
    await close_http_client()


app = FastAPI(
    title="MetroPulse API",
    version="2.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Service, data and LLM-provider health checks"},
        {"name": "regions", "description": "City configs and baselines"},
        {"name": "case-studies", "description": "Case-study search used by the agent's evidence tools"},
        {"name": "realtime-data", "description": "Live data sources, snapshots and token-gated ingestion"},
        {"name": "twin", "description": "India twin: districts, places and city boundaries"},
        {"name": "agent", "description": "Token-gated agent socket and its status probe"},
    ],
)

# Starlette runs the last-added middleware first: CORS -> correlation id -> logging -> rate limit.
app.add_middleware(RateLimitMiddleware, limit=settings.rate_limit_per_minute)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
# CORS is added last so it is outermost and a 429 still carries CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Ingest-Token", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.include_router(health_router, tags=["health"])
app.include_router(regions_router, prefix="/api", tags=["regions"])
app.include_router(case_studies_router, prefix="/api", tags=["case-studies"])
app.include_router(realtime_router, prefix="/api", tags=["realtime-data"])
app.include_router(twin_router, prefix="/api/twin", tags=["twin"])
install_twin_error_handlers(app)
# /ws/agent is token-gated (AGENT_WS_TOKEN; disabled when unset) and capped at
# WS_MAX_CONNECTIONS concurrent sessions. See app/ws/agent.py.
app.include_router(agent_ws_router, tags=["agent"])
