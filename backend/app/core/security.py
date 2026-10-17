"""JWT verification and user authentication."""
from typing import Annotated, Any

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security_scheme = HTTPBearer()

_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient | None:
    """Get or initialize the JWKS client for asymmetric token verification."""
    global _jwks_client
    if _jwks_client is None and settings.SUPABASE_URL and "placeholder" not in settings.SUPABASE_URL:
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        headers = {"apikey": settings.SUPABASE_ANON_KEY} if settings.SUPABASE_ANON_KEY else None
        _jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            max_cached_keys=16,
            lifespan=3600,
            headers=headers,
        )
    return _jwks_client


def verify_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> str:
    """Verify Supabase JWT and return the user ID.

    Extracts and validates the JWT from the Authorization header.
    Supports modern Supabase asymmetric signing (ES256/RS256 via JWKS)
    as well as symmetric signing (HS256 via SUPABASE_JWT_SECRET).

    Returns the `sub` claim (Supabase user UUID).

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        jwks = get_jwks_client()

        if alg in ("ES256", "RS256") and jwks is not None:
            signing_key = jwks.get_signing_key_from_jwt(token)
            key: Any = signing_key.key
            allowed_algs = [alg]
        else:
            key = settings.SUPABASE_JWT_SECRET
            allowed_algs = ["HS256"]

        payload = jwt.decode(
            token,
            key,
            algorithms=allowed_algs,
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Authentication token has expired."},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": f"Authentication token is invalid: {exc}"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": f"Token verification failed: {exc}"},
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token does not contain a user ID."},
        )

    return user_id


# Dependency type alias for use in route signatures
CurrentUserId = Annotated[str, Depends(verify_jwt)]
