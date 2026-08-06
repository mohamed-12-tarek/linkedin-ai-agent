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
