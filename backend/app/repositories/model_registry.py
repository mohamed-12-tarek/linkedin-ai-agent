import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LLMModel, UserSettings


class ModelRegistryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: uuid.UUID) -> list[LLMModel]:
        statement = select(LLMModel).where(LLMModel.user_id == user_id).order_by(LLMModel.name)
        return list(self.session.scalars(statement))

    def get_for_user(self, user_id: uuid.UUID, model_id: uuid.UUID) -> LLMModel | None:
        statement = select(LLMModel).where(
            LLMModel.id == model_id,
            LLMModel.user_id == user_id,
        )
        return self.session.scalar(statement)

    def find_available_for_role(self, user_id: uuid.UUID, role_type: str) -> list[LLMModel]:
        statement = (
            select(LLMModel)
            .where(
                LLMModel.user_id == user_id,
                LLMModel.role_type == role_type,
                LLMModel.is_available.is_(True),
            )
            .order_by(LLMModel.name)
        )
        return list(self.session.scalars(statement))

    def get_user_settings(self, user_id: uuid.UUID) -> UserSettings | None:
        return self.session.scalar(select(UserSettings).where(UserSettings.user_id == user_id))

    def add(self, model: LLMModel) -> LLMModel:
        self.session.add(model)
        self.session.flush()
        return model

    def delete(self, model: LLMModel) -> None:
        self.session.delete(model)
