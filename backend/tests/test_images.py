import io
import uuid

import httpx
import pytest
from PIL import Image as PillowImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.integrations.images import (
    ImageGenerationResult,
    ImageProviderRegistry,
    LocalImageStorage,
    PollinationsImageProvider,
)
from app.integrations.telegram import TelegramClient
from app.models import Post, User, WorkflowExecution
from app.repositories.posts import PostRepository
from app.repositories.workflow_executions import WorkflowExecutionRepository
from app.services.workflow_approvals import WorkflowApprovalService
from app.workflows.config import NodeConfig
from app.workflows.context import ExecutionContext
from app.workflows.post_generation.nodes import ImageGenerationNode, ImageReviewNode
from app.workflows.prompts import PromptEngine
from app.workflows.styles import StyleEngine


def png_bytes(width: int = 512, height: int = 512) -> bytes:
    buffer = io.BytesIO()
    PillowImage.new("RGB", (width, height), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


class FailingProvider:
    name = "failing"

    def generate(self, prompt: str):
        raise RuntimeError("unavailable")


class FakeProvider:
    name = "fake"

    def generate(self, prompt: str):
        return ImageGenerationResult("fake", "fake-image", png_bytes(), "image/png")


def test_image_provider_registry_falls_back_in_order() -> None:
    registry = ImageProviderRegistry()
    registry.register(FailingProvider())
    registry.register(FakeProvider())

    result = registry.generate_with_fallback("visual", ["failing", "fake"])

    assert result.provider == "fake"


def test_pollinations_provider_encodes_prompt_and_returns_bytes() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=png_bytes(), headers={"content-type": "image/png"})

    provider = PollinationsImageProvider(
        Settings(), httpx.Client(transport=httpx.MockTransport(handler))
    )

    result = provider.generate("clean architecture diagram")

    assert result.content_type == "image/png"
    assert "clean%20architecture%20diagram" in str(requests[0].url)


def test_upload_and_ai_nodes_use_shared_storage(tmp_path) -> None:
    settings = Settings(local_storage_path=str(tmp_path))
    storage = LocalImageStorage(settings)
    upload_id = storage.stage_upload(png_bytes(), "image/png")
    context = ExecutionContext(
        user_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        workflow_name="post_generation",
        workflow_version="1.0.0",
    )
    upload_node = ImageGenerationNode(
        NodeConfig(id="image_generation", type="test", model_role="writer"),
        PromptEngine(StyleEngine()),
        ImageProviderRegistry(),
        storage,
        (),
    )

    uploaded = upload_node.invoke(
        {"image_mode": "upload", "image_upload_id": upload_id}, context
    )
    reviewed = ImageReviewNode(
        NodeConfig(id="image_review", type="test"), storage
    ).invoke({"image_mode": "upload", **uploaded}, context)

    assert reviewed["image_review_status"] == "approved"
    assert reviewed["image_width"] == 512

    providers = ImageProviderRegistry()
    providers.register(FakeProvider())
    ai_node = ImageGenerationNode(
        NodeConfig(id="image_generation", type="test", model_role="writer"),
        PromptEngine(StyleEngine()),
        providers,
        storage,
        ("fake",),
    )
    generated = ai_node.invoke(
        {"image_mode": "ai", "image_prompt": "professional visual"}, context
    )

    assert generated["image_provider"] == "fake"
    assert generated["image_width"] == 512


def test_telegram_sends_photo_with_approval_keyboard(tmp_path) -> None:
    image_path = tmp_path / "approval.png"
    image_path.write_bytes(png_bytes())
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 77}})

    client = TelegramClient(
        Settings(telegram_bot_token="token"),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    message_id = client.send_approval(
        "123", uuid.uuid4(), "Post with image", image_path=str(image_path)
    )

    assert message_id == "77"
    assert requests[0].url.path.endswith("/sendPhoto")


def test_storage_rejects_small_or_unsupported_uploads(tmp_path) -> None:
    storage = LocalImageStorage(Settings(local_storage_path=str(tmp_path)))

    with pytest.raises(ValueError, match="Only JPEG"):
        storage.stage_upload(b"not an image", "application/pdf")


def test_reviewed_image_metadata_is_persisted_for_post(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(id=uuid.uuid4(), email="images@example.com", password_hash="hash")
    post = Post(
        user_id=user.id,
        topic="Images",
        description="Image persistence",
        objective="educate",
        audience="engineers",
        language="English",
        tone="professional",
        length="medium",
        cta_type="engagement",
        emoji_level="low",
        hashtag_mode="auto",
        content="Post content",
        status="awaiting_approval",
    )
    session.add_all([user, post])
    session.commit()
    execution = WorkflowExecution(
        id=uuid.uuid4(),
        user_id=user.id,
        post_id=post.id,
        workflow_name="post_generation",
        workflow_version="1.0.0",
        thread_id=str(uuid.uuid4()),
        status="running",
        input_json="{}",
    )
    session.add(execution)
    session.commit()
    storage = LocalImageStorage(Settings(local_storage_path=str(tmp_path)))
    reviewed_path = storage.persist_for_post(
        execution.id, png_bytes(), "image/png", "generated"
    )
    service = WorkflowApprovalService(
        WorkflowExecutionRepository(session),
        PostRepository(session),
        workflow=None,
        model_factory=None,
        prompt_engine=None,
        telegram=None,
        default_chat_id="",
        image_storage=storage,
    )

    service._apply_result(
        execution,
        post,
        {
            "content": "Post content",
            "status": "awaiting_approval",
            "image_path": str(reviewed_path),
            "image_provider": "fake",
            "image_model": "fake-image",
            "image_content_type": "image/png",
            "image_width": 512,
            "image_height": 512,
            "image_review_status": "approved",
            "revisions": [],
            "__interrupt__": ["pending"],
        },
    )
    session.commit()

    assert len(post.images) == 1
    assert post.images[0].is_selected is True
    assert post.images[0].review_status == "approved"
    assert post.images[0].width == 512
