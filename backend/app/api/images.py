import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.dependencies import Container, CurrentUserId, DatabaseSession
from app.models import Image, Post
from app.schemas.images import ImageRead, ImageUploadRead

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/upload", response_model=ImageUploadRead, status_code=status.HTTP_201_CREATED)
def upload_image(
    user_id: CurrentUserId,
    container: Container,
    file: Annotated[UploadFile, File()],
) -> ImageUploadRead:
    content_type = file.content_type or "application/octet-stream"
    content = file.file.read(container.image_storage.maximum_bytes + 1)
    try:
        upload_id = container.image_storage.stage_upload(content, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ImageUploadRead(upload_id=upload_id)


@router.get("/post/{post_id}", response_model=list[ImageRead])
def list_post_images(
    post_id: uuid.UUID,
    user_id: CurrentUserId,
    db: DatabaseSession,
) -> list[ImageRead]:
    post_exists = db.scalar(select(Post.id).where(Post.id == post_id, Post.user_id == user_id))
    if post_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    images = db.scalars(
        select(Image).where(Image.post_id == post_id).order_by(Image.created_at.desc())
    )
    return [ImageRead.model_validate(image) for image in images]
