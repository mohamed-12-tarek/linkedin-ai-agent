import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import Container, CurrentUserId, DatabaseSession
from app.integrations.telegram import TelegramClient
from app.repositories.model_registry import ModelRegistryRepository
from app.repositories.posts import PostRepository
from app.repositories.workflow_executions import WorkflowExecutionRepository
from app.schemas.posts import PostGenerateRequest, PostRead
from app.services.model_registry import ModelRegistryService
from app.services.posts import (
    PostGenerationService,
    PostNotFoundError,
    StyleNotFoundError,
)
from app.services.workflow_approvals import WorkflowApprovalService
from app.workflows.post_generation.workflow import build_post_generation_workflow
from app.workflows.registry import RegistryError

router = APIRouter(prefix="/posts", tags=["posts"])


def get_post_service(db: DatabaseSession, container: Container) -> PostGenerationService:
    from app.integrations.llm import LangChainChatModelFactory

    registry_service = ModelRegistryService(ModelRegistryRepository(db), container.encryption)
    model_factory = LangChainChatModelFactory(registry_service, container.settings)
    try:
        workflow = container.graph_registry.get("post_generation", "1.0.0")
    except RegistryError:
        workflow = build_post_generation_workflow(
            container.prompt_engine,
            checkpointer=container.checkpoint_store.saver,
            image_providers=container.image_providers,
            image_storage=container.image_storage,
            image_provider_order=container.settings.image_provider_names,
        )
        try:
            container.graph_registry.register(workflow)
        except RegistryError:
            workflow = container.graph_registry.get("post_generation", "1.0.0")
    post_repository = PostRepository(db)
    approval_service = WorkflowApprovalService(
        WorkflowExecutionRepository(db),
        post_repository,
        workflow,
        model_factory,
        container.prompt_engine,
        TelegramClient(container.settings),
        container.settings.telegram_chat_id,
        container.image_storage,
    )
    return PostGenerationService(
        post_repository,
        workflow,
        model_factory,
        container.prompt_engine,
        approval_service,
    )


PostService = Annotated[PostGenerationService, Depends(get_post_service)]


@router.post("/generate", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def generate_post(
    data: PostGenerateRequest,
    user_id: CurrentUserId,
    service: PostService,
) -> PostRead:
    try:
        return service.generate(user_id, data)
    except StyleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Style not found"
        ) from exc


@router.get("", response_model=list[PostRead])
def list_posts(user_id: CurrentUserId, service: PostService) -> list[PostRead]:
    return service.list_posts(user_id)


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: uuid.UUID, user_id: CurrentUserId, service: PostService) -> PostRead:
    try:
        return service.get_post(user_id, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found") from exc


def _run_regeneration(action, user_id: uuid.UUID, post_id: uuid.UUID) -> PostRead:
    try:
        return action(user_id, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found") from exc


@router.post("/{post_id}/rewrite", response_model=PostRead)
def rewrite_post(post_id: uuid.UUID, user_id: CurrentUserId, service: PostService) -> PostRead:
    return _run_regeneration(service.rewrite, user_id, post_id)


@router.post("/{post_id}/regenerate-hook", response_model=PostRead)
def regenerate_hook(
    post_id: uuid.UUID,
    user_id: CurrentUserId,
    service: PostService,
) -> PostRead:
    return _run_regeneration(service.regenerate_hook, user_id, post_id)


@router.post("/{post_id}/regenerate-cta", response_model=PostRead)
def regenerate_cta(
    post_id: uuid.UUID,
    user_id: CurrentUserId,
    service: PostService,
) -> PostRead:
    return _run_regeneration(service.regenerate_cta, user_id, post_id)


@router.post("/{post_id}/approve", response_model=PostRead)
def approve_post(post_id: uuid.UUID, user_id: CurrentUserId, service: PostService) -> PostRead:
    return _run_regeneration(
        lambda current_user_id, current_post_id: service.resume_action(
            current_user_id,
            current_post_id,
            "approve",
            f"api:{uuid.uuid4()}",
        ),
        user_id,
        post_id,
    )


@router.post("/{post_id}/reject", response_model=PostRead)
def reject_post(post_id: uuid.UUID, user_id: CurrentUserId, service: PostService) -> PostRead:
    return _run_regeneration(
        lambda current_user_id, current_post_id: service.resume_action(
            current_user_id,
            current_post_id,
            "reject",
            f"api:{uuid.uuid4()}",
        ),
        user_id,
        post_id,
    )
