from fastapi import APIRouter

from app.api.history import router as history_router
from app.api.models import router as models_router
from app.api.posts import router as posts_router
from app.api.telegram import router as telegram_router

api_router = APIRouter()
api_router.include_router(models_router)
api_router.include_router(posts_router)
api_router.include_router(telegram_router)
api_router.include_router(history_router)


@api_router.get("/", tags=["system"])
async def api_root() -> dict[str, str]:
    return {"name": "AI LinkedIn Content Agent API", "status": "ready"}
