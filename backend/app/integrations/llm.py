import uuid
from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.services.model_registry import ModelRegistryService


class ChatModelFactory(Protocol):
    def create_for_role(self, user_id: uuid.UUID, role_type: str) -> BaseChatModel: ...

    def metadata_for_role(self, user_id: uuid.UUID, role_type: str) -> dict: ...


class LangChainChatModelFactory:
    def __init__(self, registry: ModelRegistryService, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings

    def create_for_role(self, user_id: uuid.UUID, role_type: str) -> BaseChatModel:
        model = self.registry.resolve_model(user_id, role_type)
        api_key = self.registry.decrypt_api_key(model) or self._provider_api_key(model.provider)
        if not api_key:
            raise ValueError(f"No API key configured for provider '{model.provider}'")

        common = {
            "model": model.name,
            "temperature": model.temperature if model.temperature is not None else 0.7,
            "max_tokens": model.max_tokens,
        }
        if model.provider == "groq":
            return ChatGroq(api_key=api_key, **common)
        if model.provider == "gemini":
            return ChatGoogleGenerativeAI(google_api_key=api_key, **common)
        if model.provider == "openrouter":
            return ChatOpenAI(
                api_key=api_key,
                base_url=model.base_url or self.settings.openrouter_base_url,
                default_headers={
                    "HTTP-Referer": self.settings.openrouter_site_url,
                    "X-Title": self.settings.openrouter_app_name,
                },
                **common,
            )
        raise ValueError(f"Unsupported provider '{model.provider}'")

    def metadata_for_role(self, user_id: uuid.UUID, role_type: str) -> dict:
        model = self.registry.resolve_model(user_id, role_type)
        return {
            "provider": model.provider,
            "model_name": model.name,
            "cost_per_1k": model.cost_per_1k or 0,
        }

    def _provider_api_key(self, provider: str) -> str:
        return {
            "groq": self.settings.groq_api_key,
            "gemini": self.settings.google_api_key,
            "openrouter": self.settings.openrouter_api_key,
        }.get(provider, "")
