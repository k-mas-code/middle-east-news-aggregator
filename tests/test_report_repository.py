"""
Property-based and unit tests for ReportRepository.

Feature: middle-east-news-aggregator
Validates: Requirements 6.2, 5.5
"""

import pytest
from datetime import datetime
from hypothesis import given, settings
from unittest.mock import patch, MagicMock

from middle_east_aggregator.models import Report
from tests.conftest import report_strategy, create_mock_firestore_client


class TestReportRepositoryProperties:
    """
    Property-based tests for ReportRepository.

    These tests verify universal properties that should hold for all valid inputs.
    """

    @pytest.mark.property
    @given(report=report_strategy())
    @settings(max_examples=100)
    def test_property_9_report_save_roundtrip(self, report):
        """
        Property 9: レポート保存ラウンドトリップ

        任意の Report をデータストアに保存した後、同じIDで取得したとき、
        元のReportと同等のオブジェクトが返される。

        Validates: Requirements 6.2
        Feature: middle-east-news-aggregator, Property 9
        """
        from middle_east_aggregator.database import ReportRepository

        # Given: ReportRepository with mock Firestore client
        mock_firestore_client = create_mock_firestore_client()
        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ReportRepository()

            # When: We save a report
            repo.save(report)

            # Then: We can retrieve it by ID and it equals the original
            retrieved = repo.find_by_id(report.id)

            assert retrieved is not None, "Report should be retrievable after save"
            assert retrieved.id == report.id
            assert retrieved.summary == report.summary
            assert retrieved.cluster.id == report.cluster.id
            assert retrieved.cluster.topic_name == report.cluster.topic_name
            assert len(retrieved.cluster.articles) == len(report.cluster.articles)

    @pytest.mark.property
    @given(report=report_strategy())
    @settings(max_examples=50)
    def test_property_10_search_results_relevance(self, report):
        """
        Property 10: 検索結果関連性

        任意の キーワードで検索したとき、返される全Reportのtopic_nameまたは
        含まれるArticleのtitleにそのキーワードが含まれる。

        Validates: Requirements 5.5
        Feature: middle-east-news-aggregator, Property 10
        """
        from middle_east_aggregator.database import ReportRepository

        # Given: ReportRepository with a saved report
        mock_firestore_client = create_mock_firestore_client()
        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ReportRepository()
            repo.save(report)

            # Extract a keyword from the report's topic_name or first article title
            if len(report.cluster.topic_name) > 5:
                # Use a word from topic_name
                keyword = report.cluster.topic_name.split()[0] if report.cluster.topic_name.split() else report.cluster.topic_name[:5]
            elif report.cluster.articles:
                # Use a word from first article's title
                title = report.cluster.articles[0].title
                keyword = title.split()[0] if title.split() else title[:5]
            else:
                # Skip this test case if we can't extract a keyword
                return

            # When: We search for the keyword
            results = repo.search(keyword)

            # Then: All results should contain the keyword in topic_name or article titles
            for result_report in results:
                keyword_lower = keyword.lower()
                found_in_topic = keyword_lower in result_report.cluster.topic_name.lower()
                found_in_articles = any(
                    keyword_lower in article.title.lower()
                    for article in result_report.cluster.articles
                )

                assert found_in_topic or found_in_articles, \
                    f"Keyword '{keyword}' not found in topic_name or article titles"


