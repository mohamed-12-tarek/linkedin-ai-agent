import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PublishHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID
    provider: str
    linkedin_post_id: str | None
    published_url: str | None
    status: str
    retry_count: int
    idempotency_key: str
    provider_metadata_json: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class LinkedInConnectionRead(BaseModel):
    connected: bool
    profile_urn: str | None = None
    expires_at: datetime | None = None
