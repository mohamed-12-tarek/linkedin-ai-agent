
from fastapi import APIRouter

from app.core.dependencies import CurrentUserId, DatabaseSession
from app.repositories.publishing import PublishingRepository
from app.schemas.publishing import PublishHistoryRead

router = APIRouter(prefix="/publishing", tags=["publishing"])


@router.get("/history", response_model=list[PublishHistoryRead])
def publishing_history(user_id: CurrentUserId, db: DatabaseSession) -> list[PublishHistoryRead]:
    return [
        PublishHistoryRead.model_validate(history)
        for history in PublishingRepository(db).list_history(user_id)
    ]
