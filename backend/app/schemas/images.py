import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImageUploadRead(BaseModel):
    upload_id: str


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID
    source: str
    prompt_used: str | None
    model_used: str | None
    url: str
    is_selected: bool
    content_type: str | None
    width: int | None
    height: int | None
    review_status: str | None
    created_at: datetime
