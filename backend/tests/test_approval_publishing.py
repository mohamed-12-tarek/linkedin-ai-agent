import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Post, User, WorkflowExecution
from app.repositories.posts import PostRepository
from app.repositories.workflow_executions import WorkflowExecutionRepository
from app.services.workflow_approvals import WorkflowApprovalService


class FakeTelegram:
    def send_approval(self, *args, **kwargs):
        return "message"


class FakePublisher:
    def __init__(self):
        self.calls = []

    def publish(self, user_id, post_id):
        self.calls.append((user_id, post_id))
        return type("History", (), {"status": "dry_run"})()


class FakeWorkflow:
    name = "post_generation"
    version = "1.0.0"

    def resume(self, action, context, thread_id):
        assert action == "approve"
        assert thread_id == "thread"
        return {
            "content": "approved content",
            "status": "publishing",
            "current_node": "linkedin_publisher",
            "completed_nodes": [],
            "revisions": [],
        }


def test_approval_resume_invokes_generic_publisher_once() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(id=uuid.uuid4(), email="approval-publish@example.com", password_hash="hash")
    post = Post(
        user_id=user.id,
        topic="Approved",
        description="Approval",
        objective="educate",
        audience="engineers",
        language="English",
        tone="professional",
        length="medium",
        cta_type="engagement",
        emoji_level="low",
        hashtag_mode="auto",
        content="Content",
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
        thread_id="thread",
        status="awaiting_approval",
        input_json="{}",
    )
    session.add(execution)
    session.commit()
    publisher = FakePublisher()
    service = WorkflowApprovalService(
        WorkflowExecutionRepository(session),
        PostRepository(session),
        FakeWorkflow(),
        model_factory=None,
        prompt_engine=None,
        telegram=FakeTelegram(),
        default_chat_id="",
        image_storage=None,
        publisher_service=publisher,
    )

    result = service.resume(execution.id, "approve", "approval-event")

    assert publisher.calls == [(user.id, post.id)]
    assert result.status == "dry_run"
    assert post.status == "dry_run"
