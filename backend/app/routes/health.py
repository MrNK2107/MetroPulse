from fastapi import APIRouter, Depends

from app.db import get_db, DatabaseClient

router = APIRouter()


@router.get("/api/health/llm")
async def llm_health():
    """Report which LLM providers have credentials configured. Makes no LLM calls
    and never returns a key, only whether one is set."""
    from app.config import settings

    active = settings.llm_provider
    providers = {
        "gemini": {"configured": bool(settings.gemini_api_key)},
        "openai": {"configured": bool(settings.openai_api_key)},
        "mimo": {"configured": bool(settings.mimo_api_key)},
        # Ollama is local and keyless; "configured" means a base URL is set.
        "ollama": {"configured": bool(settings.ollama_base_url)},
    }
    providers[active] = {**providers.get(active, {"configured": False}), "model": settings.resolved_llm_model}
    configured_count = sum(1 for p in providers.values() if p["configured"])
    active_ready = providers.get(active, {}).get("configured", False)

    return {
        "success": True,
        "data": {
            "providers": providers,
            "active_provider": active,
            "configured_count": configured_count,
            "status": "ready" if active_ready else "no_providers_configured",
        },
        "error": None,
        "meta": {},
    }


@router.get("/api/health")
async def health_check(db: DatabaseClient = Depends(get_db)):
    db_status = "connected" if db.is_connected() else "in_memory_fallback"
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "2.0.0",
            "db_status": db_status,
        },
        "error": None,
        "meta": {},
    }


@router.get("/api/health/data")
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
