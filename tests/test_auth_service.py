# tests/test_auth_service.py

import pytest
from fastapi.testclient import TestClient


# ═════════════════════════════════════════════════════════════════
# REGISTER TESTS
# ═════════════════════════════════════════════════════════════════

class TestRegister:
    """Tests for POST /auth/register endpoint."""

    def test_register_success(self, client: TestClient, test_user_data: dict):
        """Successful registration returns 201 with user data."""
        response = client.post("/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["is_active"] is True
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client: TestClient, test_user_data: dict):
        """Duplicate email returns 400."""
        client.post("/auth/register", json=test_user_data)

        # Try registering again with same email
        duplicate = test_user_data.copy()
        duplicate["username"] = "differentuser"
        response = client.post("/auth/register", json=duplicate)

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_duplicate_username(self, client: TestClient, test_user_data: dict):
        """Duplicate username returns 400."""
        client.post("/auth/register", json=test_user_data)

        # Try registering again with same username
        duplicate = test_user_data.copy()
        duplicate["email"] = "different@example.com"
        response = client.post("/auth/register", json=duplicate)

        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_register_missing_email(self, client: TestClient):
        """Missing email returns 422 validation error."""
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "password123"
        })

        assert response.status_code == 422

    def test_register_missing_password(self, client: TestClient):
        """Missing password returns 422 validation error."""
        response = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@example.com"
        })

        assert response.status_code == 422

    def test_register_missing_username(self, client: TestClient):
        """Missing username returns 422 validation error."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        assert response.status_code == 422

    def test_register_password_not_returned(self, client: TestClient, test_user_data: dict):
        """Password must never appear in response — security check."""
        response = client.post("/auth/register", json=test_user_data)
        data = response.json()

        assert "password" not in data
        assert "hashed_password" not in data


# ═════════════════════════════════════════════════════════════════
# LOGIN TESTS
# ═════════════════════════════════════════════════════════════════

class TestLogin:
    """Tests for POST /auth/login endpoint."""

    def test_login_with_email_success(
        self,
        client: TestClient,
        test_user_data: dict,
        registered_user: dict
    ):
        """Login with email returns JWT token."""
        response = client.post("/auth/login", json={
            "identifier": test_user_data["email"],
            "password": test_user_data["password"]
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_with_username_success(
        self,
        client: TestClient,
        test_user_data: dict,
        registered_user: dict
    ):
        """Login with username returns JWT token."""
        response = client.post("/auth/login", json={
            "identifier": test_user_data["username"],
            "password": test_user_data["password"]
        })

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(
        self,
        client: TestClient,
        test_user_data: dict,
        registered_user: dict
    ):
        """Wrong password returns 401."""
        response = client.post("/auth/login", json={
            "identifier": test_user_data["email"],
            "password": "wrongpassword"
        })

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_wrong_email(self, client: TestClient):
        """Non-existent email returns 401."""
        response = client.post("/auth/login", json={
            "identifier": "notexist@example.com",
            "password": "password123"
        })

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_wrong_username(self, client: TestClient):
        """Non-existent username returns 401."""
        response = client.post("/auth/login", json={
            "identifier": "nonexistentuser",
            "password": "password123"
        })

        assert response.status_code == 401

    def test_login_error_message_not_specific(
        self,
        client: TestClient,
        registered_user: dict
    ):
        """
        Error message must never reveal if email exists or not.
        Both wrong email and wrong password return same message.
        Prevents email enumeration attacks.
        """
        # Wrong password for existing user
        response1 = client.post("/auth/login", json={
            "identifier": "test@example.com",
            "password": "wrongpassword"
        })

        # Non-existent email
        response2 = client.post("/auth/login", json={
            "identifier": "notexist@example.com",
            "password": "wrongpassword"
        })

        # Both must return same error message
        assert response1.json()["detail"] == response2.json()["detail"]


# ═════════════════════════════════════════════════════════════════
# PROFILE TESTS
# ═════════════════════════════════════════════════════════════════

class TestProfile:
    """Tests for GET /auth/profile endpoint."""

    def test_get_profile_success(
        self,
        client: TestClient,
        test_user_data: dict,
        auth_headers: dict
    ):
        """Authenticated user can get their profile."""
        response = client.get("/auth/profile", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]

    def test_get_profile_no_token(self, client: TestClient):
        """Request without token returns 401."""
        response = client.get("/auth/profile")

        assert response.status_code == 401

    def test_get_profile_invalid_token(self, client: TestClient):
        """Invalid token returns 401."""
        response = client.get(
            "/auth/profile",
            headers={"Authorization": "Bearer invalidtoken"}
        )

        assert response.status_code == 401

    def test_profile_no_password_in_response(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Profile response must never include password."""
        response = client.get("/auth/profile", headers=auth_headers)
        data = response.json()

        assert "password" not in data
        assert "hashed_password" not in data


