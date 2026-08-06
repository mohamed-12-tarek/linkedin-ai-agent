import json
import uuid
from datetime import UTC, datetime

from app.models import (
    Image,
    PostVersion,
    TelegramMessage,
    WorkflowAction,
    WorkflowExecution,
    WorkflowNodeExecution,
)
from app.schemas.workflow_executions import WorkflowExecutionRead
from app.workflows.context import ExecutionContext


class WorkflowExecutionNotFoundError(Exception):
    pass


class WorkflowActionAlreadyProcessed(Exception):
    pass


class TelegramChatMismatchError(Exception):
    pass


class WorkflowApprovalService:
    def __init__(
        self,
        execution_repository,
        post_repository,
        workflow,
        model_factory,
        prompt_engine,
        telegram,
        default_chat_id: str,
        image_storage,
        publisher_service=None,
    ) -> None:
        self.executions = execution_repository
        self.posts = post_repository
        self.workflow = workflow
        self.model_factory = model_factory
        self.prompt_engine = prompt_engine
        self.telegram = telegram
        self.default_chat_id = default_chat_id
        self.image_storage = image_storage
        self.publisher_service = publisher_service

    def list_executions(self, user_id: uuid.UUID) -> list[WorkflowExecutionRead]:
        return [
            WorkflowExecutionRead.model_validate(execution)
            for execution in self.executions.list_for_user(user_id)
        ]

    def start(self, user_id: uuid.UUID, post, initial_state: dict, style) -> dict:
        execution_id = uuid.uuid4()
        thread_id = str(execution_id)
        execution = WorkflowExecution(
            id=execution_id,
            user_id=user_id,
            post_id=post.id,
            workflow_name=self.workflow.name,
            workflow_version=self.workflow.version,
            thread_id=thread_id,
            status="running",
            current_node="planner",
            input_json=json.dumps(initial_state.get("input", {})),
        )
        self.executions.add(execution)
        self.executions.session.commit()
        context = self._context(execution, style)
        try:
            result = self.workflow.invoke(initial_state, context, thread_id=thread_id)
            self._apply_result(execution, post, result)
            self.executions.session.commit()
        except Exception:
            self.executions.session.rollback()
            failed = self.executions.get_by_id(execution.id)
            if failed is not None:
                failed.status = "failed"
                failed.completed_at = datetime.now(UTC)
                failed.post.status = "failed"
                self.executions.session.commit()
            raise
        self._send_approval(execution, post)
        return result

    def resume(
        self,
        execution_id: uuid.UUID,
        action: str,
        external_event_id: str,
        payload: dict | None = None,
        actor_chat_id: str | None = None,
    ) -> WorkflowExecution:
        existing = self.executions.get_action(external_event_id)
        if existing is not None:
            execution = self.executions.get_by_id(execution_id)
            if execution is None:
                raise WorkflowExecutionNotFoundError
            if existing.status in {"processed", "processing"}:
                return execution
            action_record = existing
            action_record.status = "processing"
        else:
            action_record = WorkflowAction(
                execution_id=execution_id,
                external_event_id=external_event_id,
                action=action,
                payload_json=json.dumps(payload or {}),
                status="processing",
            )
            self.executions.add_action(action_record)
        execution = self.executions.get_by_id(execution_id)
        if execution is None:
            raise WorkflowExecutionNotFoundError
        expected_chat_id = execution.user.telegram_chat_id or self.default_chat_id
        if (
            actor_chat_id is not None
            and expected_chat_id
            and str(actor_chat_id) != str(expected_chat_id)
        ):
            raise TelegramChatMismatchError
        execution.status = "running"
        self.executions.session.commit()
        target_language = self._target_language(execution)
        context = self._context(
            execution,
            self._style_for_execution(execution, action),
            variables={"target_language": target_language},
        )
        try:
            result = self.workflow.resume(action, context, execution.thread_id)
            self._apply_result(execution, execution.post, result)
            if action == "approve" and self.publisher_service is not None:
                history = self.publisher_service.publish(execution.user_id, execution.post_id)
                execution.post.status = history.status
                execution.status = history.status
                execution.completed_at = datetime.now(UTC)
                result["published"] = history.status in {"published", "dry_run"}
            self.executions.mark_latest_telegram_action(execution.post_id, action)
            action_record.status = "processed"
            action_record.processed_at = datetime.now(UTC)
            self.executions.session.commit()
        except Exception:
            self.executions.session.rollback()
            failed_action = self.executions.get_action(external_event_id)
            failed_execution = self.executions.get_by_id(execution_id)
            if failed_action is not None:
                failed_action.status = "failed"
                failed_action.processed_at = datetime.now(UTC)
            if failed_execution is not None:
                failed_execution.status = "awaiting_approval"
                failed_execution.post.status = "awaiting_approval"
                failed_execution.completed_at = None
            self.executions.session.commit()
            raise
        if execution.status == "awaiting_approval":
            self._send_approval(execution, execution.post)
        return execution

    def _context(
        self,
        execution: WorkflowExecution,
        style,
        variables: dict | None = None,
    ) -> ExecutionContext:
        return ExecutionContext(
            user_id=execution.user_id,
            execution_id=execution.id,
            workflow_name=execution.workflow_name,
            workflow_version=execution.workflow_version,
            model_factory=self.model_factory,
            style=style,
            variables=variables or {},
            telemetry_callback=lambda event: self._record_telemetry(execution.id, event),
        )

    def _record_telemetry(self, execution_id: uuid.UUID, event: dict) -> None:
        now = datetime.now(UTC)
        total_tokens = event.get("total_tokens")
        self.executions.add_node_execution(
            WorkflowNodeExecution(
                execution_id=execution_id,
                node_name=event["node_name"],
                attempt_number=self.executions.next_attempt(execution_id, event["node_name"]),
                status=event["status"],
                provider=event.get("provider"),
                model_name=event.get("model_name"),
                input_tokens=event.get("input_tokens"),
                output_tokens=event.get("output_tokens"),
                total_tokens=total_tokens,
                estimated_cost=event.get("estimated_cost"),
                latency_ms=event["latency_ms"],
                error_message=event.get("error_message"),
                started_at=now,
                completed_at=now,
            )
        )
        self.executions.session.commit()

    def _apply_result(self, execution: WorkflowExecution, post, result: dict) -> None:
        post.content = result.get("content", post.content)
        post.hook = result.get("hook", post.hook)
        post.cta_text = result.get("cta", post.cta_text)
        if "hashtags" in result:
            post.hashtags = " ".join(result["hashtags"])
        post.language = result.get("language", post.language)
        post.tone = result.get("tone", post.tone)
        post.length = result.get("length", post.length)
        self._persist_image(post, result)
        execution.current_node = result.get("current_node")
        execution.state_json = json.dumps(result, default=str)
        interrupted = bool(result.get("__interrupt__"))
        if interrupted:
            execution.status = "awaiting_approval"
            post.status = "awaiting_approval"
        else:
            execution.status = result.get("status", "completed")
            post.status = execution.status
            execution.completed_at = datetime.now(UTC)
        persisted_count = self.posts.version_count(post.id)
        next_version = self.posts.next_version_number(post.id)
        for revision in result.get("revisions", [])[persisted_count:]:
            self.posts.add_version(
                PostVersion(
                    post_id=post.id,
                    version_number=next_version,
                    content=revision["content"],
                    created_by_node=revision["node"],
                )
            )
            next_version += 1

    def _send_approval(self, execution: WorkflowExecution, post) -> None:
        chat_id = execution.user.telegram_chat_id or self.default_chat_id
        if not chat_id or not post.content:
            return
        selected_image = next((image for image in post.images if image.is_selected), None)
        image_path = selected_image.url if selected_image is not None else None
        message_id = self.telegram.send_approval(
            chat_id,
            execution.id,
            post.content,
            image_path=image_path,
        )
        self.executions.session.add(
            TelegramMessage(post_id=post.id, telegram_message_id=message_id)
        )
        self.executions.session.commit()

    def _persist_image(self, post, result: dict) -> None:
        path_value = result.get("image_path")
        review_status = result.get("image_review_status")
        if not path_value or review_status != "approved":
            return
        from pathlib import Path

        source_path = Path(path_value)
        if not source_path.exists():
            raise FileNotFoundError("Reviewed image file is missing")
        if post.images and any(image.url == str(source_path) for image in post.images):
            return
        content_type = result.get("image_content_type") or self.image_storage.content_type_for(
            source_path
        )
        target_path = self.image_storage.persist_for_post(
            post.id,
            source_path.read_bytes(),
            content_type,
            result.get("image_provider") or "image",
        )
        for image in post.images:
            image.is_selected = False
        self.executions.session.add(
            Image(
                post_id=post.id,
                source=result.get("image_provider") or "upload",
                prompt_used=result.get("image_prompt"),
                model_used=result.get("image_model"),
                url=str(target_path),
                is_selected=True,
                content_type=content_type,
                width=result.get("image_width"),
                height=result.get("image_height"),
                review_status=review_status,
            )
        )

    @staticmethod
    def _target_language(execution: WorkflowExecution) -> str:
        settings = execution.user.settings
        if settings and settings.default_language:
            return settings.default_language
        return "English" if execution.post.language.lower() != "english" else "Spanish"

    @staticmethod
    def _style_for_execution(execution: WorkflowExecution, action: str):
        from app.workflows.styles import StyleProfile, Tone, VocabularyLevel

        tone = execution.post.tone.lower()
        vocabulary = VocabularyLevel.GENERAL
        rules: tuple[str, ...] = ()
        if action == "professional":
            tone = "professional"
        elif action == "friendly":
            tone = "conversational"
        elif action == "technical":
            vocabulary = VocabularyLevel.TECHNICAL
            rules = ("Use precise technical terminology appropriate for the audience.",)
        try:
            resolved_tone = Tone(tone)
        except ValueError:
            resolved_tone = Tone.PROFESSIONAL
        return StyleProfile(
            name=action.title(),
            tone=resolved_tone,
            vocabulary=vocabulary,
            custom_rules=rules,
        )
