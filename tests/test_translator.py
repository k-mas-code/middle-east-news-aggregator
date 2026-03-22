"""
Tests for translation service.
"""

import pytest
from unittest.mock import Mock, patch
from middle_east_aggregator.translator import Translator, TranslationResult
from middle_east_aggregator.translation_config import TranslationMode


@pytest.fixture
def mock_translate_client():
    """Mock Google Cloud Translation API client."""
    with patch("middle_east_aggregator.translator.translate.Client") as mock:
        yield mock


@pytest.fixture
def mock_quota_tracker():
    """Mock QuotaTracker."""
    tracker = Mock()
    tracker.can_translate.return_value = True
    tracker.record_translation.return_value = None
    return tracker


@pytest.fixture
def translator(mock_translate_client, mock_quota_tracker):
    """Create Translator with mocked dependencies."""
    return Translator(quota_tracker=mock_quota_tracker, enable_cache=True)


class TestTranslator:
    """Test suite for Translator."""

    def test_translate_empty_string(self, translator):
        """Test translating empty string returns empty result."""
        result = translator.translate("")

        assert result.translated_text == ""
        assert result.input_char_count == 0
        assert result.success is True

    def test_translate_success(self, translator, mock_translate_client):
        """Test successful translation."""
        # Mock API response
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.return_value = {
            "translatedText": "こんにちは世界",
            "detectedSourceLanguage": "en"
        }

        result = translator.translate("Hello world", target_language="ja")

        assert result.translated_text == "こんにちは世界"
        assert result.input_char_count == 11  # "Hello world" = 11 chars
        assert result.success is True
        assert result.cached is False

    def test_translate_caching(self, translator, mock_translate_client):
        """Test that repeated translations use cache."""
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.return_value = {
            "translatedText": "こんにちは",
            "detectedSourceLanguage": "en"
        }

        # First call: should hit API
        result1 = translator.translate("Hello", target_language="ja")
        assert result1.input_char_count == 5
        assert result1.cached is False

        # Second call: should use cache
        result2 = translator.translate("Hello", target_language="ja")
        assert result2.translated_text == "こんにちは"
        assert result2.input_char_count == 0  # Cached translations don't count
        assert result2.cached is True

        # Verify API was only called once
        assert mock_client_instance.translate.call_count == 1

    def test_translate_api_failure(self, translator, mock_translate_client):
        """Test that API failures return original text with char_count=0."""
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.side_effect = Exception("API Error")

        result = translator.translate("Hello", target_language="ja")

        assert result.translated_text == "Hello"  # Original text
        assert result.input_char_count == 0  # Don't count failed attempts
        assert result.success is False

    def test_translate_title(self, translator, mock_translate_client):
        """Test title-only translation."""
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.return_value = {
            "translatedText": "中東ニュース",
            "detectedSourceLanguage": "en"
        }

        result = translator.translate_title("Middle East News")

        assert result.translated_text == "中東ニュース"
        assert result.input_char_count == 16  # "Middle East News" = 16 chars
        assert result.success is True

    def test_translate_summary_truncates(self, translator, mock_translate_client):
        """Test that translate_summary truncates content to max_chars."""
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.return_value = {
            "translatedText": "要約",
            "detectedSourceLanguage": "en"
        }

        long_content = "a" * 1000  # 1000 characters
        result = translator.translate_summary(long_content, max_chars=500)

        # Should have truncated to 500 chars before translating
        assert result.input_char_count == 500
        assert result.success is True

    def test_translate_full_respects_max_chars(self, translator, mock_translate_client):
        """Test that translate_full respects MAX_CHARS_PER_ARTICLE."""
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.return_value = {
            "translatedText": "翻訳",
            "detectedSourceLanguage": "en"
        }

        long_content = "b" * 10000  # 10,000 characters
        result = translator.translate_full(long_content, max_chars=5000)

        # Should have truncated to 5000 chars
        assert result.input_char_count == 5000
        assert result.success is True

    def test_translate_article_titles_only(self, translator, mock_translate_client):
        """Test translate_article with TITLES_ONLY mode."""
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.return_value = {
            "translatedText": "タイトル",
            "detectedSourceLanguage": "en"
        }

        title_ja, content_ja, total_chars = translator.translate_article(
            title="Title",
            content="Long content here",
            mode=TranslationMode.TITLES_ONLY
        )

        assert title_ja == "タイトル"
        assert content_ja is None  # Should not translate content
        assert total_chars == 5  # Only title chars

    def test_translate_article_disabled(self, translator):
        """Test translate_article with DISABLED mode."""
        title_ja, content_ja, total_chars = translator.translate_article(
            title="Title",
            content="Content",
            mode=TranslationMode.DISABLED
        )

        assert title_ja is None
        assert content_ja is None
        assert total_chars == 0

    def test_translate_article_full(self, translator, mock_translate_client):
        """Test translate_article with FULL mode."""
        call_count = [0]

        def mock_translate_side_effect(text, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"translatedText": "タイトル", "detectedSourceLanguage": "en"}
            else:
                return {"translatedText": "コンテンツ", "detectedSourceLanguage": "en"}

        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.side_effect = mock_translate_side_effect

        title_ja, content_ja, total_chars = translator.translate_article(
            title="Title",
            content="Content",
            mode=TranslationMode.FULL
        )

        assert title_ja == "タイトル"
        assert content_ja == "コンテンツ"
        assert total_chars == 12  # 5 (title) + 7 (content)

    def test_character_count_accuracy(self, translator, mock_translate_client):
        """Test that character counting matches actual input length."""
        mock_client_instance = mock_translate_client.return_value
        mock_client_instance.translate.return_value = {
            "translatedText": "翻訳されたテキスト",
            "detectedSourceLanguage": "en"
        }

        test_text = "This is a test with exactly forty-nine chars!"
        actual_length = len(test_text)

        result = translator.translate(test_text)

        assert result.input_char_count == actual_length
        assert result.input_char_count == len(test_text)
