import json
import uuid

from app.core.security import EncryptionService
from app.models import LLMModel
from app.repositories.model_registry import ModelRegistryRepository
from app.schemas.models import ModelCreate, ModelRead, ModelUpdate


class ModelNotFoundError(Exception):
    pass


class ModelRoleNotConfiguredError(Exception):
    pass


class ModelRegistryService:
    def __init__(
        self,
        repository: ModelRegistryRepository,
        encryption: EncryptionService,
    ) -> None:
        self.repository = repository
        self.encryption = encryption

    def list_models(self, user_id: uuid.UUID) -> list[ModelRead]:
        return [self._to_read(model) for model in self.repository.list_for_user(user_id)]

    def create_model(self, user_id: uuid.UUID, data: ModelCreate) -> ModelRead:
        values = data.model_dump(exclude={"api_key"})
        model = LLMModel(
            user_id=user_id,
            api_key_encrypted=self.encryption.encrypt(data.api_key) if data.api_key else None,
            **values,
        )
        try:
            self.repository.add(model)
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise
        return self._to_read(model)

    def update_model(
        self,
        user_id: uuid.UUID,
        model_id: uuid.UUID,
        data: ModelUpdate,
    ) -> ModelRead:
        model = self._get_model(user_id, model_id)
        values = data.model_dump(
            exclude_unset=True,
            exclude={"api_key", "clear_api_key"},
        )
        for field, value in values.items():
            setattr(model, field, value)
        if data.api_key is not None:
            model.api_key_encrypted = self.encryption.encrypt(data.api_key)
        elif data.clear_api_key:
            model.api_key_encrypted = None
        try:
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise
        return self._to_read(model)

    def delete_model(self, user_id: uuid.UUID, model_id: uuid.UUID) -> None:
        model = self._get_model(user_id, model_id)
        try:
            self.repository.delete(model)
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise

    def resolve_model(self, user_id: uuid.UUID, role_type: str) -> LLMModel:
        models = self.repository.find_available_for_role(user_id, role_type)
        if not models:
            raise ModelRoleNotConfiguredError(
                f"No available model configured for role '{role_type}'"
            )

        settings = self.repository.get_user_settings(user_id)
        defaults = self._parse_defaults(settings.default_models_json if settings else None)
        preferred_id = defaults.get(role_type)
        if preferred_id:
            preferred = next((model for model in models if str(model.id) == preferred_id), None)
            if preferred is not None:
                return preferred
        return models[0]

    def decrypt_api_key(self, model: LLMModel) -> str | None:
        if model.api_key_encrypted is None:
            return None
        return self.encryption.decrypt(model.api_key_encrypted)

    def _get_model(self, user_id: uuid.UUID, model_id: uuid.UUID) -> LLMModel:
        model = self.repository.get_for_user(user_id, model_id)
        if model is None:
            raise ModelNotFoundError
        return model

    @staticmethod
    def _parse_defaults(raw_value: str | None) -> dict[str, str]:
        if not raw_value:
            return {}
        try:
            parsed = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _to_read(model: LLMModel) -> ModelRead:
        return ModelRead.model_validate(
            {
                **{
                    field: getattr(model, field)
                    for field in ModelRead.model_fields
                    if field != "has_api_key"
                },
                "has_api_key": model.api_key_encrypted is not None,
            }
        )
