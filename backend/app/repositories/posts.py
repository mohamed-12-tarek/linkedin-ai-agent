import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Post, PostVersion, Style


class PostRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: uuid.UUID) -> list[Post]:
        statement = (
            select(Post)
            .where(Post.user_id == user_id)
            .options(selectinload(Post.versions))
            .order_by(Post.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get_for_user(self, user_id: uuid.UUID, post_id: uuid.UUID) -> Post | None:
        statement = (
            select(Post)
            .where(Post.id == post_id, Post.user_id == user_id)
            .options(selectinload(Post.versions))
        )
        return self.session.scalar(statement)

    def get_style_for_user(self, user_id: uuid.UUID, style_id: uuid.UUID) -> Style | None:
        return self.session.scalar(
            select(Style).where(Style.id == style_id, Style.user_id == user_id)
        )

    def add_post(self, post: Post) -> Post:
        self.session.add(post)
        self.session.flush()
        return post

    def next_version_number(self, post_id: uuid.UUID) -> int:
        current = self.session.scalar(
            select(func.max(PostVersion.version_number)).where(PostVersion.post_id == post_id)
        )
        return (current or 0) + 1

    def add_version(self, version: PostVersion) -> None:
        self.session.add(version)
