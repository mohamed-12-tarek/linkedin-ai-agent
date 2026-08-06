from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.workflows.types import ModelRole

START_NODE = "$start"
END_NODE = "$end"


class RetryConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_interval: float = Field(default=0.5, gt=0)
    backoff_factor: float = Field(default=2.0, ge=1)
    max_interval: float = Field(default=30.0, gt=0)
    jitter: bool = True


class NodeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1, pattern="^[a-z][a-z0-9_]*$")
    type: str = Field(min_length=1, pattern="^[a-z][a-z0-9_.-]*$")
    model_role: ModelRole | None = None
    prompt_template: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    retry: RetryConfig | None = None
    routes: dict[str, str] = Field(default_factory=dict)


class EdgeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    target: str


class WorkflowConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, pattern="^[a-z][a-z0-9_.-]*$")
    version: str = Field(min_length=1, pattern=r"^\d+\.\d+\.\d+$")
    description: str = ""
    nodes: tuple[NodeConfig, ...] = Field(min_length=1)
    edges: tuple[EdgeConfig, ...] = Field(min_length=2)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_topology(self) -> "WorkflowConfig":
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Workflow node IDs must be unique")
        edge_pairs = [(edge.source, edge.target) for edge in self.edges]
        if len(edge_pairs) != len(set(edge_pairs)):
            raise ValueError("Workflow edges must be unique")
        valid_ids = {*node_ids, START_NODE, END_NODE}
        for edge in self.edges:
            if edge.source not in valid_ids or edge.target not in valid_ids:
                raise ValueError(f"Edge references an unknown node: {edge.source} -> {edge.target}")
            if edge.source == END_NODE or edge.target == START_NODE:
                raise ValueError(f"Invalid edge direction: {edge.source} -> {edge.target}")
        if not any(edge.source == START_NODE for edge in self.edges):
            raise ValueError("Workflow must define an edge from $start")
        if not any(edge.target == END_NODE for edge in self.edges):
            raise ValueError("Workflow must define an edge to $end")
        reachable = self._reachable_nodes(START_NODE, reverse=False)
        disconnected = sorted(set(node_ids) - reachable)
        if disconnected:
            raise ValueError(f"Workflow contains unreachable nodes: {', '.join(disconnected)}")
        terminating = self._reachable_nodes(END_NODE, reverse=True)
        non_terminating = sorted(set(node_ids) - terminating)
        if non_terminating:
            raise ValueError(
                f"Workflow nodes cannot reach $end: {', '.join(non_terminating)}"
            )
        return self

    def _reachable_nodes(self, origin: str, *, reverse: bool) -> set[str]:
        adjacency: dict[str, set[str]] = {}
        for edge in self.edges:
            source, target = (edge.target, edge.source) if reverse else (edge.source, edge.target)
            adjacency.setdefault(source, set()).add(target)
        visited: set[str] = set()
        pending = [origin]
        while pending:
            current = pending.pop()
            for target in adjacency.get(current, set()):
                if target not in visited:
                    visited.add(target)
                    pending.append(target)
        return visited
