import base64
import mimetypes
import urllib.parse
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class ImageGenerationResult:
    provider: str
    model: str
    content: bytes
    content_type: str


class ImageProvider(Protocol):
    name: str

    def generate(self, prompt: str) -> ImageGenerationResult: ...


class ImageProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ImageProvider] = {}

    def register(self, provider: ImageProvider, *, replace: bool = False) -> None:
        if provider.name in self._providers and not replace:
            raise ValueError(f"Image provider '{provider.name}' is already registered")
        self._providers[provider.name] = provider

    def get(self, name: str) -> ImageProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ValueError(f"Unknown image provider '{name}'")
        return provider

    def generate_with_fallback(
        self, prompt: str, provider_order: list[str]
    ) -> ImageGenerationResult:
        errors: list[str] = []
        for name in provider_order:
            provider = self._providers.get(name)
            if provider is None:
                continue
            try:
                return provider.generate(prompt)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        detail = "; ".join(errors) if errors else "no configured image providers"
        raise RuntimeError(f"Image generation failed: {detail}")

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))


class PollinationsImageProvider:
    name = "pollinations"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=90, follow_redirects=True)

    def generate(self, prompt: str) -> ImageGenerationResult:
        encoded = urllib.parse.quote(prompt, safe="")
        url = (
            f"{self.settings.pollinations_base_url.rstrip('/')}/prompt/{encoded}"
            f"?model={urllib.parse.quote(self.settings.pollinations_model)}&nologo=true"
        )
        response = self.client.get(url)
        response.raise_for_status()
        return ImageGenerationResult(
            provider=self.name,
            model=self.settings.pollinations_model,
            content=response.content,
            content_type=response.headers.get("content-type", "image/jpeg").split(";", 1)[0],
        )


class HuggingFaceImageProvider:
    name = "huggingface"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=120)

    def generate(self, prompt: str) -> ImageGenerationResult:
        if not self.settings.huggingface_api_token:
            raise RuntimeError("HUGGINGFACE_API_TOKEN is not configured")
        response = self.client.post(
            f"https://api-inference.huggingface.co/models/{self.settings.huggingface_image_model}",
            headers={"Authorization": f"Bearer {self.settings.huggingface_api_token}"},
            json={"inputs": prompt},
        )
        response.raise_for_status()
        return ImageGenerationResult(
            provider=self.name,
            model=self.settings.huggingface_image_model,
            content=response.content,
            content_type=response.headers.get("content-type", "image/jpeg").split(";", 1)[0],
        )


class OpenAIImageProvider:
    name = "openai"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=120, follow_redirects=True)

    def generate(self, prompt: str) -> ImageGenerationResult:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        response = self.client.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json={
                "model": self.settings.openai_image_model,
                "prompt": prompt,
                "size": "1024x1024",
            },
        )
        response.raise_for_status()
        item = response.json()["data"][0]
        if item.get("b64_json"):
            content = base64.b64decode(item["b64_json"])
            content_type = "image/png"
        else:
            image_response = self.client.get(item["url"])
            image_response.raise_for_status()
            content = image_response.content
            content_type = image_response.headers.get("content-type", "image/png").split(";", 1)[0]
        return ImageGenerationResult(
            provider=self.name,
            model=self.settings.openai_image_model,
            content=content,
            content_type=content_type,
        )


class LocalImageStorage:
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.local_storage_path)
        self.maximum_bytes = settings.max_image_upload_mb * 1024 * 1024

    def stage_upload(self, content: bytes, content_type: str) -> str:
        self._validate(content, content_type)
        upload_id = uuid.uuid4().hex
        path = self.root / "uploads" / f"{upload_id}{self._extension(content_type)}"
        self._write(path, content)
        return upload_id

    def resolve_upload(self, upload_id: str) -> Path:
        if not upload_id.isalnum():
            raise ValueError("Invalid upload ID")
        matches = list((self.root / "uploads").glob(f"{upload_id}.*"))
        if len(matches) != 1:
            raise FileNotFoundError("Uploaded image not found")
        return matches[0]

    def persist_for_post(
        self, post_id: uuid.UUID, content: bytes, content_type: str, prefix: str
    ) -> Path:
        self._validate(content, content_type)
        path = self.root / "images" / str(post_id) / (
            f"{prefix}-{uuid.uuid4().hex}{self._extension(content_type)}"
        )
        self._write(path, content)
        return path

    def inspect(self, path: Path) -> tuple[int, int, str]:
        from PIL import Image as PillowImage

        with PillowImage.open(path) as image:
            image.verify()
        with PillowImage.open(path) as image:
            return image.width, image.height, image.format or "unknown"

    def content_type_for(self, path: Path) -> str:
        return mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    def _validate(self, content: bytes, content_type: str) -> None:
        normalized = content_type.split(";", 1)[0].lower()
        if normalized not in self.ALLOWED_TYPES:
            raise ValueError("Only JPEG, PNG, and WebP images are supported")
        if not content or len(content) > self.maximum_bytes:
            raise ValueError("Image file is empty or exceeds the configured size limit")

    @staticmethod
    def _extension(content_type: str) -> str:
        return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[
            content_type.split(";", 1)[0].lower()
        ]

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def build_image_provider_registry(settings: Settings) -> ImageProviderRegistry:
    registry = ImageProviderRegistry()
    registry.register(PollinationsImageProvider(settings))
    registry.register(HuggingFaceImageProvider(settings))
    registry.register(OpenAIImageProvider(settings))
    return registry
