"""Translation service: orchestrates Gemini calls, storage, and usage tracking."""
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Translation, UsageRecord
from app.schemas.schemas import TranslationCreateRequest, TranslationResponse
from app.services.gemini_client import gemini_client, SUPPORTED_LANGUAGE_IDS

logger = structlog.get_logger()


class TranslationService:
    """Handles translation creation, retrieval, and usage tracking."""

    async def get_current_usage(
        self, db: AsyncSession, user_id: str
    ) -> dict:
        """Get the current month's usage for a user."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await db.execute(
            select(UsageRecord).where(
                UsageRecord.user_id == uuid.UUID(user_id),
                UsageRecord.month == month_start,
            )
        )
        record = result.scalar_one_or_none()

        if record:
            return {
                "translation_count": record.translation_count,
                "tokens_consumed": record.tokens_consumed,
                "monthly_limit": settings.MONTHLY_TRANSLATION_LIMIT,
                "month": month_start.strftime("%Y-%m"),
            }
        return {
            "translation_count": 0,
            "tokens_consumed": 0,
            "monthly_limit": settings.MONTHLY_TRANSLATION_LIMIT,
            "month": month_start.strftime("%Y-%m"),
        }

    async def _increment_usage(
        self, db: AsyncSession, user_id: str, tokens: int
    ) -> None:
        """Increment the monthly usage counter for a user."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await db.execute(
            select(UsageRecord).where(
                UsageRecord.user_id == uuid.UUID(user_id),
                UsageRecord.month == month_start,
            )
        )
        record = result.scalar_one_or_none()

        if record:
            record.translation_count += 1
            record.tokens_consumed += tokens
        else:
            record = UsageRecord(
                user_id=uuid.UUID(user_id),
                month=month_start,
                translation_count=1,
                tokens_consumed=tokens,
            )
            db.add(record)

    async def create_translation(
        self,
        db: AsyncSession,
        user_id: str,
        request: TranslationCreateRequest,
    ) -> TranslationResponse:
        """Create a new code translation.

        Validates the request, checks usage limits, calls Gemini,
        stores the result, and updates usage counters.
        """
        # Validate target language
        if request.target_language not in SUPPORTED_LANGUAGE_IDS:
            raise ValueError(f"Unsupported target language: {request.target_language}")

        # Check usage limit
        usage = await self.get_current_usage(db, user_id)
        if usage["translation_count"] >= settings.MONTHLY_TRANSLATION_LIMIT:
            raise PermissionError("Monthly translation limit reached.")

        # Detect language if auto
        source_language = request.source_language
        detected_language = None
        if source_language == "auto":
            detected_language = await gemini_client.detect_language(request.source_code)
            source_language = detected_language
            if source_language == "unknown":
                raise ValueError(
                    "Could not detect the source language. Please select it manually."
                )

        # Validate source language
        if source_language not in SUPPORTED_LANGUAGE_IDS:
            raise ValueError(f"Unsupported source language: {source_language}")

        if source_language == request.target_language:
            raise ValueError("Source and target language must be different.")

        # Translate
        result = await gemini_client.translate_code(
            source_code=request.source_code,
            source_language=source_language,
            target_language=request.target_language,
            explain=request.explain,
        )

        # Store translation
        translation = Translation(
            user_id=uuid.UUID(user_id),
            source_language=source_language,
            target_language=request.target_language,
            source_code=request.source_code,
            translated_code=result["translated_code"],
            explanation=result.get("explanation"),
            detected_language=detected_language,
            model_used=result["model_used"],
            tokens_used=result["tokens_used"],
        )
        db.add(translation)

        # Update usage
        await self._increment_usage(db, user_id, result["tokens_used"])

        await db.flush()

        logger.info(
            "translation_created",
            translation_id=str(translation.id),
            user_id=user_id,
            source_language=source_language,
            target_language=request.target_language,
        )

        return TranslationResponse.model_validate(translation)

    async def list_translations(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List translations for a user with pagination."""
        offset = (page - 1) * page_size

        # Count total
        count_result = await db.execute(
            select(func.count(Translation.id)).where(
                Translation.user_id == uuid.UUID(user_id)
            )
        )
        total = count_result.scalar() or 0

        # Fetch page
        result = await db.execute(
            select(Translation)
            .where(Translation.user_id == uuid.UUID(user_id))
            .order_by(Translation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        translations = result.scalars().all()

        return {
            "translations": [
                TranslationResponse.model_validate(t) for t in translations
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_translation(
        self, db: AsyncSession, user_id: str, translation_id: str
    ) -> TranslationResponse | None:
        """Get a single translation by ID, scoped to user."""
        result = await db.execute(
            select(Translation).where(
                Translation.id == uuid.UUID(translation_id),
                Translation.user_id == uuid.UUID(user_id),
            )
        )
        translation = result.scalar_one_or_none()
        if translation:
            return TranslationResponse.model_validate(translation)
        return None

    async def delete_translation(
        self, db: AsyncSession, user_id: str, translation_id: str
    ) -> bool:
        """Delete a translation by ID, scoped to user."""
        result = await db.execute(
            select(Translation).where(
                Translation.id == uuid.UUID(translation_id),
                Translation.user_id == uuid.UUID(user_id),
            )
        )
        translation = result.scalar_one_or_none()
        if translation:
            await db.delete(translation)
            return True
        return False


translation_service = TranslationService()
