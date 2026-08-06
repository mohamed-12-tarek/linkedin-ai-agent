import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    TelegramMessage,
    User,
    WorkflowAction,
    WorkflowExecution,
    WorkflowNodeExecution,
)


class WorkflowExecutionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, execution: WorkflowExecution) -> WorkflowExecution:
        self.session.add(execution)
        self.session.flush()
        return execution

    def get_for_user(self, user_id: uuid.UUID, execution_id: uuid.UUID) -> WorkflowExecution | None:
        return self.session.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id, WorkflowExecution.user_id == user_id)
            .options(
                selectinload(WorkflowExecution.node_executions),
                selectinload(WorkflowExecution.actions),
            )
        )

    def get_by_id(self, execution_id: uuid.UUID) -> WorkflowExecution | None:
        return self.session.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .options(
                selectinload(WorkflowExecution.post),
                selectinload(WorkflowExecution.user).selectinload(User.settings),
            )
        )

    def get_active_for_post(
        self, user_id: uuid.UUID, post_id: uuid.UUID
    ) -> WorkflowExecution | None:
        return self.session.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.user_id == user_id,
                WorkflowExecution.post_id == post_id,
                WorkflowExecution.status == "awaiting_approval",
            )
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[WorkflowExecution]:
        return list(
            self.session.scalars(
                select(WorkflowExecution)
                .where(WorkflowExecution.user_id == user_id)
                .options(selectinload(WorkflowExecution.node_executions))
                .order_by(WorkflowExecution.created_at.desc())
            )
        )

    def add_node_execution(self, node_execution: WorkflowNodeExecution) -> None:
        self.session.add(node_execution)

    def next_attempt(self, execution_id: uuid.UUID, node_name: str) -> int:
        current = self.session.scalar(
            select(func.max(WorkflowNodeExecution.attempt_number)).where(
                WorkflowNodeExecution.execution_id == execution_id,
                WorkflowNodeExecution.node_name == node_name,
            )
        )
        return (current or 0) + 1

    def get_action(self, external_event_id: str) -> WorkflowAction | None:
        return self.session.scalar(
            select(WorkflowAction).where(WorkflowAction.external_event_id == external_event_id)
        )

    def add_action(self, action: WorkflowAction) -> None:
        self.session.add(action)

    def mark_latest_telegram_action(self, post_id: uuid.UUID, action: str) -> None:
        message = self.session.scalar(
            select(TelegramMessage)
            .where(TelegramMessage.post_id == post_id)
            .order_by(TelegramMessage.sent_at.desc())
            .limit(1)
        )
        if message is not None:
            from datetime import UTC, datetime

            message.action_taken = action
            message.action_at = datetime.now(UTC)
