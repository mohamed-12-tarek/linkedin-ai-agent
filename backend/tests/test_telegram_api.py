import uuid

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_telegram_webhook_rejects_invalid_secret_before_processing() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///:memory:",
            telegram_webhook_secret="expected-secret",  # pragma: allowlist secret
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            json={
                "update_id": 1,
                "callback_query": {
                    "id": "callback",
                    "data": f"wf:{uuid.uuid4()}:approve",
                },
            },
        )

    assert response.status_code == 401


def test_telegram_webhook_accepts_non_callback_updates() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///:memory:",
            telegram_webhook_secret="expected-secret",  # pragma: allowlist secret
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "expected-secret"},
            json={"update_id": 2},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
