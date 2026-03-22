"""
Tests for translation configuration.
"""

import os
import pytest
from middle_east_aggregator.translation_config import TranslationConfig, TranslationMode


class TestTranslationConfig:
    """Test suite for TranslationConfig."""

    def test_default_values(self):
        """Test that default configuration values are conservative."""
        assert TranslationConfig.MONTHLY_LIMIT_CHARS == 500000
        assert TranslationConfig.SAFE_MARGIN_PERCENT == 0.80
        assert TranslationConfig.DAILY_LIMIT_CHARS == 20000
        assert TranslationConfig.MAX_CHARS_PER_ARTICLE == 5000

    def test_get_safe_limit_chars(self):
        """Test safe limit calculation."""
        safe_limit = TranslationConfig.get_safe_limit_chars()
        expected = int(500000 * 0.80)  # 400,000
        assert safe_limit == expected

    def test_get_default_mode_titles_and_summary(self):
        """Test default mode is TITLES_AND_SUMMARY for optimal free tier usage."""
        # Default config has TRANSLATION_MODE=titles_and_summary
        mode = TranslationConfig.get_default_mode()
        assert mode == TranslationMode.TITLES_AND_SUMMARY

    def test_get_default_mode_via_env_titles_only(self, monkeypatch):
        """Test default mode when TRANSLATION_MODE is set to titles_only."""
        monkeypatch.setenv("TRANSLATION_MODE", "titles_only")

        from importlib import reload
        from middle_east_aggregator import translation_config
        reload(translation_config)

        mode = translation_config.TranslationConfig.get_default_mode()
        # Use the reloaded module's TranslationMode
        assert mode == translation_config.TranslationMode.TITLES_ONLY

    def test_get_default_mode_via_env_full(self, monkeypatch):
        """Test default mode when TRANSLATION_MODE is set to full."""
        monkeypatch.setenv("TRANSLATION_MODE", "full")

        from importlib import reload
        from middle_east_aggregator import translation_config
        reload(translation_config)

        mode = translation_config.TranslationConfig.get_default_mode()
        assert mode == translation_config.TranslationMode.FULL

    def test_get_default_mode_via_env_disabled(self, monkeypatch):
        """Test default mode when TRANSLATION_MODE is set to disabled."""
        monkeypatch.setenv("TRANSLATION_MODE", "disabled")

        from importlib import reload
        from middle_east_aggregator import translation_config
        reload(translation_config)

        mode = translation_config.TranslationConfig.get_default_mode()
        assert mode == translation_config.TranslationMode.DISABLED

    def test_legacy_flags_backward_compatibility(self, monkeypatch):
        """Test that legacy TRANSLATE_* flags still work."""
        # Clear TRANSLATION_MODE to force legacy path
        monkeypatch.setenv("TRANSLATION_MODE", "invalid_mode")
        monkeypatch.setenv("TRANSLATE_TITLES_ONLY", "true")
        monkeypatch.setenv("TRANSLATE_CONTENT", "false")

        from importlib import reload
        from middle_east_aggregator import translation_config
        reload(translation_config)

        mode = translation_config.TranslationConfig.get_default_mode()
        assert mode == translation_config.TranslationMode.TITLES_ONLY

    def test_validate_safe_margin_too_high(self, monkeypatch):
        """Test validation fails when safe margin > 1.0."""
        monkeypatch.setenv("TRANSLATION_SAFE_MARGIN", "1.5")

        from importlib import reload
        from middle_east_aggregator import translation_config
        reload(translation_config)

        with pytest.raises(ValueError, match="must be <= 1.0"):
            translation_config.TranslationConfig.validate()

    def test_to_dict(self):
        """Test configuration export to dictionary."""
        config_dict = TranslationConfig.to_dict()

        assert "monthly_limit_chars" in config_dict
        assert "safe_limit_chars" in config_dict
        assert "daily_limit_chars" in config_dict
        assert config_dict["monthly_limit_chars"] == 500000
        assert config_dict["safe_limit_chars"] == 400000
