import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_allows_local_secrets() -> None:
    settings = Settings(app_env="development")

    assert settings.app_env == "development"


def test_production_rejects_local_secrets() -> None:
    with pytest.raises(ValidationError, match="Secure values are required for"):
        Settings(app_env="production")


def test_production_accepts_generated_secrets() -> None:
    from cryptography.fernet import Fernet

    settings = Settings(
        app_env="production",
        jwt_secret_key="a" * 48,
        encryption_key=Fernet.generate_key().decode(),
    )

    assert settings.app_env == "production"
