"""add image pipeline metadata

Revision ID: f82d5a1b7c43
Revises: e71b4f9c2a10
Create Date: 2026-08-06 22:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f82d5a1b7c43"  # pragma: allowlist secret
down_revision: str | None = "e71b4f9c2a10"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("images", sa.Column("content_type", sa.String(), nullable=True))
    op.add_column("images", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("images", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("images", sa.Column("review_status", sa.String(), nullable=True))
    op.create_index("ix_images_post_selected", "images", ["post_id", "is_selected"])


def downgrade() -> None:
    op.drop_index("ix_images_post_selected", table_name="images")
    op.drop_column("images", "review_status")
    op.drop_column("images", "height")
    op.drop_column("images", "width")
    op.drop_column("images", "content_type")
