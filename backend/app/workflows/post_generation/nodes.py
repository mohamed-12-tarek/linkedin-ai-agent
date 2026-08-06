import json
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.workflows.context import ExecutionContext
from app.workflows.nodes import BaseWorkflowNode
from app.workflows.post_generation.outputs import (
    ContentOutput,
    CTAOutput,
    GrammarOutput,
    HookOutput,
    ImagePromptOutput,
    JudgeOutput,
    PlanOutput,
    ReviewOutput,
    TranslationOutput,
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
        model_metadata = context.model_metadata(self.config.model_role)
        started = time.perf_counter()
        try:
            response = model.invoke([("system", prompt.system), ("human", prompt.user)])
        except Exception as exc:
            context.record_telemetry(
                {
                    "node_name": self.name,
                    "status": "failed",
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "provider": model_metadata.get("provider"),
                    "model_name": model_metadata.get("model_name"),
                    "error_message": str(exc),
                }
            )
            raise
        raw_content = response.content if hasattr(response, "content") else response
        usage = getattr(response, "usage_metadata", {}) or {}
        total_tokens = usage.get("total_tokens")
        estimated_cost = None
        if total_tokens is not None:
            estimated_cost = total_tokens / 1000 * float(model_metadata.get("cost_per_1k", 0))
        if not isinstance(raw_content, str):
            raise ModelOutputError(f"Node '{self.name}' returned non-text output")
        try:
            parsed = output_schema.model_validate_json(self._strip_code_fence(raw_content))
        except ValidationError as exc:
            error = ModelOutputError(
                f"Node '{self.name}' returned invalid structured output"
            )
            context.record_telemetry(
                {
                    "node_name": self.name,
                    "status": "failed",
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "provider": model_metadata.get("provider"),
                    "model_name": model_metadata.get("model_name"),
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "total_tokens": total_tokens,
                    "estimated_cost": estimated_cost,
                    "error_message": str(error),
                }
            )
            raise error from exc
        context.record_telemetry(
            {
                "node_name": self.name,
                "status": "completed",
                "latency_ms": (time.perf_counter() - started) * 1000,
                "provider": model_metadata.get("provider") or model.__class__.__name__,
                "model_name": model_metadata.get("model_name")
                or getattr(model, "model_name", None)
                or getattr(model, "model", None),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "total_tokens": total_tokens,
                "estimated_cost": estimated_cost,
            }
        )
        return parsed

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


class TranslatorNode(LLMPostNode):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        target_language = context.variables.get("target_language", state.get("language", "English"))
        output = self.run_model(
            state,
            context,
            TranslationOutput,
            target_language=target_language,
        )
        return {
            "content": output.content,
            "language": output.language,
            "revisions": self.revision(self.name, output.content),
        }


class ImageGenerationNode(LLMPostNode):
    def __init__(
        self,
        config,
        prompt_engine,
        image_providers,
        image_storage,
        provider_order,
    ) -> None:
        super().__init__(config, prompt_engine)
        self.image_providers = image_providers
        self.image_storage = image_storage
        self.provider_order = provider_order

    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        mode = state.get("image_mode", "none")
        if mode == "none":
            return {"image_review_status": "skipped"}
        if mode == "upload":
            if not state.get("image_upload_id"):
                raise ValueError("Image upload ID is required for upload mode")
            path = self.image_storage.resolve_upload(state["image_upload_id"])
            return {
                "image_path": str(path),
                "image_content_type": self.image_storage.content_type_for(path),
                "image_review_status": "pending",
                "image_provider": "upload",
                "image_model": "existing_upload",
            }
        if mode != "ai":
            raise ValueError(f"Unsupported image mode '{mode}'")
        prompt = state.get("image_prompt")
        if not prompt:
            prompt_output = self.run_model(state, context, ImagePromptOutput)
            prompt = prompt_output.prompt
        started = time.perf_counter()
        try:
            result = self.image_providers.generate_with_fallback(
                prompt, list(context.variables.get("image_provider_order", self.provider_order))
            )
        except Exception as exc:
            context.record_telemetry(
                {
                    "node_name": f"{self.name}.provider",
                    "status": "failed",
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "error_message": str(exc),
                }
            )
            raise
        context.record_telemetry(
            {
                "node_name": f"{self.name}.provider",
                "status": "completed",
                "latency_ms": (time.perf_counter() - started) * 1000,
                "provider": result.provider,
                "model_name": result.model,
            }
        )
        path = self.image_storage.persist_for_post(
            context.execution_id, result.content, result.content_type, "generated"
        )
        width, height, _ = self.image_storage.inspect(path)
        return {
            "image_path": str(path),
            "image_prompt": prompt,
            "image_provider": result.provider,
            "image_model": result.model,
            "image_content_type": result.content_type,
            "image_width": width,
            "image_height": height,
            "image_review_status": "pending",
        }


class ImageReviewNode(BaseWorkflowNode[PostGenerationState]):
    def __init__(self, config, image_storage) -> None:
        super().__init__(config)
        self.image_storage = image_storage

    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        if state.get("image_mode", "none") == "none":
            return {"image_review_status": "skipped"}
        path = state.get("image_path")
        if not path:
            raise ValueError("Image path is missing")
        width, height, _ = self.image_storage.inspect(Path(path))
        if width < 256 or height < 256:
            raise ValueError("Image must be at least 256x256 pixels")
        return {
            "image_width": width,
            "image_height": height,
            "image_review_status": "approved",
        }


class ApprovalBoundaryNode(BaseWorkflowNode[PostGenerationState]):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        from langgraph.types import interrupt

        action = interrupt(
            {
                "execution_id": str(context.execution_id),
                "actions": [
                    "approve", "reject", "rewrite", "regenerate_hook", "regenerate_cta",
                    "shorter", "longer", "professional", "friendly", "technical", "translate",
                ],
            }
        )
        update: dict[str, Any] = {"workflow_action": str(action), "approval_required": True}
        if action == "shorter":
            update["length"] = "short"
        elif action == "longer":
            update["length"] = "long"
        elif action in {"professional", "friendly", "technical"}:
            update["tone"] = action
        return update


class PublisherBoundaryNode(BaseWorkflowNode[PostGenerationState]):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        return {
            "publishing_deferred": False,
            "approval_required": False,
            "status": "publishing",
        }


class RejectionNode(BaseWorkflowNode[PostGenerationState]):
    def invoke(self, state: PostGenerationState, context: ExecutionContext) -> dict[str, Any]:
        return {"status": "rejected", "approval_required": False}
