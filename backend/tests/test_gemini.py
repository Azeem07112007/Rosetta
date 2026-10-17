"""Unit tests for the Gemini client with mocked responses."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.gemini_client import GeminiClient, SUPPORTED_LANGUAGE_IDS


class TestGeminiClientTranslation:
    """Tests for GeminiClient.translate_code with mocked Gemini API."""

    @pytest.fixture
    def client(self):
        """Create a GeminiClient with a mocked model."""
        with patch("app.services.gemini_client.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig.return_value = MagicMock()
            c = GeminiClient()
            c.model = mock_model
            return c

    @pytest.mark.asyncio
    async def test_translate_code_standard(self, client):
        """Standard translation returns translated code without explanation."""
        mock_response = MagicMock()
        mock_response.text = 'console.log("hello");'
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 10

        client.model.generate_content_async = AsyncMock(return_value=mock_response)

        result = await client.translate_code(
            source_code='print("hello")',
            source_language="python",
            target_language="typescript",
            explain=False,
        )

        assert result["translated_code"] == 'console.log("hello");'
        assert result["explanation"] is None
        assert result["tokens_used"] == 30

    @pytest.mark.asyncio
    async def test_translate_code_with_explanation(self, client):
        """Translation with explain=True splits code and explanation."""
        mock_response = MagicMock()
        mock_response.text = (
            'console.log("hello");\n'
            "---EXPLANATION---\n"
            "1. Python print() maps to console.log() in TypeScript."
        )
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 30
        mock_response.usage_metadata.candidates_token_count = 20

        client.model.generate_content_async = AsyncMock(return_value=mock_response)

        result = await client.translate_code(
            source_code='print("hello")',
            source_language="python",
            target_language="typescript",
            explain=True,
        )

        assert result["translated_code"] == 'console.log("hello");'
        assert "console.log" in result["explanation"]
        assert result["tokens_used"] == 50

    @pytest.mark.asyncio
    async def test_translate_code_api_error(self, client):
        """API errors should propagate."""
        client.model.generate_content_async = AsyncMock(
            side_effect=Exception("Gemini API error")
        )

        with pytest.raises(Exception, match="Gemini API error"):
            await client.translate_code(
                source_code='print("hello")',
                source_language="python",
                target_language="typescript",
            )


class TestGeminiClientDetection:
    """Tests for GeminiClient.detect_language with mocked Gemini API."""

    @pytest.fixture
    def client(self):
        with patch("app.services.gemini_client.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig.return_value = MagicMock()
            c = GeminiClient()
            c.model = mock_model
            return c

    @pytest.mark.asyncio
    async def test_detect_known_language(self, client):
        mock_response = MagicMock()
        mock_response.text = "python"
        client.model.generate_content_async = AsyncMock(return_value=mock_response)

        result = await client.detect_language('print("hello")')
        assert result == "python"

    @pytest.mark.asyncio
    async def test_detect_alias_normalization(self, client):
        """C++ and C# should be normalized to cpp and csharp."""
        mock_response = MagicMock()
        mock_response.text = "c++"
        client.model.generate_content_async = AsyncMock(return_value=mock_response)

        result = await client.detect_language("int main() {}")
        assert result == "cpp"

    @pytest.mark.asyncio
    async def test_detect_unknown_language(self, client):
        mock_response = MagicMock()
        mock_response.text = "brainfuck"
        client.model.generate_content_async = AsyncMock(return_value=mock_response)

        result = await client.detect_language("++++++++[>++++[>++>]>+]")
        assert result == "unknown"

    @pytest.mark.asyncio
    async def test_detect_api_error_returns_unknown(self, client):
        """On API error, detect_language should return 'unknown' not crash."""
        client.model.generate_content_async = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await client.detect_language('print("hello")')
        assert result == "unknown"


class TestSupportedLanguages:
    """Verify the supported languages list."""

    def test_supported_languages_not_empty(self):
        assert len(SUPPORTED_LANGUAGE_IDS) > 0

    def test_common_languages_present(self):
        expected = {"python", "typescript", "javascript", "java", "go", "rust"}
        assert expected.issubset(SUPPORTED_LANGUAGE_IDS)
