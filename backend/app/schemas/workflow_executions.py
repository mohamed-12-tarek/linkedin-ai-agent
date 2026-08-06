import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NodeExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_name: str
    attempt_number: int
    status: str
    provider: str | None
    model_name: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: float | None
    latency_ms: float
    error_message: str | None
    started_at: datetime
    completed_at: datetime


class WorkflowActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    external_event_id: str
    action: str
    status: str
    created_at: datetime
    processed_at: datetime | None


class WorkflowExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID
    workflow_name: str
    workflow_version: str
    status: str
    current_node: str | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    node_executions: list[NodeExecutionRead] = []
    actions: list[WorkflowActionRead] = []
