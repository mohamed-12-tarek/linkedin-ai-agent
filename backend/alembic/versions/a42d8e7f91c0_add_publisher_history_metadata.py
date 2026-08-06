"""add publisher history metadata

Revision ID: a42d8e7f91c0
Revises: f82d5a1b7c43
Create Date: 2026-08-06 23:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a42d8e7f91c0"
down_revision: str | None = "f82d5a1b7c43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("publish_history", "published_at", nullable=True)
    op.add_column("publish_history", sa.Column("provider", sa.String(), nullable=True))
    op.add_column("publish_history", sa.Column("published_url", sa.String(), nullable=True))
    op.add_column("publish_history", sa.Column("retry_count", sa.Integer(), nullable=True))
    op.add_column("publish_history", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.add_column("publish_history", sa.Column("provider_metadata_json", sa.Text(), nullable=True))
    op.add_column("publish_history", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column(
        "publish_history",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "publish_history",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE publish_history SET provider = 'linkedin' WHERE provider IS NULL")
    op.execute("UPDATE publish_history SET retry_count = 0 WHERE retry_count IS NULL")
    op.execute(
        "UPDATE publish_history SET idempotency_key = 'legacy:' || id::text "
        "WHERE idempotency_key IS NULL"
    )
    op.execute("UPDATE publish_history SET started_at = published_at WHERE started_at IS NULL")
    op.alter_column("publish_history", "provider", nullable=False)
    op.alter_column("publish_history", "retry_count", nullable=False)
    op.alter_column("publish_history", "idempotency_key", nullable=False)
    op.alter_column("publish_history", "started_at", nullable=False)
    op.create_unique_constraint(
        "uq_publish_history_idempotency_key",
        "publish_history",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_publish_history_post_provider_status",
        "publish_history",
        ["post_id", "provider", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_publish_history_post_provider_status", table_name="publish_history")
    op.drop_constraint("uq_publish_history_idempotency_key", "publish_history", type_="unique")
    for column in (
        "completed_at",
        "started_at",
        "error_message",
        "provider_metadata_json",
        "idempotency_key",
        "retry_count",
        "published_url",
        "provider",
    ):
        op.drop_column("publish_history", column)
    op.execute("UPDATE publish_history SET published_at = now() WHERE published_at IS NULL")
    op.alter_column("publish_history", "published_at", nullable=False)
