 """Seed script for demo data.

THIS IS DEMO DATA FOR DEVELOPMENT ONLY.
Do not use in production. Run with:
  python -m app.seed

Requires a running database and valid environment variables.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from app.core.database import async_session_factory, engine
from app.models.models import Base, Translation, UsageRecord


DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

DEMO_TRANSLATIONS = [
    {
        "source_language": "python",
        "target_language": "typescript",
        "source_code": 'def greet(name: str) -> str:\n    """Return a greeting."""\n    return f"Hello, {name}!"',
        "translated_code": 'function greet(name: string): string {\n  // Return a greeting.\n  return `Hello, ${name}!`;\n}',
        "explanation": "1. Python type hints map to TypeScript type annotations.\n2. f-strings become template literals.\n3. Docstrings become single-line comments in TypeScript.",
        "model_used": "gemini-2.0-flash",
        "tokens_used": 150,
    },
    {
        "source_language": "javascript",
        "target_language": "python",
        "source_code": "const fibonacci = (n) => {\n  if (n <= 1) return n;\n  return fibonacci(n - 1) + fibonacci(n - 2);\n};",
        "translated_code": "def fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    return fibonacci(n - 1) + fibonacci(n - 2)",
        "explanation": None,
        "model_used": "gemini-2.0-flash",
        "tokens_used": 120,
    },
    {
        "source_language": "python",
        "target_language": "rust",
        "source_code": "def factorial(n: int) -> int:\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)",
        "translated_code": "fn factorial(n: u64) -> u64 {\n    if n == 0 {\n        return 1;\n    }\n    n * factorial(n - 1)\n}",
        "explanation": "1. Python int maps to u64 in Rust for non-negative integers.\n2. Rust uses implicit return for the last expression.",
        "model_used": "gemini-2.0-flash",
        "tokens_used": 130,
    },
]


async def seed() -> None:
    """Insert demo data into the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        for t_data in DEMO_TRANSLATIONS:
            translation = Translation(
                user_id=DEMO_USER_ID,
                **t_data,
            )
            session.add(translation)

        usage = UsageRecord(
            user_id=DEMO_USER_ID,
            month=month_start,
            translation_count=len(DEMO_TRANSLATIONS),
            tokens_consumed=sum(t["tokens_used"] for t in DEMO_TRANSLATIONS),
        )
        session.add(usage)

        await session.commit()

    print(f"Seeded {len(DEMO_TRANSLATIONS)} demo translations for user {DEMO_USER_ID}")
    print("NOTE: This is demo data for development only.")


if __name__ == "__main__":
    asyncio.run(seed())
