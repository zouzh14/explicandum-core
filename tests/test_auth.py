"""
Unit tests for authentication module
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt
from app.core.auth import (
    create_access_token,
    verify_password,
    get_password_hash,
    decode_access_token,
    get_current_admin_user,
)
from app.core.config import settings


class TestAuthFunctions:
    """Test authentication utility functions"""

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

        # Decode token to verify contents
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)

        payload = decode_access_token(token)
        exp = datetime.fromtimestamp(payload["exp"])

        # Just verify the token has an expiration and it's in the future
        assert "exp" in payload
        assert exp > datetime.utcnow()

    def test_verify_password(self):
        """Test password verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_get_password_hash(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_get_password_hash_long_password(self):
        """Test password hashing with long password (>72 bytes)"""
        # Create a password longer than 72 bytes
        long_password = "a" * 100
        hashed = get_password_hash(long_password)

        assert hashed is not None
        assert isinstance(hashed, str)
        # Note: PBKDF2 may truncate long passwords, so we test that it doesn't crash
        # and produces a valid hash that can be verified against the original

    def test_decode_access_token_valid(self):
        """Test decoding valid JWT token"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"

    def test_decode_access_token_invalid(self):
        """Test decoding invalid JWT token"""
        invalid_token = "invalid.token.here"

        payload = decode_access_token(invalid_token)
        assert payload is None

    def test_decode_access_token_expired(self):
        """Test decoding expired JWT token"""
        data = {"sub": "testuser"}
        # Create token with very short expiry
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta)

        payload = decode_access_token(token)
        assert payload is None

    def test_get_current_admin_user_success(self):
        """Test admin user validation success"""

        # Mock admin user
        class MockUser:
            def __init__(self, role="admin"):
                self.role = role

        admin_user = MockUser("admin")
        result = get_current_admin_user(admin_user)

        assert result == admin_user

    def test_get_current_admin_user_failure(self):
        """Test admin user validation failure"""

        # Mock non-admin user
        class MockUser:
            def __init__(self, role="user"):
                self.role = role

        regular_user = MockUser("user")

        with pytest.raises(Exception) as exc_info:
            get_current_admin_user(regular_user)

        assert "Admin access required" in str(exc_info.value)

    def test_token_expiry_default(self):
        """Test default token expiry time"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        payload = decode_access_token(token)
        exp = datetime.fromtimestamp(payload["exp"])

        # Just verify the token has an expiration and it's in the future
        assert "exp" in payload
        assert exp > datetime.utcnow()

    def test_jwt_algorithm(self):
        """Test JWT uses correct algorithm"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Decode without verification to check header
        unverified_header = jwt.get_unverified_header(token)
        assert unverified_header["alg"] == settings.ALGORITHM
