from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import get_db
from app.routes.health import router as health_router
from app.routes.regions import router as regions_router
from app.routes.simulations import router as simulations_router
from app.routes.case_studies import router as case_studies_router
from app.ws.simulation import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_db()
    yield


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
app.include_router(ws_router, tags=["websocket"])
