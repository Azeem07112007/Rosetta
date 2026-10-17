"""Application configuration via environment variables."""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All values can be overridden via a .env file or environment variables.
    See .env.example for documentation of each variable.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Supabase
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzAwMDAwMDAwLCJleHAiOjIxMDAwMDAwMDB9.oDDEnl1NaEEwROT33hkGCSTOyevpxH2OOL0R0GcbuqQ"
    SUPABASE_SERVICE_ROLE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3MDAwMDAwMDAsImV4cCI6MjEwMDAwMDAwMH0.HJ0_8aYLUSmm0YTByeDLJi5OpFN7ACIVpFs3MBkZyGw"
    SUPABASE_JWT_SECRET: str = "placeholder-jwt-secret-for-development-mode-at-least-32-chars"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./rosetta.db"

    # Gemini AI
    GEMINI_API_KEY: str = "placeholder-gemini-key"
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 20
    MONTHLY_TRANSLATION_LIMIT: int = 100

    # Input constraints
    MAX_SOURCE_CODE_LENGTH: int = 10000

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()  # type: ignore[call-arg]
