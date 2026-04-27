

# tests/test_security.py

import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)


# ═════════════════════════════════════════════════════════════════
# PASSWORD HASHING TESTS
# ═════════════════════════════════════════════════════════════════

class TestPasswordHashing:
    """
    Tests for password hashing and verification.

    Why test this?
    If hashing breaks — passwords stored incorrectly
    If verification breaks — nobody can login
    Most critical security component
    """

    def test_hash_password_returns_string(self):
        """
        Basic check — hashing must return a string
        """
        plain = "mypassword123"
        hashed = hash_password(plain)

        assert isinstance(hashed, str)

    def test_hash_password_not_plain_text(self):
        """
        Hashed password must never equal plain password
        If this fails — passwords stored in plain text — critical bug!
        """
        plain = "mypassword123"
        hashed = hash_password(plain)

        assert hashed != plain

    def test_hash_password_starts_with_bcrypt_prefix(self):
        """
        bcrypt hashes always start with $2b$
        This confirms we are using bcrypt correctly
        """
        plain = "mypassword123"
        hashed = hash_password(plain)

        assert hashed.startswith("$2b$")

    def test_same_password_gives_different_hashes(self):
        """
        bcrypt adds random salt each time
        Same password hashed twice gives different results
        This is intentional security feature
        """
        plain = "mypassword123"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)

        # Both are valid but different due to random salt
        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """
        Correct password must verify successfully
        This is the login check
        """
        plain = "mypassword123"
        hashed = hash_password(plain)

        result = verify_password(plain, hashed)

        assert result is True

    def test_verify_password_wrong_password(self):
        """
        Wrong password must fail verification
        Critical security test — wrong password must never pass
        """
        plain = "mypassword123"
        wrong = "wrongpassword"
        hashed = hash_password(plain)

        result = verify_password(wrong, hashed)

        assert result is False

    def test_verify_password_empty_password(self):
        """
        Empty password must fail verification
        Prevents empty password bypass attacks
        """
        plain = "mypassword123"
        hashed = hash_password(plain)

        result = verify_password("", hashed)

        assert result is False

    def test_verify_password_case_sensitive(self):
        """
        Password verification must be case sensitive
        "Password123" and "password123" are different
        """
        plain = "Password123"
        hashed = hash_password(plain)

        result = verify_password("password123", hashed)

        assert result is False


# ═════════════════════════════════════════════════════════════════
# JWT TOKEN TESTS
# ═════════════════════════════════════════════════════════════════

class TestJWTTokens:
    """
    Tests for JWT token creation and decoding.

    Why test this?
    If token creation breaks — users cannot login
    If decoding breaks — users cannot access protected routes
    If expiry breaks — security vulnerability
    """

    def test_create_access_token_returns_string(self):
        """
        Token creation must return a string
        """
        token = create_access_token(data={"sub": "test@example.com"})

        assert isinstance(token, str)

    def test_create_access_token_not_empty(self):
        """
        Token must not be empty string
        """
        token = create_access_token(data={"sub": "test@example.com"})

        assert len(token) > 0

    def test_create_access_token_has_three_parts(self):
        """
        JWT tokens always have three parts separated by dots
        header.payload.signature
        """
        token = create_access_token(data={"sub": "test@example.com"})
        parts = token.split(".")

        assert len(parts) == 3

    def test_decode_access_token_returns_email(self):
        """
        Decoding valid token must return correct email
        This is how protected routes identify current user
        """
        email = "test@example.com"
        token = create_access_token(data={"sub": email})

        decoded_email = decode_access_token(token)

        assert decoded_email == email

    def test_decode_access_token_invalid_token(self):
        """
        Invalid token must return None
        Not raise exception — just return None safely
        """
        fake_token = "this.is.fake"

        result = decode_access_token(fake_token)

        assert result is None

    def test_decode_access_token_empty_string(self):
        """
        Empty token must return None safely
        """
        result = decode_access_token("")

        assert result is None

    def test_decode_access_token_random_string(self):
        """
        Random string as token must return None
        """
        result = decode_access_token("randomstringnotajwt")

        assert result is None

    def test_create_token_with_custom_expiry(self):
        """
        Token with custom expiry must still decode correctly
        """
        email = "test@example.com"
        token = create_access_token(
            data={"sub": email},
            expires_delta=timedelta(minutes=60)
        )

        decoded_email = decode_access_token(token)

        assert decoded_email == email

    def test_expired_token_returns_none(self):
        """
        Expired token must return None
        Critical security test — expired tokens must be rejected
        """
        email = "test@example.com"
        # Create token that expired 1 minute ago
        token = create_access_token(
            data={"sub": email},
            expires_delta=timedelta(minutes=-1)
        )

        result = decode_access_token(token)

        assert result is None

    def test_different_emails_give_different_tokens(self):
        """
        Different emails must produce different tokens
        """
        token1 = create_access_token(data={"sub": "user1@example.com"})
        token2 = create_access_token(data={"sub": "user2@example.com"})

        assert token1 != token2

    def test_tampered_token_returns_none(self):
        """
        Tampered token must be rejected
        If someone modifies token payload — must fail
        This tests JWT signature verification
        """
        email = "test@example.com"
        token = create_access_token(data={"sub": email})

        # Tamper with token by modifying middle part
        parts = token.split(".")
        tampered = parts[0] + ".tamperedpayload." + parts[2]

        result = decode_access_token(tampered)

        assert result is None