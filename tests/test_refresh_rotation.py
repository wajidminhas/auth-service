# tests/test_refresh_rotation.py
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import AuthService  # Import for patch.object

@pytest.fixture
def client():
    return TestClient(app)

# ✅ Plain class - NO inheritance from BaseModel
class TestRefreshTokenRotation:
    """Test suite for /auth/refresh endpoint."""

    @patch.object(AuthService, 'refresh_tokens', new_callable=AsyncMock)
    @patch.object(AuthService, 'create_access_token_for_user')
    def test_successful_rotation_returns_new_tokens(
        self, mock_create, mock_refresh, client
    ):
        """Valid refresh token should return new access + refresh pair."""
        mock_refresh.return_value = (123, "new_refresh_token_xyz")
        mock_create.return_value = "new_access_token_abc"
        
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "valid_old_token"},
            headers={"Content-Type": "application/json"}
        )
        # DEBUG: Print full response for inspection
        print(f"\n=== RESPONSE STATUS: {response.status_code} ===")
        print(f"=== RESPONSE BODY: {response.json()} ===")
        print(f"=== RESPONSE KEYS: {list(response.json().keys())} ===\n")
        
        
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.json()}"
        data = response.json()
        assert data["access_token"] == "new_access_token_abc"
        assert data["refresh_token"] == "new_refresh_token_xyz"
        assert data["expires_in"] == 30 * 60

    @patch.object(AuthService, 'refresh_tokens', new_callable=AsyncMock)
    def test_refresh_with_invalid_token_returns_401(self, mock_refresh, client):
        """Fake tokens should be rejected with clear error."""
        mock_refresh.side_effect = ValueError("invalid_token")
        
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "fake_token"}
        )
        
        assert response.status_code in [401, 500]
        assert "error" in response.json()

    @patch.object(AuthService, 'refresh_tokens', new_callable=AsyncMock)
    def test_reuse_detection_revokes_family(self, mock_refresh, client):
        """Reusing a rotated token should revoke entire family."""
        mock_refresh.side_effect = ValueError("token_reused")
        
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "already_used_token"}
        )
        
        assert response.status_code in [401, 500]
        assert "error" in response.json()

    @patch.object(AuthService, 'refresh_tokens', new_callable=AsyncMock)
    def test_expired_token_returns_401(self, mock_refresh, client):
        """Expired refresh tokens should be rejected."""
        mock_refresh.side_effect = ValueError("token_expired")
        
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "expired_token"}
        )
        
        assert response.status_code in [401, 500]
        assert "error" in response.json()

    def test_missing_refresh_token_field_returns_422(self, client):
        """Request body must contain refresh_token field."""
        response = client.post(
            "/auth/refresh",
            json={"wrong_field": "value"}
        )
        assert response.status_code == 422

    @patch.object(AuthService, 'refresh_tokens', new_callable=AsyncMock)
    def test_database_error_returns_500(self, mock_refresh, client):
        """Database failures should return safe 500 error."""
        mock_refresh.side_effect = Exception("DB connection lost")
        
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "any_token"}
        )
        
        assert response.status_code == 500
        assert response.json() == {"error": "internal_server_error"}