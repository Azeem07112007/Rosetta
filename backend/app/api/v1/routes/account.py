"""Account management routes."""
import structlog
from fastapi import APIRouter, HTTPException, status
from supabase import create_client

from app.core.config import settings
from app.core.security import CurrentUserId
from app.schemas.schemas import AccountResponse, AccountUpdateRequest, MessageResponse

router = APIRouter()
logger = structlog.get_logger()

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.get("", response_model=AccountResponse)
async def get_account(user_id: CurrentUserId) -> AccountResponse:
    """Get the current user's account details from Supabase Auth."""
    try:
        response = supabase_admin.auth.admin.get_user_by_id(user_id)
        user = response.user

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "User not found."},
            )

        return AccountResponse(
            id=str(user.id),
            email=user.email or "",
            display_name=(user.user_metadata or {}).get("display_name"),
            created_at=str(user.created_at) if user.created_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_account_error", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ACCOUNT_ERROR", "message": "Failed to retrieve account."},
        )


@router.patch("", response_model=AccountResponse)
async def update_account(
    request: AccountUpdateRequest,
    user_id: CurrentUserId,
) -> AccountResponse:
    """Update the current user's display name."""
    try:
        response = supabase_admin.auth.admin.update_user_by_id(
            user_id,
            {"user_metadata": {"display_name": request.display_name}},
        )
        user = response.user

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "User not found."},
            )

        return AccountResponse(
            id=str(user.id),
            email=user.email or "",
            display_name=(user.user_metadata or {}).get("display_name"),
            created_at=str(user.created_at) if user.created_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_account_error", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ACCOUNT_ERROR", "message": "Failed to update account."},
        )


@router.delete("", response_model=MessageResponse)
async def delete_account(user_id: CurrentUserId) -> MessageResponse:
    """Delete the current user's account and all associated data.

    This deletes the user from Supabase Auth. Associated data in the
    translations and usage_records tables will be cleaned up by RLS
    cascade policies or a separate cleanup job.
    """
    try:
        supabase_admin.auth.admin.delete_user(user_id)
        logger.info("account_deleted", user_id=user_id)
        return MessageResponse(message="Account deleted successfully.")
    except Exception as e:
        logger.error("delete_account_error", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ACCOUNT_ERROR", "message": "Failed to delete account."},
        )
