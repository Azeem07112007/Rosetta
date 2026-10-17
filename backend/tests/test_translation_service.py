"""Tests for the TranslationService with in-memory DB and mocked Gemini."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Translation, UsageRecord
from app.schemas.schemas import TranslationCreateRequest
from app.services.translation_service import TranslationService

from tests.conftest import TEST_USER_ID


@pytest.fixture
def service():
    return TranslationService()


@pytest.fixture
def mock_gemini_client():
    mock = AsyncMock()
    mock.translate_code = AsyncMock(return_value={
        "translated_code": 'console.log("hello");',
        "explanation": None,
        "model_used": "gemini-test",
        "tokens_used": 50,
    })
    mock.detect_language = AsyncMock(return_value="python")
    return mock


class TestGetCurrentUsage:
    @pytest.mark.asyncio
    async def test_no_usage_returns_zeros(self, service, db_session):
        result = await service.get_current_usage(db_session, TEST_USER_ID)
        assert result["translation_count"] == 0
        assert result["tokens_consumed"] == 0

    @pytest.mark.asyncio
    async def test_existing_usage_returned(self, service, seeded_db):
        result = await service.get_current_usage(seeded_db, TEST_USER_ID)
        assert result["translation_count"] == 1
        assert result["tokens_consumed"] == 50


class TestCreateTranslation:
    @pytest.mark.asyncio
    async def test_successful_translation(self, service, db_session, mock_gemini_client):
        request = TranslationCreateRequest(
            source_code='print("hello")',
            source_language="python",
            target_language="typescript",
            explain=False,
        )

        with patch("app.services.translation_service.gemini_client", mock_gemini_client):
            with patch("app.services.translation_service.settings") as mock_settings:
                mock_settings.MONTHLY_TRANSLATION_LIMIT = 100
                result = await service.create_translation(db_session, TEST_USER_ID, request)

        assert result.translated_code == 'console.log("hello");'
        assert result.source_language == "python"
        assert result.target_language == "typescript"

    @pytest.mark.asyncio
    async def test_unsupported_target_language(self, service, db_session, mock_gemini_client):
        request = TranslationCreateRequest(
            source_code='print("hello")',
            source_language="python",
            target_language="brainfuck",
        )

        with patch("app.services.translation_service.gemini_client", mock_gemini_client):
            with patch("app.services.translation_service.settings") as mock_settings:
                mock_settings.MONTHLY_TRANSLATION_LIMIT = 100
                with pytest.raises(ValueError, match="Unsupported target language"):
                    await service.create_translation(db_session, TEST_USER_ID, request)

    @pytest.mark.asyncio
    async def test_same_source_and_target_rejected(self, service, db_session, mock_gemini_client):
        request = TranslationCreateRequest(
            source_code='print("hello")',
            source_language="python",
            target_language="python",
        )

        with patch("app.services.translation_service.gemini_client", mock_gemini_client):
            with patch("app.services.translation_service.settings") as mock_settings:
                mock_settings.MONTHLY_TRANSLATION_LIMIT = 100
                with pytest.raises(ValueError, match="Source and target language must be different"):
                    await service.create_translation(db_session, TEST_USER_ID, request)

    @pytest.mark.asyncio
    async def test_auto_detection_calls_detect_language(self, service, db_session, mock_gemini_client):
        request = TranslationCreateRequest(
            source_code='print("hello")',
            source_language="auto",
            target_language="typescript",
        )

        with patch("app.services.translation_service.gemini_client", mock_gemini_client):
            with patch("app.services.translation_service.settings") as mock_settings:
                mock_settings.MONTHLY_TRANSLATION_LIMIT = 100
                result = await service.create_translation(db_session, TEST_USER_ID, request)

        mock_gemini_client.detect_language.assert_called_once_with('print("hello")')
        assert result.source_language == "python"

    @pytest.mark.asyncio
    async def test_monthly_limit_enforced(self, service, db_session, mock_gemini_client):
        # Seed usage at the limit
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage = UsageRecord(
            user_id=uuid.UUID(TEST_USER_ID),
            month=month_start,
            translation_count=100,
            tokens_consumed=5000,
        )
        db_session.add(usage)
        await db_session.commit()

        request = TranslationCreateRequest(
            source_code='print("hello")',
            source_language="python",
            target_language="typescript",
        )

        with patch("app.services.translation_service.gemini_client", mock_gemini_client):
            with patch("app.services.translation_service.settings") as mock_settings:
                mock_settings.MONTHLY_TRANSLATION_LIMIT = 100
                with pytest.raises(PermissionError, match="Monthly translation limit"):
                    await service.create_translation(db_session, TEST_USER_ID, request)


class TestListTranslations:
    @pytest.mark.asyncio
    async def test_empty_list(self, service, db_session):
        result = await service.list_translations(db_session, TEST_USER_ID)
        assert result["total"] == 0
        assert result["translations"] == []

    @pytest.mark.asyncio
    async def test_returns_user_translations(self, service, seeded_db):
        result = await service.list_translations(seeded_db, TEST_USER_ID)
        assert result["total"] == 1
        assert len(result["translations"]) == 1

    @pytest.mark.asyncio
    async def test_pagination(self, service, db_session):
        # Insert 5 translations
        for i in range(5):
            t = Translation(
                user_id=uuid.UUID(TEST_USER_ID),
                source_language="python",
                target_language="go",
                source_code=f"code_{i}",
                translated_code=f"translated_{i}",
                model_used="gemini-test",
                tokens_used=10,
            )
            db_session.add(t)
        await db_session.commit()

        result = await service.list_translations(db_session, TEST_USER_ID, page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["translations"]) == 2
        assert result["page"] == 1


class TestGetTranslation:
    @pytest.mark.asyncio
    async def test_get_existing(self, service, seeded_db):
        # First list to get the ID
        result = await service.list_translations(seeded_db, TEST_USER_ID)
        t_id = str(result["translations"][0].id)

        translation = await service.get_translation(seeded_db, TEST_USER_ID, t_id)
        assert translation is not None
        assert translation.source_language == "python"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, service, db_session):
        result = await service.get_translation(
            db_session, TEST_USER_ID, str(uuid.uuid4())
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_cannot_access_other_users_translation(self, service, seeded_db):
        result = await service.list_translations(seeded_db, TEST_USER_ID)
        t_id = str(result["translations"][0].id)

        other_user = str(uuid.uuid4())
        translation = await service.get_translation(seeded_db, other_user, t_id)
        assert translation is None


class TestDeleteTranslation:
    @pytest.mark.asyncio
    async def test_delete_existing(self, service, seeded_db):
        result = await service.list_translations(seeded_db, TEST_USER_ID)
        t_id = str(result["translations"][0].id)

        deleted = await service.delete_translation(seeded_db, TEST_USER_ID, t_id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service, db_session):
        deleted = await service.delete_translation(
            db_session, TEST_USER_ID, str(uuid.uuid4())
        )
        assert deleted is False
