from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI LinkedIn Content Agent"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:8501"
    cors_origins: str = "http://localhost:8501"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+psycopg://linkedin_agent:linkedin_agent_local_password@localhost:5432/"
        "linkedin_agent"
    )
    storage_backend: str = "local"
    local_storage_path: str = "./storage"

    jwt_secret_key: str = "local-development-secret-change-before-deployment"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30
    encryption_key: str = ""

    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"

    @computed_field
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
