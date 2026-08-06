from typing import Any

from pydantic import BaseModel


class TelegramCallbackMessage(BaseModel):
    message_id: int
    chat: dict[str, Any]


class TelegramCallbackQuery(BaseModel):
    id: str
    data: str
    message: TelegramCallbackMessage | None = None


class TelegramUpdate(BaseModel):
    update_id: int
    callback_query: TelegramCallbackQuery | None = None
