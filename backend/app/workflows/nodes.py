from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from app.workflows.config import NodeConfig
from app.workflows.context import ExecutionContext
from app.workflows.state import GraphState

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

StateT = TypeVar("StateT", bound=GraphState)


class WorkflowNode(Protocol[StateT]):
    @property
    def name(self) -> str: ...

    def invoke(self, state: StateT, context: ExecutionContext) -> dict[str, Any]: ...


class BaseWorkflowNode[StateT: GraphState](ABC):
    def __init__(self, config: NodeConfig) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return self.config.id

    @abstractmethod
    def invoke(self, state: StateT, context: ExecutionContext) -> dict[str, Any]:
        raise NotImplementedError

    def as_langgraph_node(self) -> Callable[[StateT, Runtime[ExecutionContext]], dict[str, Any]]:
        def run(state: StateT, runtime: Runtime[ExecutionContext]) -> dict[str, Any]:
            result = self.invoke(state, runtime.context)
            return {**result, "current_node": self.name, "completed_nodes": [self.name]}

        return run


NodeFactory = Callable[[NodeConfig], WorkflowNode]
