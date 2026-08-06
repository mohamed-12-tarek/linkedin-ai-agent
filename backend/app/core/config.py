from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
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
    postgres_db: str = "linkedin_agent"
    postgres_user: str = "linkedin_agent"
    postgres_password: str = "linkedin_agent_local_password"
    postgres_port: int = 5432
    storage_backend: str = "local"
    local_storage_path: str = "./storage"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "linkedin-agent"

    jwt_secret_key: str = "local-development-secret-change-before-deployment"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30
    encryption_key: str = ""

    groq_api_key: str = ""
    google_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_name: str = "AI LinkedIn Content Agent"
    openrouter_site_url: str = "http://localhost:8501"

    default_writer_model: str = ""
    default_reviewer_model: str = ""
    default_judge_model: str = ""
    default_translation_model: str = ""

    pollinations_base_url: str = "https://image.pollinations.ai"
    pollinations_model: str = "flux"
    huggingface_api_token: str = ""
    huggingface_image_model: str = "black-forest-labs/FLUX.1-schnell"
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    image_provider_order: str = "pollinations,huggingface,openai"
    max_image_upload_mb: int = 10

    @computed_field
    @property
    def image_provider_names(self) -> list[str]:
        return [name.strip() for name in self.image_provider_order.split(",") if name.strip()]

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/api/v1/linkedin/oauth/callback"
    linkedin_scopes: str = "openid,profile,w_member_social"

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "us"

    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"

    @computed_field
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_deployment_secrets(self) -> "Settings":
        if self.app_env.lower() not in {"production", "staging"}:
            return self

        invalid_secrets = {
            "JWT_SECRET_KEY": self.jwt_secret_key
            == "local-development-secret-change-before-deployment"
            or len(self.jwt_secret_key) < 32,
            "ENCRYPTION_KEY": not self.encryption_key
            or self.encryption_key == "replace-with-a-valid-fernet-key",
        }
        invalid_names = [name for name, invalid in invalid_secrets.items() if invalid]
        if invalid_names:
            names = ", ".join(invalid_names)
            raise ValueError(f"Secure values are required for {names} in {self.app_env}")

        try:
            Fernet(self.encryption_key.encode())
        except (TypeError, ValueError) as exc:
            raise ValueError("ENCRYPTION_KEY must be a valid Fernet key") from exc

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
