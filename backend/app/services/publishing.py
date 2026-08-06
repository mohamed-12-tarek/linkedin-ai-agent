import json
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import Settings
from app.core.security import EncryptionService
from app.integrations.publishers import PublisherRegistry, PublishRequest
from app.models import LinkedInAccount, PublishHistory
from app.repositories.publishing import PublishingRepository


class PublisherAccountRequiredError(Exception):
    pass


class PublishFailedError(Exception):
    pass


class PostNotPublishableError(Exception):
    pass


class PublisherService:
    def __init__(
        self,
        repository: PublishingRepository,
        registry: PublisherRegistry,
        encryption: EncryptionService,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.registry = registry
        self.encryption = encryption
        self.settings = settings

    def publish(
        self,
        user_id: uuid.UUID,
        post_id: uuid.UUID,
        provider_name: str = "linkedin",
        idempotency_key: str | None = None,
        dry_run: bool | None = None,
    ) -> PublishHistory:
        post = self.repository.get_post(user_id, post_id)
        if post is None or not post.content:
            raise PostNotPublishableError
        resolved_dry_run = self.settings.linkedin_dry_run if dry_run is None else dry_run
        mode = "dry-run" if resolved_dry_run else "live"
        key = idempotency_key or f"{provider_name}:{post_id}:{mode}"
        history = self.repository.get_history_by_key(key)
        if history is not None and history.status in {"published", "dry_run"}:
            return history
        account = self.repository.get_account(user_id)
        if not resolved_dry_run and account is None:
            raise PublisherAccountRequiredError
        if history is None:
            history = self.repository.add_history(
                PublishHistory(
                    post_id=post.id,
                    provider=provider_name,
                    status="pending",
                    idempotency_key=key,
                    retry_count=0,
                )
            )
            self.repository.session.commit()
        publisher = self.registry.get(provider_name)
        selected_image = next((image for image in post.images if image.is_selected), None)
        access_token = (
            self.encryption.decrypt(account.access_token_encrypted) if account is not None else ""
        )
        author_urn = (
            account.profile_urn if account and account.profile_urn else "urn:li:person:dry-run"
        )
        request = PublishRequest(
            idempotency_key=key,
            content=post.content,
            author_urn=author_urn,
            access_token=access_token,
            image_path=selected_image.url if selected_image else None,
            dry_run=resolved_dry_run,
        )
        history.status = "publishing"
        history.error_message = None
        self.repository.session.commit()
        max_attempts = max(1, self.settings.publisher_max_retries)
        previous_retries = history.retry_count
        for attempt in range(1, max_attempts + 1):
            try:
                result = publisher.publish(request)
                history.linkedin_post_id = result.external_id
                history.published_url = result.published_url
                history.status = "dry_run" if result.dry_run else "published"
                history.provider_metadata_json = json.dumps(result.metadata)
                history.retry_count = previous_retries + attempt - 1
                history.completed_at = datetime.now(UTC)
                history.published_at = history.completed_at
                post.status = history.status
                self.repository.session.commit()
                return history
            except Exception as exc:
                history.retry_count = previous_retries + attempt - 1
                history.error_message = str(exc)
                history.status = (
                    "retrying"
                    if self._is_retryable(exc) and attempt < max_attempts
                    else "failed"
                )
                self.repository.session.commit()
                if history.status == "failed":
                    raise PublishFailedError(str(exc)) from exc
                time.sleep(self.settings.publisher_retry_delay_seconds)
        raise PublishFailedError("Publisher exhausted retries")

    def save_linkedin_account(
        self, user_id: uuid.UUID, token_data: dict, profile_urn: str
    ) -> LinkedInAccount:
        account = self.repository.get_account(user_id)
        if account is None:
            account = LinkedInAccount(
                user_id=user_id,
                access_token_encrypted="",
            )
        account.access_token_encrypted = self.encryption.encrypt(token_data["access_token"])
        refresh_token = token_data.get("refresh_token")
        account.refresh_token_encrypted = (
            self.encryption.encrypt(refresh_token) if refresh_token else None
        )
        expires_in = token_data.get("expires_in")
        account.expires_at = (
            datetime.now(UTC) + timedelta(seconds=expires_in) if expires_in else None
        )
        account.profile_urn = profile_urn
        self.repository.save_account(account)
        self.repository.session.commit()
        return account

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, httpx.TransportError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code == 429 or exc.response.status_code >= 500
        return False
