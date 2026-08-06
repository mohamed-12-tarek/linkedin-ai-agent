import operator
from typing import Annotated, Any, TypedDict


class GraphState(TypedDict, total=False):
    execution_id: str
    workflow_name: str
    input: dict[str, Any]
    output: dict[str, Any]
    artifacts: dict[str, Any]
    current_node: str
    completed_nodes: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
    workflow_action: str


class ContentGraphState(GraphState, total=False):
    language: str
    source_text: str
    generated_text: str
    review_notes: list[str]
    image_prompt: str
