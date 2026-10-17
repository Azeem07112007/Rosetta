"""Unit tests for JWT verification and security module."""
import uuid
from datetime import datetime, timezone, timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.core.security import verify_jwt

# Use the same secret as conftest
TEST_JWT_SECRET = "test-jwt-secret-for-rosetta-unit-tests"


def _make_credentials(token: str):
    """Create a mock HTTPAuthorizationCredentials."""
    class Creds:
        credentials = token
    return Creds()


class TestVerifyJwt:
    """Tests for the verify_jwt dependency."""

    @pytest.fixture(autouse=True)
    def _patch_settings(self, monkeypatch):
        """Patch the JWT secret for all tests in this class."""
        monkeypatch.setattr("app.core.security.settings.SUPABASE_JWT_SECRET", TEST_JWT_SECRET)

    def test_valid_token_returns_user_id(self):
        """A valid, non-expired token with 'sub' should return the user ID."""
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        creds = _make_credentials(token)

        result = verify_jwt(creds)
        assert result == user_id

    def test_expired_token_raises_401(self):
        """An expired token should raise HTTPException with TOKEN_EXPIRED."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        creds = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(creds)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "TOKEN_EXPIRED"

    def test_invalid_token_raises_401(self):
        """A malformed token should raise HTTPException with INVALID_TOKEN."""
        creds = _make_credentials("not.a.valid.jwt.token")

        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(creds)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "INVALID_TOKEN"

    def test_wrong_secret_raises_401(self):
        """A token signed with a different secret should be rejected."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        creds = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(creds)
        assert exc_info.value.status_code == 401

    def test_missing_sub_claim_raises_401(self):
        """A token without 'sub' claim should raise INVALID_TOKEN."""
        now = datetime.now(timezone.utc)
        payload = {
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        creds = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(creds)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "INVALID_TOKEN"

    def test_wrong_audience_raises_401(self):
        """A token with wrong audience should be rejected."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid.uuid4()),
            "aud": "anon",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        creds = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(creds)
        assert exc_info.value.status_code == 401
