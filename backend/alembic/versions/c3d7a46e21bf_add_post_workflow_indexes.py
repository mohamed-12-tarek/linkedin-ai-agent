"""add post workflow indexes

Revision ID: c3d7a46e21bf
Revises: 8f2c61e4a9d7
Create Date: 2026-08-06 20:20:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3d7a46e21bf"  # pragma: allowlist secret
down_revision: str | None = "8f2c61e4a9d7"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_posts_user_created_at",
        "posts",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_post_versions_post_version",
        "post_versions",
        ["post_id", "version_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_post_versions_post_version", table_name="post_versions")
    op.drop_index("ix_posts_user_created_at", table_name="posts")
