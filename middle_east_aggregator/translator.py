"""
Google Cloud Translation API wrapper with character counting and caching.

Provides translation services with precise character counting for quota tracking.
"""

import hashlib
import logging
from typing import Optional

from google.cloud import translate_v2 as translate

from .translation_config import TranslationConfig, TranslationMode
from .translation_quota import QuotaTracker

logger = logging.getLogger(__name__)


class TranslationResult:
    """Result of a translation operation."""

    def __init__(
        self,
        translated_text: str,
        input_char_count: int,
        output_char_count: int,
        success: bool,
        cached: bool = False
    ):
        self.translated_text = translated_text
        self.input_char_count = input_char_count
        self.output_char_count = output_char_count
        self.success = success
        self.cached = cached


class Translator:
    """
    Translation service with quota management and caching.

    Uses Google Cloud Translation API with character counting before
    API calls to enable accurate quota tracking.
    """

    def __init__(
        self,
        quota_tracker: Optional[QuotaTracker] = None,
        enable_cache: bool = True
    ):
        """
        Initialize translator.

        Args:
            quota_tracker: QuotaTracker instance. If None, creates new one.
            enable_cache: Whether to cache translation results
        """
        self.client = translate.Client()
        self.quota_tracker = quota_tracker or QuotaTracker()
        self.enable_cache = enable_cache
        self._cache: dict[str, str] = {}

    def _get_cache_key(self, text: str, target_language: str) -> str:
        """Generate cache key for text and target language."""
        content = f"{text}:{target_language}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _check_cache(self, text: str, target_language: str) -> Optional[str]:
        """Check if translation is in cache."""
        if not self.enable_cache:
            return None

        cache_key = self._get_cache_key(text, target_language)
        return self._cache.get(cache_key)

    def _store_cache(self, text: str, target_language: str, translation: str) -> None:
        """Store translation in cache."""
        if not self.enable_cache:
            return

        cache_key = self._get_cache_key(text, target_language)
        self._cache[cache_key] = translation

    def translate(
        self,
        text: str,
        target_language: str = "ja"
    ) -> TranslationResult:
        """
        Translate text to target language.

        Character counting happens BEFORE API call for accuracy.
        Failed API calls return original text with char_count=0.

        Args:
            text: Text to translate
            target_language: ISO 639-1 language code (default: "ja")

        Returns:
            TranslationResult with translation and character counts
        """
        if not text or not text.strip():
            return TranslationResult(
                translated_text="",
                input_char_count=0,
                output_char_count=0,
                success=True,
                cached=False
            )

        # Check cache first
        cached_translation = self._check_cache(text, target_language)
        if cached_translation:
            logger.debug(f"Using cached translation for text: {text[:50]}...")
            return TranslationResult(
                translated_text=cached_translation,
                input_char_count=0,  # Don't count cached translations
                output_char_count=len(cached_translation),
                success=True,
                cached=True
            )

        # Count input characters BEFORE API call
        input_char_count = len(text)

        try:
            # Call Google Cloud Translation API
            result = self.client.translate(
                text,
                target_language=target_language,
                format_="text"
            )

            translated_text = result["translatedText"]
            output_char_count = len(translated_text)

            # Store in cache
            self._store_cache(text, target_language, translated_text)

            logger.debug(
                f"Translated {input_char_count} chars to {output_char_count} chars"
            )

            return TranslationResult(
                translated_text=translated_text,
                input_char_count=input_char_count,
                output_char_count=output_char_count,
                success=True,
                cached=False
            )

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original text with char_count=0 (don't count failed attempts)
            return TranslationResult(
                translated_text=text,
                input_char_count=0,
                output_char_count=0,
                success=False,
                cached=False
            )

    def translate_title(self, title: str) -> TranslationResult:
        """
        Translate article title only.

        Args:
            title: Article title

        Returns:
            TranslationResult
        """
        return self.translate(title, target_language="ja")

    def translate_summary(self, content: str, max_chars: int = 500) -> TranslationResult:
        """
        Translate article content summary (first N characters).

        Args:
            content: Full article content
            max_chars: Maximum characters to translate

        Returns:
            TranslationResult
        """
        # Truncate to max_chars
        summary = content[:max_chars] if len(content) > max_chars else content
        return self.translate(summary, target_language="ja")

    def translate_full(
        self,
        content: str,
        max_chars: Optional[int] = None
    ) -> TranslationResult:
        """
        Translate full article content with optional character limit.

        Args:
            content: Full article content
            max_chars: Maximum characters to translate (default: from config)

        Returns:
            TranslationResult
        """
        max_chars = max_chars or TranslationConfig.MAX_CHARS_PER_ARTICLE
        truncated = content[:max_chars] if len(content) > max_chars else content
        return self.translate(truncated, target_language="ja")

    def translate_article(
        self,
        title: str,
        content: str,
        mode: TranslationMode
    ) -> tuple[Optional[str], Optional[str], int]:
        """
        Translate article based on translation mode.

        Args:
            title: Article title
            content: Article content
            mode: Translation mode

        Returns:
            Tuple of (title_ja, content_ja, total_char_count)
        """
        if mode == TranslationMode.DISABLED:
            return None, None, 0

        total_chars = 0
        title_ja = None
        content_ja = None

        # Always translate title if not disabled
        if mode in [
            TranslationMode.TITLES_ONLY,
            TranslationMode.TITLES_AND_SUMMARY,
            TranslationMode.FULL
        ]:
            title_result = self.translate_title(title)
            if title_result.success:
                title_ja = title_result.translated_text
                total_chars += title_result.input_char_count

        # Translate content based on mode
        if mode == TranslationMode.TITLES_AND_SUMMARY:
            content_result = self.translate_summary(content, max_chars=500)
            if content_result.success:
                content_ja = content_result.translated_text
                total_chars += content_result.input_char_count

        elif mode == TranslationMode.FULL:
            content_result = self.translate_full(content)
            if content_result.success:
                content_ja = content_result.translated_text
                total_chars += content_result.input_char_count

        return title_ja, content_ja, total_chars
