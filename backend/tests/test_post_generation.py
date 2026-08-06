import json
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

pytest.importorskip("langgraph")

from app.db.base import Base
from app.models import PostVersion, User
from app.repositories.posts import PostRepository
from app.schemas.posts import PostGenerateRequest
from app.services.posts import PostGenerationService
from app.workflows.context import ExecutionContext
from app.workflows.post_generation.workflow import build_post_generation_workflow
from app.workflows.prompts import PromptEngine
from app.workflows.styles import StyleEngine


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.content = json.dumps(payload)


class FakeModel:
    def __init__(self, role: str) -> None:
        self.role = role

    def invoke(self, messages):
        system_prompt = messages[0][1]
        user_prompt = messages[-1][1]
        if "content strategist" in system_prompt:
            return FakeResponse(
                {
                    "angle": "practical resilience",
                    "outline": ["hook", "lesson", "action"],
                    "key_points": ["design for failure"],
                    "hook_direction": "specific outcome",
                }
            )
        if "opening hooks" in system_prompt:
            return FakeResponse(
                {
                    "hook": "Build systems that keep working.",
                    "content": "Build systems that keep working. A reviewed practical post.",
                }
            )
        if "calls to action" in system_prompt:
            return FakeResponse(
                {
                    "cta": "What would you improve first?",
                    "content": "A reviewed practical post. What would you improve first?",
                }
            )
        if "expert LinkedIn writer" in system_prompt:
            return FakeResponse({"content": "A practical post about resilient systems."})
        if self.role == "reviewer":
            if "Correct" in user_prompt:
                return FakeResponse(
                    {"content": "A polished practical post.", "corrections": ["clarity"]}
                )
            return FakeResponse({"content": "A reviewed practical post.", "feedback": ["clear"]})
        if self.role == "judge":
            return FakeResponse(
                {
                    "approved": True,
                    "score": 94,
                    "reasoning": "Clear and useful.",
                    "content": "A final practical post.",
                    "hook": "Build systems that keep working.",
                    "cta": "What would you improve first?",
                    "hashtags": ["#engineering", "#architecture"],
                }
            )
        raise AssertionError(f"Unexpected role {self.role}")


class FakeFactory:
    def create_for_role(self, user_id, role):
        return FakeModel(role)

    def metadata_for_role(self, user_id, role):
        return {"provider": "fake", "model_name": f"fake-{role}", "cost_per_1k": 0}


def make_context(factory: FakeFactory) -> ExecutionContext:
    return ExecutionContext(
        user_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        workflow_name="post_generation",
        workflow_version="1.0.0",
        model_factory=factory,
    )


def test_graph_1_runs_all_nodes_with_fake_models() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    workflow = build_post_generation_workflow(
        PromptEngine(StyleEngine()), checkpointer=InMemorySaver()
    )
    context = make_context(FakeFactory())
    state = {
        "topic": "Resilient systems",
        "description": "A practical lesson",
        "objective": "educate",
        "audience": "engineers",
        "language": "English",
        "length": "medium",
        "cta_type": "engagement",
        "emoji_level": "low",
        "hashtag_mode": "auto",
        "completed_nodes": [],
        "errors": [],
        "revisions": [],
    }

    result = workflow.invoke(state, context, thread_id=str(context.execution_id))

    assert result["completed_nodes"] == [
        "planner",
        "writer",
        "reviewer",
        "hook_optimizer",
        "cta_optimizer",
        "grammar_checker",
        "final_judge",
        "image_generation",
        "image_review",
    ]
    assert result["content"] == "A final practical post."
    assert result["judge_approved"] is True
    assert result["__interrupt__"]
    assert [revision["node"] for revision in result["revisions"]] == [
        "writer",
        "reviewer",
        "hook_optimizer",
        "cta_optimizer",
        "grammar_checker",
        "final_judge",
    ]

    approved = workflow.resume("approve", context, str(context.execution_id))
    assert approved["status"] == "publishing"
    assert approved["publishing_deferred"] is False
    assert approved["completed_nodes"][-2:] == ["telegram_approval", "linkedin_publisher"]


def test_rewrite_resumes_same_thread_and_returns_to_approval() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    workflow = build_post_generation_workflow(
        PromptEngine(StyleEngine()), checkpointer=InMemorySaver()
    )
    context = make_context(FakeFactory())
    state = {
        "topic": "Resilient systems",
        "description": "A practical lesson",
        "objective": "educate",
        "audience": "engineers",
        "language": "English",
        "length": "medium",
        "cta_type": "engagement",
        "emoji_level": "low",
        "hashtag_mode": "auto",
        "completed_nodes": [],
        "errors": [],
        "revisions": [],
    }
    thread_id = str(context.execution_id)
    workflow.invoke(state, context, thread_id=thread_id)

    rewritten = workflow.resume("rewrite", context, thread_id)

    assert rewritten["__interrupt__"]
    assert rewritten["completed_nodes"].count("writer") == 2
    assert rewritten["completed_nodes"].count("final_judge") == 2


def make_service() -> tuple[Session, PostGenerationService, User]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(id=uuid.uuid4(), email="graph@example.com", password_hash="hash")
    session.add(user)
    session.commit()
    workflow = build_post_generation_workflow(PromptEngine(StyleEngine()))
    prompt_engine = PromptEngine(StyleEngine())
    return (
        session,
        PostGenerationService(PostRepository(session), workflow, FakeFactory(), prompt_engine),
        user,
    )


def test_generation_service_persists_post_and_revisions() -> None:
    session, service, user = make_service()
    post = service.generate(
        user.id,
        PostGenerateRequest(
            topic="Resilient systems",
            description="A practical lesson",
            objective="educate",
            audience="engineers",
        ),
    )

    assert post.status == "awaiting_approval"
    assert post.content == "A final practical post."
    assert len(post.versions) == 6
    assert [version.created_by_node for version in post.versions] == [
        "writer",
        "reviewer",
        "hook_optimizer",
        "cta_optimizer",
        "grammar_checker",
        "final_judge",
    ]
    assert session.scalar(select(PostVersion).where(PostVersion.post_id == post.id)) is not None