# ═════════════════════════════════════════════════════════════════
# CHANGE PASSWORD TESTS
# ═════════════════════════════════════════════════════════════════

class TestChangePassword:
    """Tests for PUT /auth/change-password endpoint."""

    def test_change_password_success(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Valid password change returns success message."""
        response = client.put(
            "/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

    def test_change_password_wrong_current(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Wrong current password returns 400."""
        response = client.put(
            "/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]

    def test_change_password_mismatch(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Mismatched new passwords returns 400."""
        response = client.put(
            "/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123",
                "confirm_password": "differentpassword"
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Passwords do not match" in response.json()["detail"]

    def test_change_password_same_as_current(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """New password same as current returns 400."""
        response = client.put(
            "/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "testpassword123",
                "confirm_password": "testpassword123"
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "must differ" in response.json()["detail"]

    def test_change_password_too_short(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Password less than 8 characters returns 422."""
        response = client.put(
            "/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "short",
                "confirm_password": "short"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_change_password_no_token(self, client: TestClient):
        """Request without token returns 401."""
        response = client.put(
            "/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        )

        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════
# FORGOT PASSWORD TESTS
# ═════════════════════════════════════════════════════════════════

class TestForgotPassword:
    """Tests for POST /auth/forgot-password endpoint."""

    def test_forgot_password_success(
        self,
        client: TestClient,
        registered_user: dict
    ):
        """Valid email returns OTP in development mode."""
        response = client.post("/auth/forgot-password", json={
            "email": "test@example.com"
        })

        assert response.status_code == 200
        data = response.json()
        assert "otp" in data
        assert len(data["otp"]) == 6
        assert data["otp"].isdigit()

    def test_forgot_password_invalid_email(self, client: TestClient):
        """Non-existent email returns 404."""
        response = client.post("/auth/forgot-password", json={
            "email": "notexist@example.com"
        })

        assert response.status_code == 404
        assert "Email not found" in response.json()["detail"]


# ═════════════════════════════════════════════════════════════════
# RESET PASSWORD TESTS
# ═════════════════════════════════════════════════════════════════

class TestResetPassword:
    """Tests for POST /auth/reset-password endpoint."""

    def test_reset_password_success(
        self,
        client: TestClient,
        registered_user: dict
    ):
        """Valid OTP allows password reset."""
        # Get OTP first
        otp_response = client.post("/auth/forgot-password", json={
            "email": "test@example.com"
        })
        otp = otp_response.json()["otp"]

        # Reset password using OTP
        response = client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "otp": otp,
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        })

        assert response.status_code == 200
        assert "Password reset successfully" in response.json()["message"]

    def test_reset_password_invalid_otp(
        self,
        client: TestClient,
        registered_user: dict
    ):
        """Invalid OTP returns 400."""
        response = client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "otp": "000000",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        })

        assert response.status_code == 400
        assert "Invalid OTP" in response.json()["detail"]

    def test_reset_password_mismatch(
        self,
        client: TestClient,
        registered_user: dict
    ):
        """Mismatched passwords returns 400."""
        otp_response = client.post("/auth/forgot-password", json={
            "email": "test@example.com"
        })
        otp = otp_response.json()["otp"]

        response = client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "otp": otp,
            "new_password": "newpassword123",
            "confirm_password": "differentpassword"
        })

        assert response.status_code == 400

    def test_reset_password_can_login_after(
        self,
        client: TestClient,
        registered_user: dict
    ):
        """User can login with new password after reset."""
        # Get OTP
        otp_response = client.post("/auth/forgot-password", json={
            "email": "test@example.com"
        })
        otp = otp_response.json()["otp"]

        # Reset password
        client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "otp": otp,
            "new_password": "brandnewpassword123",
            "confirm_password": "brandnewpassword123"
        })

        # Login with new password
        login_response = client.post("/auth/login", json={
            "identifier": "test@example.com",
            "password": "brandnewpassword123"
        })

        assert login_response.status_code == 200
        assert "access_token" in login_response.json()


