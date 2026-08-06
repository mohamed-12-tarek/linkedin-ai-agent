import uuid

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import get_current_user_id
from app.main import create_app


class FakePostService:
    def list_posts(self, user_id):
        return []

    def generate(self, user_id, data):
        raise AssertionError("Endpoint test should use the overridden service")


def test_post_routes_are_registered_and_require_tenant_identity() -> None:
    app = create_app(Settings(database_url="sqlite:///:memory:"))

    from app.api.posts import get_post_service

    app.dependency_overrides[get_post_service] = lambda: FakePostService()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/posts/generate",
            json={
                "topic": "Testing",
                "description": "A test",
                "objective": "educate",
                "audience": "engineers",
            },
        )

    assert response.status_code == 422


def test_post_list_endpoint_uses_injected_service() -> None:
    app = create_app(Settings(database_url="sqlite:///:memory:"))
    user_id = uuid.uuid4()

    def override_service() -> FakePostService:
        return FakePostService()

    from app.api.posts import get_post_service

    app.dependency_overrides[get_post_service] = override_service
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/posts",
            headers={"X-User-ID": str(user_id)},
        )

    assert response.status_code == 200
    assert response.json() == []
