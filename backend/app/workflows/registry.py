from collections.abc import Iterable

from packaging.version import Version

from app.workflows.config import NodeConfig
from app.workflows.nodes import NodeFactory, WorkflowNode


class RegistryError(ValueError):
    pass


class NodeRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, NodeFactory] = {}

    def register(self, node_type: str, factory: NodeFactory, *, replace: bool = False) -> None:
        if node_type in self._factories and not replace:
            raise RegistryError(f"Node type '{node_type}' is already registered")
        self._factories[node_type] = factory

    def create(self, config: NodeConfig) -> WorkflowNode:
        factory = self._factories.get(config.type)
        if factory is None:
            raise RegistryError(f"Unknown node type '{config.type}'")
        return factory(config)

    def registered_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


class GraphRegistry:
    def __init__(self) -> None:
        self._workflows: dict[tuple[str, str], object] = {}

    def register(self, workflow, *, replace: bool = False) -> None:
        key = (workflow.name, workflow.version)
        if key in self._workflows and not replace:
            raise RegistryError(
                f"Workflow '{workflow.name}:{workflow.version}' is already registered"
            )
        self._workflows[key] = workflow

    def get(self, name: str, version: str | None = None):
        if version is not None:
            workflow = self._workflows.get((name, version))
            if workflow is None:
                raise RegistryError(f"Unknown workflow '{name}:{version}'")
            return workflow
        versions = [key for key in self._workflows if key[0] == name]
        if not versions:
            raise RegistryError(f"Unknown workflow '{name}'")
        latest_key = max(versions, key=lambda key: Version(key[1]))
        return self._workflows[latest_key]

    def list(self) -> Iterable[tuple[str, str]]:
        return tuple(sorted(self._workflows))