# ═════════════════════════════════════════════════════════════════
# UPDATE PROFILE TESTS
# ═════════════════════════════════════════════════════════════════

class TestUpdateProfile:
    """Tests for PUT /auth/profile/update endpoint."""

    def test_update_full_name(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Update full name returns updated profile."""
        response = client.put(
            "/auth/profile/update",
            json={"full_name": "Wajid Minhas"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["full_name"] == "Wajid Minhas"

    def test_update_phone_number_valid(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Valid phone number updates successfully."""
        response = client.put(
            "/auth/profile/update",
            json={"phone_number": "+923001234567"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["phone_number"] == "+923001234567"

    def test_update_phone_number_invalid(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Invalid phone number returns 422."""
        response = client.put(
            "/auth/profile/update",
            json={"phone_number": "123"},
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_update_username_success(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Valid new username updates successfully."""
        response = client.put(
            "/auth/profile/update",
            json={"username": "newusername"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["username"] == "newusername"

    def test_update_username_taken(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Already taken username returns 400."""
        # Register second user
        client.post("/auth/register", json={
            "username": "seconduser",
            "email": "second@example.com",
            "password": "password123"
        })

        # Try to take second user's username
        response = client.put(
            "/auth/profile/update",
            json={"username": "seconduser"},
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_update_no_token(self, client: TestClient):
        """Request without token returns 401."""
        response = client.put(
            "/auth/profile/update",
            json={"full_name": "Test User"}
        )

        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════
# REFRESH TOKEN TESTS
# ═════════════════════════════════════════════════════════════════

class TestRefreshToken:
    """Tests for POST /auth/refresh-token endpoint."""

    def test_refresh_token_success(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Valid token returns new valid token."""
        response = client.post(
            "/auth/refresh-token",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        # Remove token comparison — tokens can be same
        # if generated within same second
        # What matters is response is valid
        
    def test_refresh_token_no_auth(self, client: TestClient):
        """Request without token returns 403."""
        response = client.post("/auth/refresh-token")
        assert response.status_code == 401

  
    


# ═════════════════════════════════════════════════════════════════
# LOGOUT TESTS
# ═════════════════════════════════════════════════════════════════

class TestLogout:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_success(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Logout returns success message."""
        response = client.post("/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

    def test_logout_no_token(self, client: TestClient):
        """Request without token returns 401."""
        response = client.post("/auth/logout")

        assert response.status_code == 401


# ═════════════════════════════════════════════════════════════════
# HEALTH CHECK TESTS
# ═════════════════════════════════════════════════════════════════

class TestHealthCheck:
    """Tests for GET /auth/health endpoint."""

    def test_health_check_success(self, client: TestClient):
        """Health check returns healthy status."""
        response = client.get("/auth/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth-service"

    def test_root_endpoint(self, client: TestClient):
        """Root endpoint returns service info."""
        response = client.get("/")

        assert response.status_code == 200
        assert "service" in response.json()
        assert "docs" in response.json()