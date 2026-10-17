"""Unit tests for Pydantic schemas and input validation."""
import pytest
from pydantic import ValidationError

from app.schemas.schemas import (
    SignUpRequest,
    SignInRequest,
    ResetPasswordRequest,
    TranslationCreateRequest,
    AccountUpdateRequest,
)


class TestSignUpRequest:
    def test_valid_signup(self):
        req = SignUpRequest(email="test@example.com", password="securepass123")
        assert req.email == "test@example.com"

    def test_short_email_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            SignUpRequest(email="a@b", password="securepass123")
        assert "string_too_short" in str(exc_info.value) or "at least" in str(exc_info.value)

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            SignUpRequest(email="test@example.com", password="short")
        assert "string_too_short" in str(exc_info.value) or "at least" in str(exc_info.value)

    def test_long_password_rejected(self):
        with pytest.raises(ValidationError):
            SignUpRequest(email="test@example.com", password="x" * 129)


class TestSignInRequest:
    def test_valid_signin(self):
        req = SignInRequest(email="test@example.com", password="p")
        assert req.password == "p"

    def test_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            SignInRequest(email="test@example.com", password="")


class TestResetPasswordRequest:
    def test_valid_reset(self):
        req = ResetPasswordRequest(email="user@example.com")
        assert req.email == "user@example.com"

    def test_short_email_rejected(self):
        with pytest.raises(ValidationError):
            ResetPasswordRequest(email="a@b")


class TestTranslationCreateRequest:
    def test_valid_request(self):
        req = TranslationCreateRequest(
            source_code='print("hello")',
            source_language="python",
            target_language="typescript",
            explain=False,
        )
        assert req.source_language == "python"
        assert req.explain is False

    def test_auto_detect_default(self):
        req = TranslationCreateRequest(
            source_code="x = 1",
            target_language="go",
        )
        assert req.source_language == "auto"

    def test_empty_source_code_rejected(self):
        with pytest.raises(ValidationError):
            TranslationCreateRequest(
                source_code="",
                target_language="python",
            )

    def test_source_code_max_length(self):
        with pytest.raises(ValidationError):
            TranslationCreateRequest(
                source_code="x" * 10001,
                target_language="python",
            )

    def test_missing_target_language(self):
        with pytest.raises(ValidationError):
            TranslationCreateRequest(
                source_code="x = 1",
            )


class TestAccountUpdateRequest:
    def test_valid_update(self):
        req = AccountUpdateRequest(display_name="John Doe")
        assert req.display_name == "John Doe"

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValidationError):
            AccountUpdateRequest(display_name="")

    def test_long_display_name_rejected(self):
        with pytest.raises(ValidationError):
            AccountUpdateRequest(display_name="x" * 101)
