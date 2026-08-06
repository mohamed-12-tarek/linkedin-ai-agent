from fastapi import APIRouter

from app.api.models import router as models_router

api_router = APIRouter()
api_router.include_router(models_router)


@api_router.get("/", tags=["system"])
async def api_root() -> dict[str, str]:
    return {"name": "AI LinkedIn Content Agent API", "status": "ready"}
