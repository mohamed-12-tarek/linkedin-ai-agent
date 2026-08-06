from collections.abc import Mapping
from dataclasses import dataclass
from string import Formatter
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.workflows.context import ExecutionContext
from app.workflows.styles import StyleEngine, StyleProfile


class PromptTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    system_template: str
    user_template: str
    required_variables: frozenset[str] = frozenset()
    output_instructions: str | None = None


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    name: str
    system: str
    user: str
    variables: Mapping[str, Any]


class PromptRenderError(ValueError):
    pass


class PromptEngine:
    def __init__(self, style_engine: StyleEngine) -> None:
        self.style_engine = style_engine

    def render(
        self,
        template: PromptTemplate,
        variables: Mapping[str, Any],
        context: ExecutionContext,
        style: StyleProfile | None = None,
    ) -> RenderedPrompt:
        resolved_style = style or context.style
        values = {**context.runtime_values(), **variables}
        if resolved_style is not None:
            values.update(self.style_engine.prompt_variables(resolved_style))
        else:
            values.setdefault("style_instructions", "")

        required = set(template.required_variables)
        required.update(self._template_fields(template.system_template))
        required.update(self._template_fields(template.user_template))
        missing = sorted(field for field in required if field not in values)
        if missing:
            raise PromptRenderError(f"Missing prompt variables: {', '.join(missing)}")

        system = template.system_template.format_map(values)
        user = template.user_template.format_map(values)
        if template.output_instructions:
            user = f"{user}\n\nOutput requirements:\n{template.output_instructions}"
        return RenderedPrompt(template.name, system, user, MappingProxyType(values))

    @staticmethod
    def _template_fields(template: str) -> set[str]:
        return {
            field_name.split(".", 1)[0].split("[", 1)[0]
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name
        }
