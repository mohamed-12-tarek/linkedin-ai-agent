import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_allows_local_secrets() -> None:
    settings = Settings(app_env="development")

    assert settings.app_env == "development"


def test_production_rejects_local_secrets() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY, ENCRYPTION_KEY"):
        Settings(app_env="production")
