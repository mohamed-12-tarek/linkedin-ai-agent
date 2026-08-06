import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class PublishRequest:
    idempotency_key: str
    content: str
    author_urn: str
    access_token: str
    image_path: str | None = None
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class PublishResult:
    provider: str
    external_id: str
    published_url: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False


class Publisher(Protocol):
    name: str

    def publish(self, request: PublishRequest) -> PublishResult: ...


class PublisherRegistry:
    def __init__(self) -> None:
        self._publishers: dict[str, Publisher] = {}

    def register(self, publisher: Publisher, *, replace: bool = False) -> None:
        if publisher.name in self._publishers and not replace:
            raise ValueError(f"Publisher '{publisher.name}' is already registered")
        self._publishers[publisher.name] = publisher

    def get(self, name: str) -> Publisher:
        publisher = self._publishers.get(name)
        if publisher is None:
            raise ValueError(f"Unknown publisher '{name}'")
        return publisher

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._publishers))


class LinkedInPublisher:
    name = "linkedin"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=30)

    def publish(self, request: PublishRequest) -> PublishResult:
        if request.dry_run:
            digest = hashlib.sha256(request.idempotency_key.encode()).hexdigest()[:20]
            return PublishResult(
                provider=self.name,
                external_id=f"dry-run:{digest}",
                published_url=None,
                metadata={"author_urn": request.author_urn, "image": bool(request.image_path)},
                dry_run=True,
            )
        headers = self._headers(request.access_token, request.idempotency_key)
        image_urn = self._upload_image(request, headers) if request.image_path else None
        payload: dict[str, Any] = {
            "author": request.author_urn,
            "commentary": request.content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if image_urn:
            payload["content"] = {"media": {"id": image_urn}}
        response = self.client.post(
            "https://api.linkedin.com/rest/posts", headers=headers, json=payload
        )
        response.raise_for_status()
        external_id = response.headers.get("x-restli-id")
        if not external_id:
            body = response.json() if response.content else {}
            external_id = body.get("id")
        if not external_id:
            raise RuntimeError("LinkedIn did not return a post ID")
        encoded = external_id.rsplit(":", 1)[-1]
        return PublishResult(
            provider=self.name,
            external_id=external_id,
            published_url=f"https://www.linkedin.com/feed/update/{external_id}/",
            metadata={"image_urn": image_urn, "post_suffix": encoded},
        )

    def exchange_code(self, code: str) -> dict[str, Any]:
        response = self.client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.settings.linkedin_client_id,
                "client_secret": self.settings.linkedin_client_secret,
                "redirect_uri": self.settings.linkedin_redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()

    def fetch_profile_urn(self, access_token: str) -> str:
        response = self.client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        subject = response.json().get("sub")
        if not subject:
            raise RuntimeError("LinkedIn userinfo did not return a subject")
        return f"urn:li:person:{subject}"

    def _upload_image(self, request: PublishRequest, headers: dict[str, str]) -> str:
        initialize = self.client.post(
            "https://api.linkedin.com/rest/images?action=initializeUpload",
            headers=headers,
            json={"initializeUploadRequest": {"owner": request.author_urn}},
        )
        initialize.raise_for_status()
        value = initialize.json()["value"]
        upload_url = value["uploadUrl"]
        image_urn = value["image"]
        path = Path(request.image_path or "")
        with path.open("rb") as image_file:
            upload = self.client.put(
                upload_url,
                headers={"Authorization": f"Bearer {request.access_token}"},
                content=image_file.read(),
            )
        upload.raise_for_status()
        return image_urn

    def _headers(self, access_token: str, idempotency_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": self.settings.linkedin_api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        }


def build_publisher_registry(settings: Settings) -> PublisherRegistry:
    registry = PublisherRegistry()
    registry.register(LinkedInPublisher(settings))
    return registry
