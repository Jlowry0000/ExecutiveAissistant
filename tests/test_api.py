import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestFastAPIEndpoints:
    @pytest.fixture
    def mock_env(self):
        with patch.dict("os.environ", {
            "NOCODB_URL": "http://localhost:8080",
            "API_KEY": "test-api-key",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "exec_assistant",
            "POSTGRES_USER": "exec_assistant",
            "POSTGRES_PASSWORD": "test",
        }):
            yield

    @pytest.fixture
    def mock_nocodb(self):
        with patch("api.app.NocoDBClient") as MockClient:
            instance = AsyncMock()
            MockClient.return_value = instance
            yield instance

    def test_health_endpoint(self, mock_env):
        from api.app import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_get_context_unauthorized(self, mock_env, mock_nocodb):
        from api.app import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/context")
        assert response.status_code == 422

    def test_get_context_wrong_api_key(self, mock_env, mock_nocodb):
        from api.app import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/context", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401

    def test_get_flagged_emails_authorized(self, mock_env, mock_nocodb):
        from api.app import app
        from fastapi.testclient import TestClient
        mock_nocodb.get_rows = AsyncMock(return_value={
            "list": [
                {
                    "Id": "123",
                    "sender": "test@example.com",
                    "sender_name": "Test User",
                    "subject": "Test",
                    "summary": "Summary",
                    "flag_reason": "Important",
                    "suggested_action": "Reply",
                    "draft_response": "Hi,",
                    "is_flagged": True,
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ]
        })
        client = TestClient(app)
        response = client.get(
            "/correspondence/flagged",
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["data"][0]["sender"] == "test@example.com"

    def test_digest_trigger(self, mock_env, mock_nocodb):
        from api.app import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post(
            "/digest/trigger",
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"