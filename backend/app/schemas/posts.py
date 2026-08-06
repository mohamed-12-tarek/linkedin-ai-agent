import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
