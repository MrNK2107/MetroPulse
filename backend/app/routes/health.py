from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health_check():
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
        },
        "error": None,
        "meta": {},
    }
