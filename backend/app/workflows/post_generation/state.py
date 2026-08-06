import operator
from typing import Annotated, Any, TypedDict

from app.workflows.state import GraphState


class NodeRevision(TypedDict):
    node: str
    content: str


class PostGenerationState(GraphState, total=False):
    topic: str
    description: str
    objective: str
    audience: str
    language: str
    length: str
    cta_type: str
    emoji_level: str
    hashtag_mode: str
    image_mode: str
    image_prompt: str | None
    image_upload_id: str | None
    image_path: str | None
    image_provider: str | None
    image_model: str | None
    image_content_type: str | None
    image_width: int | None
    image_height: int | None
    image_review_status: str | None
    plan: dict[str, Any]
    content: str
    hook: str
    cta: str
    hashtags: list[str]
    review_feedback: list[str]
    grammar_corrections: list[str]
    judge_score: float
    judge_reasoning: str
    judge_approved: bool
    approval_required: bool
    publishing_deferred: bool
    status: str
    revisions: Annotated[list[NodeRevision], operator.add]
