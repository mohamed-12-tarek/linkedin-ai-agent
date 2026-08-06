import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.workflows.context import ExecutionContext
from app.workflows.nodes import BaseWorkflowNode
from app.workflows.post_generation.outputs import (
    ContentOutput,
    CTAOutput,
    GrammarOutput,
    HookOutput,
    JudgeOutput,
    PlanOutput,
    ReviewOutput,
)
from app.workflows.post_generation.prompts import POST_PROMPTS
from app.workflows.post_generation.state import PostGenerationState
from app.workflows.prompts import PromptEngine

OutputT = TypeVar("OutputT", bound=BaseModel)


class ModelOutputError(ValueError):
    pass


class LLMPostNode(BaseWorkflowNode[PostGenerationState]):
    output_schema: type[BaseModel]

    def __init__(self, config, prompt_engine: PromptEngine) -> None:
        super().__init__(config)
        self.prompt_engine = prompt_engine

    def run_model(
        self,
        state: PostGenerationState,
        context: ExecutionContext,
        output_schema: type[OutputT],
        **variables: Any,
    ) -> OutputT:
        if self.config.model_role is None:
            raise RuntimeError(f"Node '{self.name}' has no model role")
        prompt = self.prompt_engine.render(
            POST_PROMPTS[self.config.prompt_template or self.name],
            {**state, **variables},
            context,
        )
        model = context.create_model(self.config.model_role)
        response = model.invoke([("system", prompt.system), ("human", prompt.user)])
        raw_content = response.content if hasattr(response, "content") else response
        if not isinstance(raw_content, str):
            raise ModelOutputError(f"Node '{self.name}' returned non-text output")
        try:
            return output_schema.model_validate_json(self._strip_code_fence(raw_content))
        except ValidationError as exc:
            raise ModelOutputError(
                f"Node '{self.name}' returned invalid structured output"
            ) from exc

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        value = content.strip()
        if value.startswith("```"):
            lines = value.splitlines()
            if lines and lines[-1].strip() == "```":
                value = "\n".join(lines[1:-1])
                if value.lstrip().startswith("json"):
                    value = value.lstrip()[4:].lstrip()
        return value

    @staticmethod
    def revision(node: str, content: str) -> list[dict[str, str]]:
        return [{"node": node, "content": content}]


class PlannerNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        output = self.run_model(state, context, PlanOutput)
        return {"plan": output.model_dump(mode="json")}


class WriterNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        output = self.run_model(
            state,
            context,
            ContentOutput,
            plan_json=json.dumps(state["plan"], ensure_ascii=True),
        )
        return {"content": output.content, "revisions": self.revision(self.name, output.content)}


class ReviewerNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        output = self.run_model(state, context, ReviewOutput)
        return {
            "content": output.content,
            "review_feedback": output.feedback,
            "revisions": self.revision(self.name, output.content),
        }


class HookOptimizerNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        output = self.run_model(state, context, HookOutput)
        return {
            "hook": output.hook,
            "content": output.content,
            "revisions": self.revision(self.name, output.content),
        }


class CTAOptimizerNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        output = self.run_model(state, context, CTAOutput)
        return {
            "cta": output.cta,
            "content": output.content,
            "revisions": self.revision(self.name, output.content),
        }


class GrammarCheckerNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        output = self.run_model(state, context, GrammarOutput)
        return {
            "content": output.content,
            "grammar_corrections": output.corrections,
            "revisions": self.revision(self.name, output.content),
        }


class FinalJudgeNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        output = self.run_model(state, context, JudgeOutput)
        return {
            "content": output.content,
            "hook": output.hook,
            "cta": output.cta,
            "hashtags": output.hashtags,
            "judge_approved": output.approved,
            "judge_score": output.score,
            "judge_reasoning": output.reasoning,
            "revisions": self.revision(self.name, output.content),
        }


class ApprovalBoundaryNode(BaseWorkflowNode[PostGenerationState]):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        return {"approval_required": True, "status": "awaiting_approval"}


class PublisherBoundaryNode(BaseWorkflowNode[PostGenerationState]):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        return {"publishing_deferred": True, "status": "awaiting_approval"}
