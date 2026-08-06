from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid_column() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_column()
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    telegram_chat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = created_at_column()

    prompts: Mapped[list[Prompt]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    styles: Mapped[list[Style]] = relationship(back_populates="user", cascade="all, delete-orphan")
    posts: Mapped[list[Post]] = relationship(back_populates="user", cascade="all, delete-orphan")
    cv_documents: Mapped[list[CVDocument]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    linkedin_accounts: Mapped[list[LinkedInAccount]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    job_matches: Mapped[list[JobMatch]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profile_optimizations: Mapped[list[ProfileOptimization]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    llm_models: Mapped[list[LLMModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped[UserSettings | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class LLMModel(Base):
    __tablename__ = "llm_models"

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    api_key_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    context_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_per_1k: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role_type: Mapped[str] = mapped_column(String)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    user: Mapped[User] = relationship(back_populates="llm_models")


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    agent_type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()
    user: Mapped[User] = relationship(back_populates="prompts")


class Style(Base):
    __tablename__ = "styles"

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    instructions: Mapped[str] = mapped_column(Text)
    example_posts: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()
    user: Mapped[User] = relationship(back_populates="styles")
    posts: Mapped[list[Post]] = relationship(back_populates="style")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    style_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("styles.id"), nullable=True)
    topic: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(String)
    audience: Mapped[str] = mapped_column(String)
    language: Mapped[str] = mapped_column(String)
    tone: Mapped[str] = mapped_column(String)
    length: Mapped[str] = mapped_column(String)
    cta_type: Mapped[str] = mapped_column(String)
    emoji_level: Mapped[str] = mapped_column(String)
    hashtag_mode: Mapped[str] = mapped_column(String)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    user: Mapped[User] = relationship(back_populates="posts")
    style: Mapped[Style | None] = relationship(back_populates="posts")
    versions: Mapped[list[PostVersion]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    images: Mapped[list[Image]] = relationship(back_populates="post", cascade="all, delete-orphan")
    telegram_messages: Mapped[list[TelegramMessage]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    schedule: Mapped[Schedule | None] = relationship(
        back_populates="post", uselist=False, cascade="all, delete-orphan"
    )
    publish_history: Mapped[list[PublishHistory]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class PostVersion(Base):
    __tablename__ = "post_versions"
    id: Mapped[uuid.UUID] = uuid_column()
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    created_by_node: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
    post: Mapped[Post] = relationship(back_populates="versions")


class Image(Base):
    __tablename__ = "images"
    id: Mapped[uuid.UUID] = uuid_column()
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"))
    source: Mapped[str] = mapped_column(String)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()
    post: Mapped[Post] = relationship(back_populates="images")


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    id: Mapped[uuid.UUID] = uuid_column()
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"))
    telegram_message_id: Mapped[str] = mapped_column(String)
    action_taken: Mapped[str | None] = mapped_column(String, nullable=True)
    sent_at: Mapped[datetime] = created_at_column()
    action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    post: Mapped[Post] = relationship(back_populates="telegram_messages")


class Schedule(Base):
    __tablename__ = "schedules"
    id: Mapped[uuid.UUID] = uuid_column()
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"), unique=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recurrence: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    post: Mapped[Post] = relationship(back_populates="schedule")


class LinkedInAccount(Base):
    __tablename__ = "linkedin_accounts"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    access_token_encrypted: Mapped[str] = mapped_column(String)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile_urn: Mapped[str | None] = mapped_column(String, nullable=True)
    user: Mapped[User] = relationship(back_populates="linkedin_accounts")


class PublishHistory(Base):
    __tablename__ = "publish_history"
    id: Mapped[uuid.UUID] = uuid_column()
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"))
    linkedin_post_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    published_at: Mapped[datetime] = created_at_column()
    post: Mapped[Post] = relationship(back_populates="publish_history")


class ProfileOptimization(Base):
    __tablename__ = "profile_optimizations"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    profile_snapshot: Mapped[str] = mapped_column(Text)
    suggestions: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
    user: Mapped[User] = relationship(back_populates="profile_optimizations")


class CVDocument(Base):
    __tablename__ = "cv_documents"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    file_path: Mapped[str] = mapped_column(String)
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    uploaded_at: Mapped[datetime] = created_at_column()
    user: Mapped[User] = relationship(back_populates="cv_documents")
    job_matches: Mapped[list[JobMatch]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )


class JobListing(Base):
    __tablename__ = "job_listings"
    id: Mapped[uuid.UUID] = uuid_column()
    source: Mapped[str] = mapped_column(String)
    external_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = created_at_column()
    job_matches: Mapped[list[JobMatch]] = relationship(
        back_populates="job_listing", cascade="all, delete-orphan"
    )


class JobMatch(Base):
    __tablename__ = "job_matches"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    cv_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cv_documents.id"))
    job_listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_listings.id"))
    match_score: Mapped[float] = mapped_column(Float)
    match_reasoning: Mapped[str] = mapped_column(Text)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()
    user: Mapped[User] = relationship(back_populates="job_matches")
    cv: Mapped[CVDocument] = relationship(back_populates="job_matches")
    job_listing: Mapped[JobListing] = relationship(back_populates="job_matches")


class UserSettings(Base):
    __tablename__ = "settings"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    default_language: Mapped[str | None] = mapped_column(String, nullable=True)
    default_tone: Mapped[str | None] = mapped_column(String, nullable=True)
    default_style_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("styles.id"), nullable=True
    )
    default_models_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduling_settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_matching_settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    user: Mapped[User] = relationship(back_populates="settings")
    default_style: Mapped[Style | None] = relationship(foreign_keys=[default_style_id])
