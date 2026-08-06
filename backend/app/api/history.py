from fastapi import APIRouter

from app.core.dependencies import CurrentUserId, DatabaseSession
from app.repositories.workflow_executions import WorkflowExecutionRepository
from app.schemas.workflow_executions import WorkflowExecutionRead

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[WorkflowExecutionRead])
def list_history(user_id: CurrentUserId, db: DatabaseSession) -> list[WorkflowExecutionRead]:
    repository = WorkflowExecutionRepository(db)
    return [
        WorkflowExecutionRead.model_validate(execution)
        for execution in repository.list_for_user(user_id)
    ]
