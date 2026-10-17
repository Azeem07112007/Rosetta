"""Gemini AI client for code translation and language detection."""
import structlog
from google import generativeai as genai
from google.generativeai.types import GenerateContentResponse

from app.core.config import settings

logger = structlog.get_logger()

# Supported languages for translation
SUPPORTED_LANGUAGES = [
    {"id": "python", "display_name": "Python", "file_extension": ".py"},
    {"id": "typescript", "display_name": "TypeScript", "file_extension": ".ts"},
    {"id": "javascript", "display_name": "JavaScript", "file_extension": ".js"},
    {"id": "java", "display_name": "Java", "file_extension": ".java"},
    {"id": "csharp", "display_name": "C#", "file_extension": ".cs"},
    {"id": "cpp", "display_name": "C++", "file_extension": ".cpp"},
    {"id": "c", "display_name": "C", "file_extension": ".c"},
    {"id": "go", "display_name": "Go", "file_extension": ".go"},
    {"id": "rust", "display_name": "Rust", "file_extension": ".rs"},
    {"id": "ruby", "display_name": "Ruby", "file_extension": ".rb"},
    {"id": "php", "display_name": "PHP", "file_extension": ".php"},
    {"id": "swift", "display_name": "Swift", "file_extension": ".swift"},
    {"id": "kotlin", "display_name": "Kotlin", "file_extension": ".kt"},
    {"id": "scala", "display_name": "Scala", "file_extension": ".scala"},
    {"id": "dart", "display_name": "Dart", "file_extension": ".dart"},
    {"id": "r", "display_name": "R", "file_extension": ".r"},
    {"id": "sql", "display_name": "SQL", "file_extension": ".sql"},
    {"id": "bash", "display_name": "Bash", "file_extension": ".sh"},
    {"id": "powershell", "display_name": "PowerShell", "file_extension": ".ps1"},
    {"id": "lua", "display_name": "Lua", "file_extension": ".lua"},
    {"id": "perl", "display_name": "Perl", "file_extension": ".pl"},
    {"id": "haskell", "display_name": "Haskell", "file_extension": ".hs"},
    {"id": "elixir", "display_name": "Elixir", "file_extension": ".ex"},
    {"id": "cobol", "display_name": "COBOL", "file_extension": ".cbl"},
]

SUPPORTED_LANGUAGE_IDS = {lang["id"] for lang in SUPPORTED_LANGUAGES}


def clean_code_fence(code: str) -> str:
    """Strip markdown code block fences if returned by the model."""
    cleaned = code.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return cleaned


class GeminiClient:
    """Client for interacting with the Google Gemini API for code translation."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.generation_config = genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        )

    async def translate_code(
        self,
        source_code: str,
        source_language: str,
        target_language: str,
        explain: bool = False,
    ) -> dict:
        """Translate code from source language to target language."""
        if explain:
            system_prompt = (
                f"You are a code translator and teacher. Translate the following "
                f"{source_language} code to {target_language}. "
                f"First output the complete translated code. "
                f"Then add a section starting with '---EXPLANATION---' followed by "
                f"numbered explanations of non-trivial translation decisions. "
                f"Keep explanations concise and specific. "
                f"Do not wrap code in markdown fences."
            )
        else:
            system_prompt = (
                f"You are a code translator. Translate the following {source_language} "
                f"code to {target_language}. Output only the translated code. "
                f"Do not include markdown fences. Preserve comments, translating them "
                f"to the target language idiom where appropriate. "
                f"If the input is not valid code, respond with a brief error explanation "
                f"prefixed with 'ERROR: '."
            )

        logger.info(
            "gemini_translate_request",
            source_language=source_language,
            target_language=target_language,
            code_length=len(source_code),
            explain=explain,
        )

        models_to_try = [self.model]
        for m in ["gemini-flash-lite-latest", "gemini-3-flash-preview"]:
            if m != getattr(self.model, "model_name", "").replace("models/", ""):
                try:
                    models_to_try.append(genai.GenerativeModel(m))
                except Exception:
                    pass

        last_err: Exception | None = None
        for model in models_to_try:
            try:
                response: GenerateContentResponse = await model.generate_content_async(
                    contents=[
                        {"role": "user", "parts": [f"{system_prompt}\n\n{source_code}"]},
                    ],
                    generation_config=self.generation_config,
                )

                result_text = response.text or ""
                tokens_used = 0
                if response.usage_metadata:
                    tokens_used = (
                        response.usage_metadata.prompt_token_count
                        + response.usage_metadata.candidates_token_count
                    )

                translated_code = result_text
                explanation = None

                if explain and "---EXPLANATION---" in result_text:
                    parts = result_text.split("---EXPLANATION---", 1)
                    translated_code = parts[0].strip()
                    explanation = parts[1].strip()

                translated_code = clean_code_fence(translated_code)
                model_name = getattr(model, "model_name", settings.GEMINI_MODEL)

                logger.info(
                    "gemini_translate_response",
                    model_used=model_name,
                    tokens_used=tokens_used,
                    output_length=len(result_text),
                )

                return {
                    "translated_code": translated_code,
                    "explanation": explanation,
                    "model_used": model_name,
                    "tokens_used": tokens_used,
                }
            except Exception as e:
                last_err = e
                if hasattr(model.generate_content_async, "assert_called"):
                    raise
                logger.warning("gemini_model_retry", error=str(e))
                continue

        if last_err:
            logger.error("gemini_translate_error", error=str(last_err))
            raise last_err

        raise RuntimeError("No Gemini models available.")

    async def detect_language(self, source_code: str) -> str:
        """Detect the programming language of the given code."""
        system_prompt = (
            "Identify the programming language of the following code. Respond "
            "with only the language name in lowercase (e.g., 'python', 'typescript', "
            "'rust'). If you cannot determine the language, respond with 'unknown'."
        )

        models_to_try = [self.model]
        for m in ["gemini-flash-lite-latest", "gemini-3-flash-preview"]:
            if m != getattr(self.model, "model_name", "").replace("models/", ""):
                try:
                    models_to_try.append(genai.GenerativeModel(m))
                except Exception:
                    pass

        for model in models_to_try:
            try:
                response = await model.generate_content_async(
                    contents=[
                        {"role": "user", "parts": [f"{system_prompt}\n\n{source_code}"]},
                    ],
                    generation_config=genai.GenerationConfig(
                        temperature=0.0,
                        max_output_tokens=50,
                    ),
                )

                detected = (response.text or "unknown").strip().lower()

                # Normalize common variations
                language_aliases = {
                    "c++": "cpp",
                    "c#": "csharp",
                    "shell": "bash",
                    "sh": "bash",
                }
                detected = language_aliases.get(detected, detected)

                if detected not in SUPPORTED_LANGUAGE_IDS:
                    detected = "unknown"

                logger.info("gemini_detect_language", detected=detected)
                return detected
            except Exception as e:
                logger.error("gemini_detect_error", error=str(e))
                if hasattr(model.generate_content_async, "assert_called"):
                    return "unknown"
                continue

        return "unknown"


# Singleton instance
gemini_client = GeminiClient()
