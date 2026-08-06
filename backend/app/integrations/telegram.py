import uuid
from typing import Protocol

import httpx

from app.core.config import Settings

APPROVAL_ACTIONS = (
    ("Approve", "approve"),
    ("Reject", "reject"),
    ("Rewrite", "rewrite"),
    ("Regenerate Hook", "regenerate_hook"),
    ("Regenerate CTA", "regenerate_cta"),
    ("Shorter", "shorter"),
    ("Longer", "longer"),
    ("Professional", "professional"),
    ("Friendly", "friendly"),
    ("Technical", "technical"),
    ("Translate", "translate"),
)


class TelegramGateway(Protocol):
    def send_approval(
        self,
        chat_id: str,
        execution_id: uuid.UUID,
        content: str,
        image_path: str | None = None,
    ) -> str: ...

    def answer_callback(self, callback_query_id: str, text: str) -> None: ...


class TelegramClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=10)

    def send_approval(
        self,
        chat_id: str,
        execution_id: uuid.UUID,
        content: str,
        image_path: str | None = None,
    ) -> str:
        if not self.settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        if image_path:
            import json
            from pathlib import Path

            path = Path(image_path)
            with path.open("rb") as image_file:
                response = self.client.post(
                    self._url("sendPhoto"),
                    data={
                        "chat_id": chat_id,
                        "caption": self._caption_text(content),
                        "reply_markup": json.dumps(self.approval_keyboard(execution_id)),
                    },
                    files={"photo": (path.name, image_file, "application/octet-stream")},
                )
        else:
            response = self.client.post(
                self._url("sendMessage"),
                json={
                    "chat_id": chat_id,
                    "text": self._message_text(content),
                    "reply_markup": self.approval_keyboard(execution_id),
                    "disable_web_page_preview": True,
                },
            )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description", "Telegram sendMessage failed"))
        return str(payload["result"]["message_id"])

    def answer_callback(self, callback_query_id: str, text: str) -> None:
        if not self.settings.telegram_bot_token:
            return
        response = self.client.post(
            self._url("answerCallbackQuery"),
            json={"callback_query_id": callback_query_id, "text": text[:200]},
        )
        response.raise_for_status()

    @staticmethod
    def approval_keyboard(execution_id: uuid.UUID) -> dict:
        rows = []
        actions = list(APPROVAL_ACTIONS)
        for index in range(0, len(actions), 2):
            rows.append(
                [
                    {
                        "text": label,
                        "callback_data": f"wf:{execution_id}:{action}",
                    }
                    for label, action in actions[index : index + 2]
                ]
            )
        return {"inline_keyboard": rows}

    @staticmethod
    def parse_callback_data(value: str) -> tuple[uuid.UUID, str]:
        prefix, execution_id, action = value.split(":", 2)
        if prefix != "wf" or action not in {item[1] for item in APPROVAL_ACTIONS}:
            raise ValueError("Invalid Telegram callback data")
        return uuid.UUID(execution_id), action

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/{method}"

    @staticmethod
    def _message_text(content: str) -> str:
        header = "LinkedIn post awaiting approval:\n\n"
        maximum = 4096 - len(header)
        return header + content[:maximum]

    @staticmethod
    def _caption_text(content: str) -> str:
        header = "LinkedIn post awaiting approval:\n\n"
        maximum = 1024 - len(header)
        return header + content[:maximum]
