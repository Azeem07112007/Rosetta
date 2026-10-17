"""Usage tracking routes."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import CurrentUserId
from app.schemas.schemas import UsageResponse
from app.services.translation_service import translation_service

router = APIRouter()


@router.get("", response_model=UsageResponse)
async def get_usage(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UsageResponse:
    """Get the current month's usage statistics for the authenticated user."""
    usage = await translation_service.get_current_usage(db, user_id)
    return UsageResponse(**usage)
