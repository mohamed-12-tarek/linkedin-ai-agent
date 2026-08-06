from typing import Protocol, TypeVar

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from app.workflows.config import END_NODE, START_NODE, WorkflowConfig
from app.workflows.context import ExecutionContext
from app.workflows.nodes import BaseWorkflowNode
from app.workflows.registry import NodeRegistry
from app.workflows.state import GraphState

StateT = TypeVar("StateT", bound=GraphState)


class Workflow(Protocol[StateT]):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def invoke(self, state: StateT, context: ExecutionContext) -> StateT: ...


class CompiledWorkflow[StateT: GraphState]:
    def __init__(self, config: WorkflowConfig, graph: CompiledStateGraph) -> None:
        self.config = config
        self.graph = graph

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def version(self) -> str:
        return self.config.version

    def invoke(self, state: StateT, context: ExecutionContext) -> StateT:
        return self.graph.invoke(state, context=context)

    async def ainvoke(self, state: StateT, context: ExecutionContext) -> StateT:
        return await self.graph.ainvoke(state, context=context)


class WorkflowBuilder:
    def __init__(self, node_registry: NodeRegistry) -> None:
        self.node_registry = node_registry

    def build(
        self,
        config: WorkflowConfig,
        state_schema: type[StateT],
    ) -> CompiledWorkflow[StateT]:
        graph = StateGraph(state_schema, context_schema=ExecutionContext)
        for node_config in config.nodes:
            node = self.node_registry.create(node_config)
            action = self._node_action(node)
            graph.add_node(
                node_config.id,
                action,
                retry_policy=self._retry_policy(node_config.retry),
                metadata={
                    "node_type": node_config.type,
                    "model_role": node_config.model_role.value if node_config.model_role else None,
                },
            )
        for edge in config.edges:
            graph.add_edge(self._edge_name(edge.source), self._edge_name(edge.target))
        return CompiledWorkflow(config, graph.compile())

    @staticmethod
    def _node_action(node):
        if isinstance(node, BaseWorkflowNode):
            return node.as_langgraph_node()

        def run(state, runtime):
            result = node.invoke(state, runtime.context)
            return {**result, "current_node": node.name, "completed_nodes": [node.name]}

        return run

    @staticmethod
    def _edge_name(name: str) -> str:
        return {START_NODE: START, END_NODE: END}.get(name, name)

    @staticmethod
    def _retry_policy(config) -> RetryPolicy | None:
        if config is None:
            return None
        return RetryPolicy(
            initial_interval=config.initial_interval,
            backoff_factor=config.backoff_factor,
            max_interval=config.max_interval,
            max_attempts=config.max_attempts,
            jitter=config.jitter,
        )
