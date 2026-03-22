"""
Integration tests for translation pipeline.

Tests the complete flow: filtering → translation → quota tracking → storage.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from middle_east_aggregator.pipeline import NewsPipeline
from middle_east_aggregator.models import Article, RawArticle
from middle_east_aggregator.translation_config import TranslationMode


@pytest.fixture
def mock_collectors():
    """Mock RSS collectors."""
    with patch("middle_east_aggregator.pipeline.AlJazeeraCollector") as aj, \
         patch("middle_east_aggregator.pipeline.ReutersCollector") as reuters, \
         patch("middle_east_aggregator.pipeline.BBCCollector") as bbc:

        # Return mock RawArticles
        raw_articles = [
            RawArticle(
                url="https://example.com/article1",
                title="Middle East Peace Talks Resume",
                content="Diplomatic efforts continue in the region...",
                published_at=datetime.utcnow(),
                media_name="Al Jazeera"
            ),
            RawArticle(
                url="https://example.com/article2",
                title="Tech Innovation in Dubai",
                content="Dubai announces new technology hub...",
                published_at=datetime.utcnow(),
                media_name="Reuters"
            )
        ]

        aj.return_value.fetch.return_value = [raw_articles[0]]
        reuters.return_value.fetch.return_value = [raw_articles[1]]
        bbc.return_value.fetch.return_value = []

        yield aj, reuters, bbc


@pytest.fixture
def mock_filter():
    """Mock MiddleEastFilter that accepts all articles."""
    with patch("middle_east_aggregator.pipeline.MiddleEastFilter") as mock:
        # Return all articles as Middle East content
        mock.return_value.filter.side_effect = lambda articles: articles
        yield mock


@pytest.fixture
def mock_quota_tracker():
    """Mock QuotaTracker with safe quota status."""
    with patch("middle_east_aggregator.pipeline.QuotaTracker") as mock:
        tracker = Mock()

        # Default: SAFE status (usage < 80%)
        status = Mock()
        status.usage_percent = 0.5  # 50%
        status.status = "SAFE"
        tracker.get_quota_status.return_value = status

        # Allow all translations
        tracker.can_translate.return_value = True
        tracker.record_translation.return_value = None

        mock.return_value = tracker
        yield mock


@pytest.fixture
def mock_translator():
    """Mock Translator with successful translations."""
    with patch("middle_east_aggregator.pipeline.Translator") as mock:
        translator = Mock()

        # Return Japanese translations
        translator.translate_article.return_value = (
            "タイトル（日本語）",  # title_ja
            "コンテンツ（日本語）",  # content_ja
            100  # char_count
        )

        mock.return_value = translator
        yield mock


@pytest.fixture
def mock_database():
    """Mock database repositories."""
    with patch("middle_east_aggregator.pipeline.ArticleRepository") as article_repo, \
         patch("middle_east_aggregator.pipeline.ReportRepository") as report_repo:

        article_repo.return_value.save.return_value = None
        report_repo.return_value.save.return_value = None

        yield article_repo, report_repo


@pytest.fixture
def mock_clusterer():
    """Mock TopicClusterer."""
    with patch("middle_east_aggregator.pipeline.TopicClusterer") as mock:
        mock.return_value.cluster.return_value = []  # No clusters for simplicity
        yield mock


@pytest.fixture
def mock_analyzer():
    """Mock BiasAnalyzer."""
    with patch("middle_east_aggregator.pipeline.BiasAnalyzer") as mock:
        yield mock


class TestTranslationPipeline:
    """Integration tests for translation in pipeline."""

    def test_pipeline_translates_articles_in_safe_mode(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test pipeline translates articles when quota is safe."""
        pipeline = NewsPipeline()
        result = pipeline.run()

        # Verify articles were collected
        assert result['articles_collected'] == 2
        assert result['articles_filtered'] == 2

        # Verify translation was attempted
        assert result['articles_translated'] == 2
        assert result['translation_chars_used'] == 200  # 2 articles × 100 chars

        # Verify translator was called
        translator = mock_translator.return_value
        assert translator.translate_article.call_count == 2

        # Verify quota was recorded
        quota_tracker = mock_quota_tracker.return_value
        assert quota_tracker.record_translation.call_count == 2

    def test_pipeline_skips_translation_when_quota_critical(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test pipeline skips translation when quota is critical (≥95%)."""
        # Set quota to CRITICAL
        quota_tracker = mock_quota_tracker.return_value
        status = Mock()
        status.usage_percent = 0.96  # 96%
        status.status = "CRITICAL"
        quota_tracker.get_quota_status.return_value = status

        pipeline = NewsPipeline()
        result = pipeline.run()

        # Verify articles were collected
        assert result['articles_collected'] == 2

        # Verify translation was SKIPPED
        assert result['articles_translated'] == 0
        assert result['translation_chars_used'] == 0

        # Verify translator was NOT called
        translator = mock_translator.return_value
        assert translator.translate_article.call_count == 0

    def test_pipeline_degrades_to_titles_only_at_85_percent(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test pipeline uses TITLES_ONLY mode when quota is 85-95%."""
        # Set quota to 85%
        quota_tracker = mock_quota_tracker.return_value
        status = Mock()
        status.usage_percent = 0.87  # 87%
        status.status = "WARNING"
        quota_tracker.get_quota_status.return_value = status

        pipeline = NewsPipeline()
        result = pipeline.run()

        # Verify translation happened
        assert result['articles_translated'] == 2

        # Verify translator was called with TITLES_ONLY mode
        translator = mock_translator.return_value
        calls = translator.translate_article.call_args_list
        for call in calls:
            args, kwargs = call
            title, content, mode = args
            assert mode == TranslationMode.TITLES_ONLY

    def test_pipeline_respects_daily_quota_limit(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test pipeline respects daily quota limit."""
        # First article allowed, second blocked by quota
        quota_tracker = mock_quota_tracker.return_value
        quota_tracker.can_translate.side_effect = [True, False]

        pipeline = NewsPipeline()
        result = pipeline.run()

        # Only 1 article should be translated
        assert result['articles_translated'] == 1
        assert result['translation_chars_used'] == 100

        # Verify quota check was called twice
        assert quota_tracker.can_translate.call_count == 2

    def test_pipeline_handles_translation_failure_gracefully(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test pipeline continues when translation fails."""
        # Make translator raise exception
        translator = mock_translator.return_value
        translator.translate_article.side_effect = Exception("Translation API error")

        pipeline = NewsPipeline()
        result = pipeline.run()

        # Pipeline should complete despite translation errors
        assert result['status'] == 'success'
        assert result['articles_collected'] == 2

        # No articles translated due to error
        assert result['articles_translated'] == 0

    def test_pipeline_records_quota_only_for_successful_translations(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test quota is only recorded for successful translations."""
        # First translation succeeds, second returns 0 chars (cached or failed)
        translator = mock_translator.return_value
        translator.translate_article.side_effect = [
            ("タイトル", "コンテンツ", 100),  # Success
            ("", "", 0)  # Skipped/cached
        ]

        pipeline = NewsPipeline()
        result = pipeline.run()

        # Only one quota record should be created
        quota_tracker = mock_quota_tracker.return_value
        assert quota_tracker.record_translation.call_count == 1

        # Verify the correct values were recorded
        call_args = quota_tracker.record_translation.call_args
        assert call_args[1]['char_count'] == 100
        assert call_args[1]['success'] is True

    def test_pipeline_saves_translated_articles_to_database(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test translated articles are saved with Japanese fields."""
        pipeline = NewsPipeline()
        result = pipeline.run()

        # Verify articles were saved
        article_repo, _ = mock_database
        assert article_repo.return_value.save.call_count == 2

        # Get the saved articles
        saved_calls = article_repo.return_value.save.call_args_list

        for call in saved_calls:
            article = call[0][0]  # First positional argument

            # Verify article has translation fields populated
            assert article.title_ja == "タイトル（日本語）"
            assert article.content_ja == "コンテンツ（日本語）"
            assert article.char_count_input == 100
            assert article.translation_status == "success"
            assert article.is_middle_east is True

    def test_pipeline_marks_skipped_articles_with_correct_status(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test articles skipped due to quota have correct status."""
        # Block all translations
        quota_tracker = mock_quota_tracker.return_value
        quota_tracker.can_translate.return_value = False

        pipeline = NewsPipeline()
        result = pipeline.run()

        # Verify articles were saved with skipped status
        article_repo, _ = mock_database
        saved_calls = article_repo.return_value.save.call_args_list

        for call in saved_calls:
            article = call[0][0]
            assert article.translation_status == "skipped"
            assert article.title_ja is None
            assert article.content_ja is None
            assert article.char_count_input == 0

    def test_pipeline_end_to_end_flow(
        self,
        mock_collectors,
        mock_filter,
        mock_quota_tracker,
        mock_translator,
        mock_database,
        mock_clusterer,
        mock_analyzer
    ):
        """Test complete pipeline flow from collection to storage."""
        pipeline = NewsPipeline()
        result = pipeline.run()

        # Verify complete flow
        assert result['status'] == 'success'
        assert result['articles_collected'] == 2
        assert result['articles_filtered'] == 2
        assert result['articles_translated'] == 2
        assert result['translation_chars_used'] == 200
        assert result['articles_saved'] == 2

        # Verify duration was tracked
        assert 'duration_seconds' in result
        assert result['duration_seconds'] > 0
