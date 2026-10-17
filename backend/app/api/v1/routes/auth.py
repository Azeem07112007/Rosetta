"""Authentication routes proxying Supabase Auth."""
import structlog
from fastapi import APIRouter, HTTPException, status
from supabase import create_client

from app.core.config import settings
from app.core.security import CurrentUserId
from app.schemas.schemas import (
    AuthResponse,
    MessageResponse,
    ResetPasswordRequest,
    SignInRequest,
    SignUpRequest,
)

router = APIRouter()
logger = structlog.get_logger()

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(request: SignUpRequest) -> AuthResponse:
    """Create a new user account via Supabase Auth."""
    try:
        response = supabase.auth.sign_up(
            {"email": request.email, "password": request.password}
        )

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SIGNUP_FAILED", "message": "Account creation failed."},
            )

        session = response.session
        if not session:
            # Email confirmation may be required
            return AuthResponse(
                access_token="",
                refresh_token="",
                user_id=str(response.user.id),
                email=response.user.email or request.email,
            )

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user_id=str(response.user.id),
            email=response.user.email or request.email,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("signup_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SIGNUP_FAILED", "message": str(e)},
        )


@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest) -> AuthResponse:
    """Authenticate a user via Supabase Auth."""
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."},
            )

        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=str(response.user.id),
            email=response.user.email or request.email,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("signin_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."},
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest) -> MessageResponse:
    """Send a password reset email via Supabase Auth."""
    try:
        supabase.auth.reset_password_email(request.email)
        return MessageResponse(
            message="If an account with that email exists, a reset link has been sent."
        )
    except Exception as e:
        logger.error("reset_password_error", error=str(e))
        # Always return success to avoid email enumeration
        return MessageResponse(
            message="If an account with that email exists, a reset link has been sent."
        )


@router.post("/signout", response_model=MessageResponse)
async def sign_out(user_id: CurrentUserId) -> MessageResponse:
    """Sign out the current user."""
    # JWT is stateless; client should discard the token.
    # This endpoint exists for completeness and potential future server-side invalidation.
    logger.info("user_signed_out", user_id=user_id)
    return MessageResponse(message="Signed out successfully.")
