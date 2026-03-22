"""
Translation configuration with free tier safeguards.

Manages all configuration for the Google Cloud Translation API integration,
including quota limits, safe margins, and translation modes.
"""

import os
from enum import Enum


class TranslationMode(Enum):
    """Translation modes with different character usage levels."""
    DISABLED = "disabled"  # No translation
    TITLES_ONLY = "titles_only"  # ~100 chars per article
    TITLES_AND_SUMMARY = "titles_and_summary"  # ~600 chars per article
    FULL = "full"  # ~2000 chars per article


class TranslationConfig:
    """
    Translation configuration with environment variable overrides.

    Default configuration is conservative to ensure free tier compliance.
    """

    # Free tier limits
    MONTHLY_LIMIT_CHARS = int(os.getenv("TRANSLATION_MONTHLY_LIMIT", "500000"))

    # Safe margin: operate at 80% of limit by default (400K of 500K)
    SAFE_MARGIN_PERCENT = float(os.getenv("TRANSLATION_SAFE_MARGIN", "0.80"))

    # Translation mode (direct control)
    # Options: "disabled", "titles_only", "titles_and_summary", "full"
    # Default: "titles_and_summary" for optimal free tier usage
    TRANSLATION_MODE = os.getenv("TRANSLATION_MODE", "titles_and_summary")

    # Legacy flags (for backward compatibility)
    TRANSLATE_TITLES_ONLY = os.getenv("TRANSLATE_TITLES_ONLY", "false").lower() == "true"
    TRANSLATE_CONTENT = os.getenv("TRANSLATE_CONTENT", "false").lower() == "true"

    # Automatic disable threshold (95% by default)
    DISABLE_ON_QUOTA_PERCENT = float(os.getenv("TRANSLATION_DISABLE_THRESHOLD", "0.95"))

    # Daily limit to spread usage evenly across month
    DAILY_LIMIT_CHARS = int(os.getenv("TRANSLATION_DAILY_LIMIT", "20000"))

    # Maximum characters per article to prevent individual article overruns
    MAX_CHARS_PER_ARTICLE = int(os.getenv("TRANSLATION_MAX_PER_ARTICLE", "5000"))

    # GCP credentials path
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        os.path.expanduser("~/gcp-key.json")
    )

    # GCP project ID
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "middle-east-news-aggregator")

    @classmethod
    def get_safe_limit_chars(cls) -> int:
        """Calculate the safe monthly limit with margin applied."""
        return int(cls.MONTHLY_LIMIT_CHARS * cls.SAFE_MARGIN_PERCENT)

    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration at startup.

        Raises:
            ValueError: If configuration is invalid or dangerous
        """
        if cls.SAFE_MARGIN_PERCENT > 1.0:
            raise ValueError(
                f"TRANSLATION_SAFE_MARGIN must be <= 1.0, got {cls.SAFE_MARGIN_PERCENT}"
            )

        if cls.SAFE_MARGIN_PERCENT > 0.90:
            print(
                f"WARNING: TRANSLATION_SAFE_MARGIN is {cls.SAFE_MARGIN_PERCENT}, "
                f"which provides little buffer for variance. Recommended: 0.80"
            )

        safe_limit = cls.get_safe_limit_chars()
        if safe_limit < 50000:
            raise ValueError(
                f"Safe limit is only {safe_limit} chars/month. "
                f"This is too low to be useful. Check TRANSLATION_MONTHLY_LIMIT "
                f"and TRANSLATION_SAFE_MARGIN settings."
            )

        if cls.DAILY_LIMIT_CHARS * 31 > cls.get_safe_limit_chars():
            print(
                f"WARNING: TRANSLATION_DAILY_LIMIT ({cls.DAILY_LIMIT_CHARS}) "
                f"allows up to {cls.DAILY_LIMIT_CHARS * 31} chars/month, "
                f"which exceeds safe limit of {safe_limit}. "
                f"Daily limit will be capped to prevent overage."
            )

        if not os.path.exists(cls.GOOGLE_APPLICATION_CREDENTIALS):
            raise FileNotFoundError(
                f"Google Cloud credentials not found at: "
                f"{cls.GOOGLE_APPLICATION_CREDENTIALS}. "
                f"Set GOOGLE_APPLICATION_CREDENTIALS environment variable."
            )

    @classmethod
    def get_default_mode(cls) -> TranslationMode:
        """Determine default translation mode from configuration."""
        # Check TRANSLATION_MODE first (preferred method)
        mode_str = cls.TRANSLATION_MODE.lower()

        if mode_str == "disabled":
            return TranslationMode.DISABLED
        elif mode_str == "titles_only":
            return TranslationMode.TITLES_ONLY
        elif mode_str == "titles_and_summary":
            return TranslationMode.TITLES_AND_SUMMARY
        elif mode_str == "full":
            return TranslationMode.FULL

        # Fall back to legacy flags if TRANSLATION_MODE is invalid
        if cls.TRANSLATE_TITLES_ONLY and not cls.TRANSLATE_CONTENT:
            return TranslationMode.TITLES_ONLY
        elif cls.TRANSLATE_CONTENT:
            return TranslationMode.FULL
        else:
            return TranslationMode.DISABLED

    @classmethod
    def to_dict(cls) -> dict:
        """Export configuration as dictionary for monitoring."""
        return {
            "monthly_limit_chars": cls.MONTHLY_LIMIT_CHARS,
            "safe_margin_percent": cls.SAFE_MARGIN_PERCENT,
            "safe_limit_chars": cls.get_safe_limit_chars(),
            "translate_titles_only": cls.TRANSLATE_TITLES_ONLY,
            "translate_content": cls.TRANSLATE_CONTENT,
            "disable_threshold_percent": cls.DISABLE_ON_QUOTA_PERCENT,
            "daily_limit_chars": cls.DAILY_LIMIT_CHARS,
            "max_chars_per_article": cls.MAX_CHARS_PER_ARTICLE,
            "default_mode": cls.get_default_mode().value,
            "gcp_project_id": cls.GCP_PROJECT_ID,
        }
