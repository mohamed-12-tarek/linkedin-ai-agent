from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_check() -> None:
    app = create_app(Settings(database_url="sqlite:///:memory:"))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
