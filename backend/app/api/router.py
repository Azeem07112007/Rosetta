"""API router aggregating all v1 route modules."""
from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.translations import router as translations_router
from app.api.v1.routes.usage import router as usage_router
from app.api.v1.routes.account import router as account_router
from app.api.v1.routes.analyses import router as analyses_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(translations_router, prefix="/translations", tags=["translations"])
api_router.include_router(usage_router, prefix="/usage", tags=["usage"])
api_router.include_router(account_router, prefix="/account", tags=["account"])
api_router.include_router(analyses_router, prefix="/analyses", tags=["analyses"])
