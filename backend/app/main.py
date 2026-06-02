import asyncio
import logging
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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
            if not cities:
                await asyncio.sleep(900)
                continue
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
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Service health and readiness checks"},
        {"name": "Regions", "description": "City region data and baselines"},
        {"name": "Simulation", "description": "Simulation run management and results"},
        {"name": "Case Studies", "description": "RAG case study search and retrieval"},
        {"name": "Realtime", "description": "Live data sources, snapshots, and ingestion"},
        {"name": "WebSocket", "description": "Real-time simulation streaming"},
    ],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured JSON logging for all requests except health checks."""

    async def dispatch(self, request: Request, call_next):
        # Skip logging for health check endpoints
        if request.url.path in ("/api/v1/health", "/api/v1/health/data", "/health"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        log_entry = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "response_time_ms": elapsed_ms,
        }
        logger.info(json.dumps(log_entry))

        # Add version header to response
        response.headers["X-API-Version"] = "1"
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(regions_router, prefix="/api/v1", tags=["Regions"])
app.include_router(simulations_router, prefix="/api/v1", tags=["Simulation"])
app.include_router(case_studies_router, prefix="/api/v1", tags=["Case Studies"])
app.include_router(realtime_router, prefix="/api/v1", tags=["Realtime"])
app.include_router(ws_router, tags=["WebSocket"])
