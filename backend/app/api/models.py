import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import Container, CurrentUserId, DatabaseSession
from app.repositories.model_registry import ModelRegistryRepository
from app.schemas.models import ModelCreate, ModelRead, ModelUpdate
from app.services.model_registry import ModelNotFoundError, ModelRegistryService

router = APIRouter(prefix="/models", tags=["models"])


def get_model_registry_service(
    db: DatabaseSession,
    container: Container,
) -> ModelRegistryService:
    return ModelRegistryService(ModelRegistryRepository(db), container.encryption)


ModelRegistry = Annotated[ModelRegistryService, Depends(get_model_registry_service)]


@router.get("", response_model=list[ModelRead])
def list_models(user_id: CurrentUserId, registry: ModelRegistry) -> list[ModelRead]:
    return registry.list_models(user_id)


@router.post("", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
def create_model(
    data: ModelCreate,
    user_id: CurrentUserId,
    registry: ModelRegistry,
) -> ModelRead:
    return registry.create_model(user_id, data)


@router.put("/{model_id}", response_model=ModelRead)
def update_model(
    model_id: uuid.UUID,
    data: ModelUpdate,
    user_id: CurrentUserId,
    registry: ModelRegistry,
) -> ModelRead:
    try:
        return registry.update_model(user_id, model_id, data)
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
        ) from exc


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: uuid.UUID,
    user_id: CurrentUserId,
    registry: ModelRegistry,
) -> Response:
    try:
        registry.delete_model(user_id, model_id)
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
