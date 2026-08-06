import uuid

import pytest

pytest.importorskip("langgraph")

from app.workflows.config import EdgeConfig, NodeConfig, RetryConfig, WorkflowConfig
from app.workflows.context import ExecutionContext
from app.workflows.nodes import BaseWorkflowNode
from app.workflows.registry import GraphRegistry, NodeRegistry
from app.workflows.state import GraphState
from app.workflows.workflow import WorkflowBuilder


class EchoNode(BaseWorkflowNode[GraphState]):
    def invoke(self, state: GraphState, context: ExecutionContext) -> dict:
        return {
            "current_node": "incorrect",
            "completed_nodes": ["incorrect"],
            "output": {
                "message": state["input"]["message"],
                "workflow": context.workflow_name,
                "prefix": self.config.settings["prefix"],
            }
        }


def test_configured_workflow_compiles_registers_and_invokes() -> None:
    nodes = NodeRegistry()
    nodes.register("test.echo", EchoNode)
    config = WorkflowConfig(
        name="infrastructure.echo",
        version="1.0.0",
        nodes=(
            NodeConfig(
                id="echo",
                type="test.echo",
                settings={"prefix": "test"},
                retry=RetryConfig(max_attempts=2),
            ),
        ),
        edges=(
            EdgeConfig(source="$start", target="echo"),
            EdgeConfig(source="echo", target="$end"),
        ),
    )
    workflow = WorkflowBuilder(nodes).build(config, GraphState)
    registry = GraphRegistry()
    registry.register(workflow)
    context = ExecutionContext(
        user_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        workflow_name=config.name,
        workflow_version=config.version,
    )

    result = registry.get(config.name).invoke(
        {"input": {"message": "hello"}, "completed_nodes": [], "errors": []},
        context,
    )

    assert result["output"] == {
        "message": "hello",
        "workflow": "infrastructure.echo",
        "prefix": "test",
    }
    assert result["current_node"] == "echo"
    assert result["completed_nodes"] == ["echo"]