class TestReportRepositoryUnit:
    """
    Unit tests for ReportRepository with specific examples and edge cases.
    """

    @pytest.mark.unit
    def test_save_and_find_by_id(self, mock_firestore_client):
        """
        Test saving a report and retrieving it by ID.

        Validates: Requirements 6.2
        """
        from middle_east_aggregator.database import ReportRepository
        from middle_east_aggregator.models import (
            Report,
            Cluster,
            Article,
            ComparisonResult,
            SentimentResult,
            Entity,
        )

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ReportRepository()

            # Create a simple report
            article = Article(
                id="article-1",
                url="https://example.com/article1",
                title="Middle East Peace Talks",
                content="Peace talks are ongoing...",
                published_at=datetime(2024, 3, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 3, 15)
            )

            cluster = Cluster(
                id="cluster-1",
                topic_name="Peace Talks",
                articles=[article],
                media_names=["aljazeera"],
                created_at=datetime(2024, 3, 15)
            )

            comparison = ComparisonResult(
                media_bias_scores={
                    "aljazeera": SentimentResult(polarity=0.5, subjectivity=0.3, label="positive")
                },
                unique_entities_by_media={
                    "aljazeera": [Entity(text="Israel", label="GPE", count=3)]
                },
                common_entities=[],
                bias_diff=0.0
            )

            report = Report(
                id="report-1",
                cluster=cluster,
                comparison=comparison,
                generated_at=datetime(2024, 3, 15),
                summary="Peace talks summary"
            )

            # Save and retrieve
            repo.save(report)
            retrieved = repo.find_by_id("report-1")

            assert retrieved is not None
            assert retrieved.id == "report-1"
            assert retrieved.summary == "Peace talks summary"

    @pytest.mark.unit
    def test_find_by_id_nonexistent(self, mock_firestore_client):
        """
        Test finding a report by ID that doesn't exist.

        Validates: Requirements 6.2
        """
        from middle_east_aggregator.database import ReportRepository

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ReportRepository()

            result = repo.find_by_id("nonexistent-id")

            assert result is None

    @pytest.mark.unit
    def test_find_all(self, mock_firestore_client):
        """
        Test retrieving all reports.

        Validates: Requirements 6.2
        """
        from middle_east_aggregator.database import ReportRepository
        from middle_east_aggregator.models import (
            Report,
            Cluster,
            Article,
            ComparisonResult,
            SentimentResult,
        )

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ReportRepository()

            # Create two simple reports
            for i in range(2):
                article = Article(
                    id=f"article-{i}",
                    url=f"https://example.com/article{i}",
                    title=f"Article {i}",
                    content="Content",
                    published_at=datetime(2024, 3, 15),
                    media_name="aljazeera",
                    is_middle_east=True,
                    collected_at=datetime(2024, 3, 15)
                )

                cluster = Cluster(
                    id=f"cluster-{i}",
                    topic_name=f"Topic {i}",
                    articles=[article],
                    media_names=["aljazeera"],
                    created_at=datetime(2024, 3, 15)
                )

                comparison = ComparisonResult(
                    media_bias_scores={
                        "aljazeera": SentimentResult(polarity=0.0, subjectivity=0.5, label="neutral")
                    },
                    unique_entities_by_media={"aljazeera": []},
                    common_entities=[],
                    bias_diff=0.0
                )

                report = Report(
                    id=f"report-{i}",
                    cluster=cluster,
                    comparison=comparison,
                    generated_at=datetime(2024, 3, 15),
                    summary=f"Summary {i}"
                )

                repo.save(report)

            # Retrieve all
            all_reports = repo.find_all()

            assert len(all_reports) == 2
            report_ids = [r.id for r in all_reports]
            assert "report-0" in report_ids
            assert "report-1" in report_ids

    @pytest.mark.unit
    def test_search_by_topic_name(self, mock_firestore_client):
        """
        Test searching reports by keyword in topic_name.

        Validates: Requirements 5.5
        """
        from middle_east_aggregator.database import ReportRepository
        from middle_east_aggregator.models import (
            Report,
            Cluster,
            Article,
            ComparisonResult,
            SentimentResult,
        )

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ReportRepository()

            # Create report with specific topic
            article = Article(
                id="article-1",
                url="https://example.com/article1",
                title="Article about Gaza",
                content="Content",
                published_at=datetime(2024, 3, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 3, 15)
            )

            cluster = Cluster(
                id="cluster-1",
                topic_name="Gaza Conflict Analysis",
                articles=[article],
                media_names=["aljazeera"],
                created_at=datetime(2024, 3, 15)
            )

            comparison = ComparisonResult(
                media_bias_scores={
                    "aljazeera": SentimentResult(polarity=0.0, subjectivity=0.5, label="neutral")
                },
                unique_entities_by_media={"aljazeera": []},
                common_entities=[],
                bias_diff=0.0
            )

            report = Report(
                id="report-1",
                cluster=cluster,
                comparison=comparison,
                generated_at=datetime(2024, 3, 15),
                summary="Summary"
            )

            repo.save(report)

            # Search by keyword in topic_name
            results = repo.search("Gaza")

            assert len(results) == 1
            assert results[0].id == "report-1"

            # Search by non-matching keyword
            results = repo.search("Syria")

            assert len(results) == 0
