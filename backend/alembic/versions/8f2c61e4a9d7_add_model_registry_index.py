"""add model registry index

Revision ID: 8f2c61e4a9d7
Revises: feb89f310868
Create Date: 2026-08-06 19:10:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "8f2c61e4a9d7"
down_revision: str | None = "feb89f310868"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_llm_models_user_role_available",
        "llm_models",
        ["user_id", "role_type", "is_available"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_llm_models_user_role_available", table_name="llm_models")
