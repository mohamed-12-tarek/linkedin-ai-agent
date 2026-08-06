import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import LinkedInAccount, Post, PublishHistory


class PublishingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_account(self, user_id: uuid.UUID) -> LinkedInAccount | None:
        return self.session.scalar(
            select(LinkedInAccount)
            .where(LinkedInAccount.user_id == user_id)
            .order_by(LinkedInAccount.expires_at.desc().nullslast())
        )

    def save_account(self, account: LinkedInAccount) -> LinkedInAccount:
        self.session.add(account)
        self.session.flush()
        return account

    def get_post(self, user_id: uuid.UUID, post_id: uuid.UUID) -> Post | None:
        return self.session.scalar(
            select(Post)
            .where(Post.id == post_id, Post.user_id == user_id)
            .options(selectinload(Post.images))
        )

    def get_history_by_key(self, idempotency_key: str) -> PublishHistory | None:
        return self.session.scalar(
            select(PublishHistory).where(PublishHistory.idempotency_key == idempotency_key)
        )

    def add_history(self, history: PublishHistory) -> PublishHistory:
        self.session.add(history)
        self.session.flush()
        return history

    def list_history(self, user_id: uuid.UUID) -> list[PublishHistory]:
        return list(
            self.session.scalars(
                select(PublishHistory)
                .join(Post, Post.id == PublishHistory.post_id)
                .where(Post.user_id == user_id)
                .order_by(PublishHistory.started_at.desc())
            )
        )
