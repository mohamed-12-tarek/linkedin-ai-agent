import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProviderType = Literal["groq", "gemini", "openrouter"]
RoleType = Literal["writer", "reviewer", "judge", "image", "translation"]


class ModelBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: ProviderType
    base_url: str | None = Field(default=None, max_length=2048)
    context_length: int | None = Field(default=None, gt=0)
    cost_per_1k: float | None = Field(default=0, ge=0)
    temperature: float | None = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    role_type: RoleType
    is_available: bool = True


class ModelCreate(ModelBase):
    api_key: str | None = Field(default=None, min_length=1)


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    provider: ProviderType | None = None
    api_key: str | None = Field(default=None, min_length=1)
    clear_api_key: bool = False
    base_url: str | None = Field(default=None, max_length=2048)
    context_length: int | None = Field(default=None, gt=0)
    cost_per_1k: float | None = Field(default=None, ge=0)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    role_type: RoleType | None = None
    is_available: bool | None = None

    @model_validator(mode="after")
    def validate_api_key_action(self) -> "ModelUpdate":
        if self.api_key is not None and self.clear_api_key:
            raise ValueError("api_key and clear_api_key cannot be used together")
        return self


class ModelRead(ModelBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    has_api_key: bool
