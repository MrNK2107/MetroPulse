from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db, DatabaseClient

router = APIRouter()


@router.get("/health/llm")
async def llm_health():
    """Check which LLM providers have API keys configured (no actual calls made)."""
    from app.config import settings

    providers = {
        "gemini": {
            "configured": bool(settings.gemini_api_key),
            "model": settings.resolved_llm_model if settings.llm_provider == "gemini" else "gemini-2.0-flash",
        },
        "openai": {
            "configured": bool(settings.openai_api_key),
            "model": settings.resolved_llm_model if settings.llm_provider == "openai" else "gpt-4o-mini",
        },
        "mimo": {
            "configured": bool(settings.mimo_api_key),
            "model": settings.resolved_llm_model if settings.llm_provider == "mimo" else "mimo-v2.5-pro",
            "base_url": settings.mimo_base_url,
        },
    }

    configured_count = sum(1 for p in providers.values() if p["configured"])
    active_provider = settings.llm_provider

    return {
        "success": True,
        "data": {
            "providers": providers,
            "active_provider": active_provider,
            "configured_count": configured_count,
            "status": "ready" if configured_count > 0 else "no_providers_configured",
        },
        "error": None,
        "meta": {},
    }


@router.get("/health")
async def health_check(db: DatabaseClient = Depends(get_db)):
    db_status = "connected" if db.is_connected() else "in_memory_fallback"
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
            "db_status": db_status,
        },
        "error": None,
        "meta": {},
    }


@router.get("/health/data")
async def data_health(city: str = "bengaluru", db: DatabaseClient = Depends(get_db)):
    sources = await db.list_data_sources(city=city)
    status = "healthy"
    if any(source["freshness"] in {"stale", "missing"} for source in sources):
        status = "degraded"
    if all(source["freshness"] in {"missing", "demo"} for source in sources):
        status = "demo"
    return {
        "success": True,
        "data": {
            "status": status,
            "city": city,
            "sources": sources,
        },
        "error": None,
        "meta": {},
    }
