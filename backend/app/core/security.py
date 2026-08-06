import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class EncryptionService:
    def __init__(self, settings: Settings) -> None:
        key = (
            settings.encryption_key.encode()
            if settings.encryption_key
            else self._development_key(settings)
        )
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Stored credential cannot be decrypted") from exc

    @staticmethod
    def _development_key(settings: Settings) -> bytes:
        digest = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
        return base64.urlsafe_b64encode(digest)
