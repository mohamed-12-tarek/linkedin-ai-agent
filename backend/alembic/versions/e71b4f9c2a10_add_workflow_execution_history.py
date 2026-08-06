"""add workflow execution history

Revision ID: e71b4f9c2a10
Revises: c3d7a46e21bf
Create Date: 2026-08-06 20:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e71b4f9c2a10"
down_revision: str | None = "c3d7a46e21bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_name", sa.String(), nullable=False),
        sa.Column("workflow_version", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_node", sa.String(), nullable=True),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index(
        "ix_workflow_executions_post_status",
        "workflow_executions",
        ["post_id", "status"],
    )
    op.create_index(
        "ix_workflow_executions_user_created",
        "workflow_executions",
        ["user_id", "created_at"],
    )
    op.create_table(
        "workflow_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("external_event_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_event_id"),
    )
    op.create_index(
        "ix_workflow_actions_execution_created",
        "workflow_actions",
        ["execution_id", "created_at"],
    )
    op.create_table(
        "workflow_node_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("node_name", sa.String(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_node_executions_execution_node",
        "workflow_node_executions",
        ["execution_id", "node_name"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_node_executions_execution_node",
        table_name="workflow_node_executions",
    )
    op.drop_table("workflow_node_executions")
    op.drop_index("ix_workflow_actions_execution_created", table_name="workflow_actions")
    op.drop_table("workflow_actions")
    op.drop_index("ix_workflow_executions_user_created", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_post_status", table_name="workflow_executions")
    op.drop_table("workflow_executions")
