from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from app.workflows.styles import StyleProfile
from app.workflows.types import ModelRole

if TYPE_CHECKING:
    from app.integrations.llm import ChatModelFactory


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    user_id: uuid.UUID
    execution_id: uuid.UUID
    workflow_name: str
    workflow_version: str
    model_factory: ChatModelFactory | None = None
    model_role_overrides: Mapping[ModelRole, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    variables: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    style: StyleProfile | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "model_role_overrides",
            MappingProxyType(dict(self.model_role_overrides)),
        )
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def create_model(self, role: ModelRole):
        if self.model_factory is None:
            raise RuntimeError("No chat model factory is available in this execution context")
        resolved_role = self.model_role_overrides.get(role, role.value)
        return self.model_factory.create_for_role(self.user_id, resolved_role)

    def runtime_values(self) -> dict[str, Any]:
        return {
            "execution_id": str(self.execution_id),
            "user_id": str(self.user_id),
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            **self.variables,
        }
