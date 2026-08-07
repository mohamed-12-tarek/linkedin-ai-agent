import uuid

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import Settings
from app.core.dependencies import get_current_user_id
from app.main import create_app


def test_linkedin_oauth_start_returns_signed_expiring_state() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        linkedin_client_id="client-id",
        linkedin_client_secret="client-secret",  # pragma: allowlist secret
        linkedin_redirect_uri="http://localhost/callback",
    )
    app = create_app(settings)
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    with TestClient(app) as client:
        response = client.get("/api/v1/linkedin/oauth/start")

    assert response.status_code == 200
    authorization_url = response.json()["authorization_url"]
    state = authorization_url.split("state=", 1)[1].split("&", 1)[0]
    from urllib.parse import unquote

    claims = jwt.decode(
        unquote(state),
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert claims["sub"] == str(user_id)
    assert claims["purpose"] == "linkedin_oauth"
    assert "exp" in claims
