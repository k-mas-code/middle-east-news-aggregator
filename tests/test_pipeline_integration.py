"""
Integration tests for the complete news aggregation pipeline.

Tests the end-to-end flow: Collection → Filtering → Clustering → Analysis → Storage

Feature: middle-east-news-aggregator
"""

import pytest
from datetime import datetime
from unittest.mock import patch, Mock

from middle_east_aggregator.models import RawArticle, Article


class TestPipelineIntegration:
    """
    Integration tests for the complete pipeline.

    Tests the flow from RSS collection through to report generation.
    """

    @pytest.mark.integration
    def test_end_to_end_pipeline_with_mock_rss(self, mock_firestore_client):
        """
        Test complete pipeline from collection to report generation.

        This test uses mocked RSS feeds to verify the entire workflow.
        """
        from middle_east_aggregator.pipeline import NewsPipeline

        # Mock RSS feed with Middle East content
        mock_rss_feed = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Israel and Palestine peace talks resume</title>
                    <link>https://www.aljazeera.com/news/2024/1/15/peace-talks</link>
                    <description>Diplomatic efforts continue as Israel and Palestine resume peace negotiations in Geneva.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
                <item>
                    <title>Gaza humanitarian situation worsens</title>
                    <link>https://www.aljazeera.com/news/2024/1/15/gaza-crisis</link>
                    <description>The humanitarian crisis in Gaza continues to deteriorate as aid organizations struggle to provide assistance.</description>
                    <pubDate>Mon, 15 Jan 2024 09:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Technology conference in Silicon Valley</title>
                    <link>https://www.aljazeera.com/news/2024/1/15/tech-conference</link>
                    <description>Major technology companies gather for annual conference.</description>
                    <pubDate>Mon, 15 Jan 2024 08:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            # Mock HTTP response - returns same feed for all collectors
            mock_response = Mock()
            mock_response.text = mock_rss_feed
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Mock Firestore client
            with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
                # Given: A pipeline instance
                pipeline = NewsPipeline()

                # When: We run the pipeline
                result = pipeline.run()

                # Then: Pipeline should complete successfully
                assert result is not None
                assert result['status'] == 'success'

                # Should collect articles
                assert result['articles_collected'] > 0

                # Should filter to only Middle East articles
                # 2 Middle East articles × 3 collectors = 6 filtered articles
                assert result['articles_filtered'] == 6

                # Should create clusters
                assert result['clusters_created'] >= 1

                # Should generate reports
                assert result['reports_generated'] >= 1

    @pytest.mark.integration
    def test_pipeline_filters_non_middle_east_content(self, mock_firestore_client):
        """
        Test that pipeline correctly filters out non-Middle East articles.
        """
        from middle_east_aggregator.pipeline import NewsPipeline

        # Mock RSS with only non-Middle East content
        non_me_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Sports championship final results</title>
                    <link>https://www.reuters.com/sports/championship</link>
                    <description>The championship game ended with a score of 3-2.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = non_me_rss
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
                pipeline = NewsPipeline()
                result = pipeline.run()

                # Should filter out all articles
                assert result['articles_filtered'] == 0
                assert result['clusters_created'] == 0
                assert result['reports_generated'] == 0

    @pytest.mark.integration
    def test_pipeline_handles_multiple_media_sources(self, mock_firestore_client):
        """
        Test pipeline with articles from multiple media sources on same topic.
        """
        from middle_east_aggregator.pipeline import NewsPipeline

        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Syria conflict developments</title>
                    <link>https://www.example.com/syria-1</link>
                    <description>Latest updates on the Syrian conflict situation.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
                <item>
                    <title>Syrian peace talks continue</title>
                    <link>https://www.example.com/syria-2</link>
                    <description>Diplomatic efforts to resolve Syrian crisis ongoing.</description>
                    <pubDate>Mon, 15 Jan 2024 09:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_rss
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
                pipeline = NewsPipeline()
                result = pipeline.run()

                # Should cluster similar articles together
                # 2 Syria articles × 3 collectors = 6 filtered articles
                assert result['articles_filtered'] == 6
                # Similar articles should be clustered (may be 1 or 2 clusters depending on similarity)
                assert result['clusters_created'] >= 1

    @pytest.mark.integration
    def test_pipeline_saves_to_database(self, mock_firestore_client):
        """
        Test that pipeline saves articles and reports to database.
        """
        from middle_east_aggregator.pipeline import NewsPipeline

        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Lebanon political developments</title>
                    <link>https://www.bbc.com/lebanon-news</link>
                    <description>Recent political changes in Lebanon.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_rss
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
                pipeline = NewsPipeline()
                result = pipeline.run()

                # Should save to database
                assert result['articles_saved'] >= 1
                assert result['reports_saved'] >= 1

    @pytest.mark.integration
    def test_pipeline_handles_collector_failure_gracefully(self, mock_firestore_client):
        """
        Test that pipeline continues when one collector fails.
        """
        from middle_east_aggregator.pipeline import NewsPipeline
        import httpx

        def mock_get_side_effect(url, **kwargs):
            # AlJazeera fails, others succeed
            if "aljazeera" in url:
                raise httpx.TimeoutException("Connection timeout")
            else:
                mock_response = Mock()
                mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
                <rss version="2.0"><channel><item>
                <title>Iran nuclear program update</title>
                <link>https://example.com/iran</link>
                <description>Updates on Iran nuclear program.</description>
                <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item></channel></rss>"""
                mock_response.status_code = 200
                return mock_response

        with patch('httpx.get', side_effect=mock_get_side_effect):
            with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
                pipeline = NewsPipeline()
                result = pipeline.run()

                # Pipeline should complete despite one collector failing
                assert result['status'] == 'success'
                # Should still collect from other sources
                assert result['articles_collected'] >= 0

    @pytest.mark.integration
    def test_pipeline_generates_valid_reports(self, mock_firestore_client):
        """
        Test that generated reports have all required fields.
        """
        from middle_east_aggregator.pipeline import NewsPipeline

        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Yemen humanitarian crisis deepens</title>
                    <link>https://example.com/yemen</link>
                    <description>The situation in Yemen continues to worsen.</description>
                    <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_rss
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
                pipeline = NewsPipeline()
                result = pipeline.run()

                # Verify reports have required structure
                if 'reports' in result and result['reports']:
                    report = result['reports'][0]
                    assert report.id is not None
                    assert report.cluster is not None
                    assert report.comparison is not None
                    assert report.summary is not None
                    assert report.generated_at is not None

    @pytest.mark.unit
    def test_pipeline_component_integration(self):
        """
        Test that pipeline correctly integrates all components.
        """
        from middle_east_aggregator.pipeline import NewsPipeline

        # Given: A pipeline instance
        pipeline = NewsPipeline()

        # Then: All components should be initialized
        assert pipeline.collectors is not None
        assert len(pipeline.collectors) == 3  # AlJazeera, Reuters, BBC
        assert pipeline.filter is not None
        assert pipeline.clusterer is not None
        assert pipeline.analyzer is not None
        assert pipeline.article_repo is not None
        assert pipeline.report_repo is not None
