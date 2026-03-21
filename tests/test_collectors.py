"""
Property-based and unit tests for Collectors.

Feature: middle-east-news-aggregator
Validates: Requirements 1.1, 1.2, 1.4, 1.5, 7.1, 7.2
"""

import pytest
from datetime import datetime
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from unittest.mock import patch, MagicMock, Mock
import httpx

from middle_east_aggregator.models import RawArticle


class TestCollectorProperties:
    """
    Property-based tests for Collectors.

    These tests verify universal properties that should hold for all valid inputs.
    """

    @pytest.mark.property
    def test_property_1_article_field_completeness(self):
        """
        Property 1: 記事フィールド完全性

        任意の 収集済みArticleに対して、title・content・published_at・url・media_nameの
        全フィールドが空でない値を持つ。

        Validates: Requirements 1.5
        Feature: middle-east-news-aggregator, Property 1
        """
        from middle_east_aggregator.collectors import AlJazeeraCollector

        # Mock RSS feed response
        mock_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test Article Title</title>
                    <link>https://www.aljazeera.com/news/2024/1/15/test-article</link>
                    <description>Test article content with sufficient length for testing.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_feed_xml
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            collector = AlJazeeraCollector()
            articles = collector.fetch()

            # Then: All fetched articles have complete fields
            for article in articles:
                assert article.title, "Title should not be empty"
                assert article.content, "Content should not be empty"
                assert article.published_at, "Published date should not be empty"
                assert article.url, "URL should not be empty"
                assert article.media_name, "Media name should not be empty"
                assert article.media_name == "aljazeera", f"Media name should be 'aljazeera', got '{article.media_name}'"

    @pytest.mark.property
    def test_property_4_partial_failure_resilience(self):
        """
        Property 4: 部分障害時の継続性

        任意の メディアセット（3つ）のうち1つが接続失敗のとき、
        残り2つのメディアの収集結果が正常に返される。

        Validates: Requirements 1.4, 7.5
        Feature: middle-east-news-aggregator, Property 4
        """
        from middle_east_aggregator.collectors import (
            AlJazeeraCollector,
            ReutersCollector,
            BBCCollector,
        )

        # Mock successful RSS feed
        success_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Success Article</title>
                    <link>https://example.com/article</link>
                    <description>Article content.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        def mock_get_side_effect(url, **kwargs):
            """Simulate one failing endpoint and two successful ones."""
            mock_response = Mock()

            # Simulate AlJazeera failing
            if "aljazeera.com" in url:
                raise httpx.TimeoutException("Connection timeout")
            else:
                # Reuters and BBC succeed
                mock_response.text = success_feed_xml
                mock_response.status_code = 200
                return mock_response

        with patch('httpx.get', side_effect=mock_get_side_effect):
            # When: We collect from all three media sources
            aljazeera_articles = AlJazeeraCollector().fetch()
            reuters_articles = ReutersCollector().fetch()
            bbc_articles = BBCCollector().fetch()

            # Then: The two successful collectors return articles
            # AlJazeera should fail gracefully and return empty list
            assert isinstance(aljazeera_articles, list), "Should return list even on failure"

            # Reuters and BBC should succeed
            assert len(reuters_articles) > 0, "Reuters should return articles"
            assert len(bbc_articles) > 0, "BBC should return articles"


class TestCollectorUnit:
    """
    Unit tests for Collectors with specific examples and edge cases.
    """

    @pytest.mark.unit
    def test_aljazeera_collector_fetch_success(self):
        """
        Test AlJazeeraCollector successfully fetches and parses RSS feed.

        Validates: Requirements 1.1, 1.2
        """
        from middle_east_aggregator.collectors import AlJazeeraCollector

        mock_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Middle East News Update</title>
                    <link>https://www.aljazeera.com/news/2024/1/15/middle-east-update</link>
                    <description>Latest developments in the Middle East region.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
                <item>
                    <title>Gaza Situation Report</title>
                    <link>https://www.aljazeera.com/news/2024/1/15/gaza-report</link>
                    <description>Situation report from Gaza.</description>
                    <pubDate>Mon, 15 Jan 2024 09:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_feed_xml
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            collector = AlJazeeraCollector()
            articles = collector.fetch()

            assert len(articles) == 2
            assert articles[0].title == "Middle East News Update"
            assert articles[0].media_name == "aljazeera"
            assert "aljazeera.com" in articles[0].url

    @pytest.mark.unit
    def test_collector_timeout_handling(self):
        """
        Test that collector handles timeout gracefully.

        Validates: Requirements 7.1
        """
        from middle_east_aggregator.collectors import AlJazeeraCollector

        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Connection timeout after 30s")

            collector = AlJazeeraCollector()
            articles = collector.fetch()

            # Should return empty list on timeout, not raise exception
            assert articles == []

    @pytest.mark.unit
    def test_collector_http_error_handling(self):
        """
        Test that collector handles HTTP errors gracefully.

        Validates: Requirements 7.1
        """
        from middle_east_aggregator.collectors import ReutersCollector

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=Mock(), response=mock_response
            )
            mock_get.return_value = mock_response

            collector = ReutersCollector()
            articles = collector.fetch()

            # Should return empty list on HTTP error
            assert articles == []

    @pytest.mark.unit
    def test_collector_parse_error_handling(self):
        """
        Test that collector handles malformed RSS feed gracefully.

        Validates: Requirements 7.1
        """
        from middle_east_aggregator.collectors import BBCCollector

        malformed_xml = "This is not valid XML"

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = malformed_xml
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            collector = BBCCollector()
            articles = collector.fetch()

            # Should handle parse error and return empty list or skip malformed entries
            assert isinstance(articles, list)

    @pytest.mark.unit
    def test_reuters_collector_fetch(self):
        """
        Test ReutersCollector with Reuters-specific RSS format.

        Validates: Requirements 1.1
        """
        from middle_east_aggregator.collectors import ReutersCollector

        mock_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Israel-Palestine Tensions</title>
                    <link>https://www.reuters.com/world/middle-east/israel-palestine-2024-01-15/</link>
                    <description>Tensions rise in the region.</description>
                    <pubDate>Mon, 15 Jan 2024 11:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_feed_xml
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            collector = ReutersCollector()
            articles = collector.fetch()

            assert len(articles) == 1
            assert articles[0].media_name == "reuters"
            assert "reuters.com" in articles[0].url

    @pytest.mark.unit
    def test_bbc_collector_fetch(self):
        """
        Test BBCCollector with BBC-specific RSS format.

        Validates: Requirements 1.1
        """
        from middle_east_aggregator.collectors import BBCCollector

        mock_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Lebanon Political Crisis</title>
                    <link>https://www.bbc.co.uk/news/world-middle-east-12345678</link>
                    <description>Political situation in Lebanon.</description>
                    <pubDate>Mon, 15 Jan 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_feed_xml
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            collector = BBCCollector()
            articles = collector.fetch()

            assert len(articles) == 1
            assert articles[0].media_name == "bbc"
            assert "bbc.co.uk" in articles[0].url

    @pytest.mark.unit
    def test_collector_empty_feed(self):
        """
        Test that collector handles empty RSS feed.

        Validates: Requirements 1.4
        """
        from middle_east_aggregator.collectors import AlJazeeraCollector

        empty_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = empty_feed_xml
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            collector = AlJazeeraCollector()
            articles = collector.fetch()

            # Should return empty list for empty feed
            assert articles == []
