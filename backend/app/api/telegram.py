from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from app.core.dependencies import Container, DatabaseSession
from app.integrations.telegram import TelegramClient
from app.repositories.model_registry import ModelRegistryRepository
from app.repositories.posts import PostRepository
from app.repositories.workflow_executions import WorkflowExecutionRepository
from app.schemas.telegram import TelegramUpdate
from app.services.model_registry import ModelRegistryService
from app.services.workflow_approvals import (
    TelegramChatMismatchError,
    WorkflowApprovalService,
    WorkflowExecutionNotFoundError,
)
from app.workflows.post_generation.workflow import build_post_generation_workflow

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
def telegram_webhook(
    update: TelegramUpdate,
    db: DatabaseSession,
    container: Container,
    x_telegram_bot_api_secret_token: Annotated[
        str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")
    ] = None,
) -> dict[str, bool]:
    expected = container.settings.telegram_webhook_secret
    if expected and x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")
    callback = update.callback_query
    if callback is None:
        return {"ok": True}
    telegram = TelegramClient(container.settings)
    try:
        execution_id, action = telegram.parse_callback_data(callback.data)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid callback"
        ) from exc
    from app.integrations.llm import LangChainChatModelFactory

    registry = ModelRegistryService(ModelRegistryRepository(db), container.encryption)
    model_factory = LangChainChatModelFactory(registry, container.settings)
    workflow = build_post_generation_workflow(
        container.prompt_engine, checkpointer=container.checkpoint_store.saver
    )
    service = WorkflowApprovalService(
        WorkflowExecutionRepository(db),
        PostRepository(db),
        workflow,
        model_factory,
        container.prompt_engine,
        telegram,
        container.settings.telegram_chat_id,
    )
    try:
        execution = service.resume(
            execution_id,
            action,
            external_event_id=str(update.update_id),
            payload=update.model_dump(mode="json"),
            actor_chat_id=(
                str(callback.message.chat.get("id")) if callback.message is not None else None
            ),
        )
    except TelegramChatMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chat mismatch") from exc
    except WorkflowExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
        ) from exc
    telegram.answer_callback(callback.id, f"Action processed: {action}")
    return {"ok": execution is not None}
