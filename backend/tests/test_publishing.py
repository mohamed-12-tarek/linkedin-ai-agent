import io
import json
import uuid

import httpx
from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.security import EncryptionService
from app.db.base import Base
from app.integrations.publishers import LinkedInPublisher, PublisherRegistry, PublishRequest
from app.models import LinkedInAccount, Post, PublishHistory, User
from app.repositories.publishing import PublishingRepository
from app.services.publishing import PublisherService


def make_png() -> bytes:
    buffer = io.BytesIO()
    PillowImage.new("RGB", (256, 256), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def make_database(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(id=uuid.uuid4(), email=f"publish-{uuid.uuid4()}@example.com", password_hash="hash")
    post = Post(
        user_id=user.id,
        topic="Publishing",
        description="A publishable post",
        objective="educate",
        audience="engineers",
        language="English",
        tone="professional",
        length="medium",
        cta_type="engagement",
        emoji_level="low",
        hashtag_mode="auto",
        content="A publishable LinkedIn post.",
        status="approved",
    )
    session.add_all([user, post])
    session.commit()
    return session, user, post


def test_linkedin_dry_run_is_idempotent_without_account(tmp_path) -> None:
    session, user, post = make_database(tmp_path)
    settings = Settings(linkedin_dry_run=True)
    registry = PublisherRegistry()
    registry.register(LinkedInPublisher(settings))
    service = PublisherService(
        PublishingRepository(session),
        registry,
        EncryptionService(settings),
        settings,
    )

    first = service.publish(user.id, post.id)
    second = service.publish(user.id, post.id)

    assert first.id == second.id
    assert first.status == "dry_run"
    assert first.linkedin_post_id.startswith("dry-run:")
    assert len(session.query(PublishHistory).all()) == 1


def test_dry_run_key_does_not_block_later_live_publish(tmp_path) -> None:
    session, user, post = make_database(tmp_path)
    settings = Settings()
    encryption = EncryptionService(settings)
    session.add(
        LinkedInAccount(
            user_id=user.id,
            access_token_encrypted=encryption.encrypt("access"),
            profile_urn="urn:li:person:test",
        )
    )
    session.commit()

    class FakePublisher:
        name = "linkedin"

        def publish(self, request):
            from app.integrations.publishers import PublishResult

            return PublishResult(
                "linkedin",
                "dry" if request.dry_run else "live",
                None if request.dry_run else "https://linkedin.test/live",
                dry_run=request.dry_run,
            )

    registry = PublisherRegistry()
    registry.register(FakePublisher())
    service = PublisherService(PublishingRepository(session), registry, encryption, settings)

    dry_run = service.publish(user.id, post.id, dry_run=True)
    live = service.publish(user.id, post.id, dry_run=False)

    assert dry_run.id != live.id
    assert dry_run.idempotency_key.endswith(":dry-run")
    assert live.idempotency_key.endswith(":live")


def test_linkedin_publisher_publishes_text_and_image_with_mock_http(tmp_path) -> None:
    image_path = tmp_path / "post.png"
    image_path.write_bytes(make_png())
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/images"):
            return httpx.Response(
                200,
                json={
                    "value": {
                        "uploadUrl": "https://upload.test/image",
                        "image": "urn:li:image:1",
                    }
                },
            )
        if request.url.host == "upload.test":
            return httpx.Response(201)
        return httpx.Response(201, headers={"x-restli-id": "urn:li:share:123"})

    settings = Settings(linkedin_api_version="202601")
    publisher = LinkedInPublisher(
        settings,
        httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True),
    )
    result = publisher.publish(
        PublishRequest(
            idempotency_key="key-123",
            content="A post",
            author_urn="urn:li:person:abc",
            access_token="access",
            image_path=str(image_path),
        )
    )

    assert result.external_id == "urn:li:share:123"
    assert result.published_url.endswith("urn:li:share:123/")
    assert len(requests) == 3
    post_payload = json.loads(requests[-1].content)
    assert post_payload["content"]["media"]["id"] == "urn:li:image:1"
    assert requests[-1].headers["idempotency-key"] == "key-123"


def test_publisher_retries_transient_http_failure(tmp_path) -> None:
    session, user, post = make_database(tmp_path)
    calls = 0

    class FlakyPublisher:
        name = "linkedin"

        def publish(self, request):
            nonlocal calls
            calls += 1
            if calls == 1:
                response = httpx.Response(503, request=httpx.Request("POST", "https://test"))
                raise httpx.HTTPStatusError(
                    "temporary", request=response.request, response=response
                )
            from app.integrations.publishers import PublishResult

            return PublishResult("linkedin", "urn:li:share:ok", "https://linkedin.test/ok")

    settings = Settings(publisher_max_retries=2, publisher_retry_delay_seconds=0)
    registry = PublisherRegistry()
    registry.register(FlakyPublisher())
    session.add(
        LinkedInAccount(
            user_id=user.id,
            access_token_encrypted=EncryptionService(settings).encrypt("access"),
            profile_urn="urn:li:person:test",
        )
    )
    session.commit()
    service = PublisherService(
        PublishingRepository(session),
        registry,
        EncryptionService(settings),
        settings,
    )

    history = service.publish(user.id, post.id, idempotency_key="retry-key")

    assert calls == 2
    assert history.status == "published"
    assert history.retry_count == 1


def test_linkedin_account_tokens_are_encrypted(tmp_path) -> None:
    session, user, post = make_database(tmp_path)
    settings = Settings()
    service = PublisherService(
        PublishingRepository(session),
        PublisherRegistry(),
        EncryptionService(settings),
        settings,
    )

    account = service.save_linkedin_account(
        user.id,
        {"access_token": "access-secret", "refresh_token": "refresh-secret", "expires_in": 3600},
        "urn:li:person:abc",
    )

    assert account.access_token_encrypted != "access-secret"
    assert EncryptionService(settings).decrypt(account.access_token_encrypted) == "access-secret"
    assert EncryptionService(settings).decrypt(account.refresh_token_encrypted) == "refresh-secret"


def test_linkedin_oauth_exchange_and_profile_lookup_use_mock_http() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/accessToken"):
            return httpx.Response(200, json={"access_token": "token", "expires_in": 3600})
        return httpx.Response(200, json={"sub": "member123"})

    settings = Settings(
        linkedin_client_id="client",
        linkedin_client_secret="secret",  # pragma: allowlist secret
        linkedin_redirect_uri="http://localhost/callback",
    )
    publisher = LinkedInPublisher(
        settings, httpx.Client(transport=httpx.MockTransport(handler))
    )

    token = publisher.exchange_code("authorization-code")
    urn = publisher.fetch_profile_urn(token["access_token"])

    assert urn == "urn:li:person:member123"
    assert len(requests) == 2
