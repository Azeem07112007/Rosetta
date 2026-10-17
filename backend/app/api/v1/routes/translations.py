"""Translation CRUD routes."""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import CurrentUserId
from app.schemas.schemas import (
    TranslationCreateRequest,
    TranslationListResponse,
    TranslationResponse,
    MessageResponse,
)
from app.services.translation_service import translation_service

router = APIRouter()
logger = structlog.get_logger()


@router.post("", response_model=TranslationResponse, status_code=status.HTTP_201_CREATED)
async def create_translation(
    request: TranslationCreateRequest,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TranslationResponse:
    """Create a new code translation using Gemini AI."""
    try:
        return await translation_service.create_translation(db, user_id, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(e)},
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "TRANSLATION_LIMIT_REACHED", "message": str(e)},
        )
    except Exception as e:
        logger.error("create_translation_error", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "TRANSLATION_FAILED",
                "message": "Translation failed. Please try again.",
            },
        )


@router.get("", response_model=TranslationListResponse)
async def list_translations(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TranslationListResponse:
    """List the current user's translations with pagination."""
    result = await translation_service.list_translations(db, user_id, page, page_size)
    return TranslationListResponse(**result)


@router.get("/{translation_id}", response_model=TranslationResponse)
async def get_translation(
    translation_id: str,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TranslationResponse:
    """Get a single translation by ID."""
    translation = await translation_service.get_translation(db, user_id, translation_id)
    if not translation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Translation not found."},
        )
    return translation


@router.delete("/{translation_id}", response_model=MessageResponse)
async def delete_translation(
    translation_id: str,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Delete a translation by ID."""
    deleted = await translation_service.delete_translation(db, user_id, translation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Translation not found."},
        )
    return MessageResponse(message="Translation deleted.")
