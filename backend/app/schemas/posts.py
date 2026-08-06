import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PostGenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10_000)
    objective: str = Field(min_length=1, max_length=255)
    audience: str = Field(min_length=1, max_length=500)
    language: str = Field(default="English", min_length=1, max_length=100)
    tone: str = Field(default="professional", min_length=1, max_length=100)
    style_id: uuid.UUID | None = None
    length: Literal["short", "medium", "long"] = "medium"
    cta_type: str = Field(default="engagement", min_length=1, max_length=100)
    emoji_level: Literal["none", "low", "medium", "high"] = "low"
    hashtag_mode: Literal["none", "auto", "custom"] = "auto"
    image_mode: Literal["none", "upload", "ai"] = "none"
    image_upload_id: str | None = Field(default=None, pattern="^[a-f0-9]{32}$")
    image_prompt: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def validate_image_mode(self) -> "PostGenerateRequest":
        if self.image_mode == "upload" and not self.image_upload_id:
            raise ValueError("image_upload_id is required when image_mode is upload")
        if self.image_mode != "upload" and self.image_upload_id:
            raise ValueError("image_upload_id is only valid when image_mode is upload")
        return self


class PostVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    content: str
    created_by_node: str
    created_at: datetime


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    style_id: uuid.UUID | None
    topic: str
    description: str
    objective: str
    audience: str
    language: str
    tone: str
    length: str
    cta_type: str
    emoji_level: str
    hashtag_mode: str
    content: str | None
    hook: str | None
    cta_text: str | None
    hashtags: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    versions: list[PostVersionRead] = []
