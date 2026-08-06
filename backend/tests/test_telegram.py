import uuid

import httpx
import pytest

from app.core.config import Settings
from app.integrations.telegram import APPROVAL_ACTIONS, TelegramClient


def test_approval_keyboard_contains_every_required_action() -> None:
    execution_id = uuid.uuid4()
    keyboard = TelegramClient.approval_keyboard(execution_id)
    callbacks = [
        button["callback_data"]
        for row in keyboard["inline_keyboard"]
        for button in row
    ]

    assert callbacks == [f"wf:{execution_id}:{action}" for _, action in APPROVAL_ACTIONS]


def test_callback_data_round_trips_and_rejects_unknown_actions() -> None:
    execution_id = uuid.uuid4()

    assert TelegramClient.parse_callback_data(f"wf:{execution_id}:approve") == (
        execution_id,
        "approve",
    )
    with pytest.raises(ValueError, match="Invalid Telegram callback data"):
        TelegramClient.parse_callback_data(f"wf:{execution_id}:publish")


def test_telegram_client_sends_approval_without_real_network() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    client = TelegramClient(
        Settings(telegram_bot_token="token"),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    message_id = client.send_approval("123", uuid.uuid4(), "Post content")

    assert message_id == "42"
    assert requests[0].url.path.endswith("/sendMessage")
