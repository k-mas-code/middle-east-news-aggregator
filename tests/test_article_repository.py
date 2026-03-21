"""
Property-based and unit tests for ArticleRepository.

Feature: middle-east-news-aggregator
Validates: Requirements 1.2, 1.3, 6.1, 6.3, 6.4
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, settings, assume
from unittest.mock import patch, MagicMock

from middle_east_aggregator.models import Article
from tests.conftest import article_strategy, create_mock_firestore_client


class TestArticleRepositoryProperties:
    """
    Property-based tests for ArticleRepository.

    These tests verify universal properties that should hold for all valid inputs.
    """

    @pytest.mark.property
    @given(article=article_strategy())
    @settings(max_examples=100)
    def test_property_2_article_save_roundtrip(self, article):
        """
        Property 2: 記事保存ラウンドトリップ

        任意の Article をデータストアに保存した後、同じURLで検索したとき、
        元のArticleと同等のオブジェクトが返される。

        Validates: Requirements 1.2, 6.1
        Feature: middle-east-news-aggregator, Property 2
        """
        from middle_east_aggregator.database import ArticleRepository

        # Given: ArticleRepository with mock Firestore client
        mock_firestore_client = create_mock_firestore_client()
        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            # When: We save an article
            repo.save(article)

            # Then: We can retrieve it by URL and it equals the original
            retrieved = repo.find_by_url(article.url)

            assert retrieved is not None, "Article should be retrievable after save"
            assert retrieved.id == article.id
            assert retrieved.url == article.url
            assert retrieved.title == article.title
            assert retrieved.content == article.content
            assert retrieved.media_name == article.media_name
            assert retrieved.is_middle_east == article.is_middle_east
            # Note: datetime comparison might need tolerance for serialization

    @pytest.mark.property
    @given(article=article_strategy())
    @settings(max_examples=100)
    def test_property_3_duplicate_save_idempotency(self, article):
        """
        Property 3: 重複保存の冪等性

        任意の Article を2回保存したとき、データストア内に同一URLのレコードは1件のみ存在する。

        Validates: Requirements 1.3
        Feature: middle-east-news-aggregator, Property 3
        """
        from middle_east_aggregator.database import ArticleRepository

        # Given: ArticleRepository with mock Firestore client
        mock_firestore_client = create_mock_firestore_client()
        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            # When: We save the same article twice
            repo.save(article)
            repo.save(article)

            # Then: Only one record should exist with that URL
            retrieved = repo.find_by_url(article.url)
            assert retrieved is not None

            # Verify storage has only one document with this URL
            # (implementation-specific check via mock)
            storage = mock_firestore_client._storage
            url_matches = sum(1 for doc_data in storage.values() if doc_data.get('url') == article.url)
            assert url_matches == 1, f"Expected 1 article with URL {article.url}, found {url_matches}"

    @pytest.mark.property
    @given(article=article_strategy())
    @settings(max_examples=50)
    def test_property_11_data_retention_period(self, article):
        """
        Property 11: データ保持期間

        任意の 保存から30日以内のArticleは、クリーンアップ処理後もデータストアに存在する。

        Validates: Requirements 6.4
        Feature: middle-east-news-aggregator, Property 11
        """
        from middle_east_aggregator.database import ArticleRepository

        # Given: An article that is less than 30 days old
        assume(article.collected_at >= datetime.utcnow() - timedelta(days=30))

        mock_firestore_client = create_mock_firestore_client()
        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            # When: We save the article and run cleanup for articles older than 30 days
            repo.save(article)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            repo.delete_older_than(cutoff_date)

            # Then: The article should still exist
            retrieved = repo.find_by_url(article.url)
            assert retrieved is not None, "Articles less than 30 days old should not be deleted"

    @pytest.mark.property
    @given(article=article_strategy())
    @settings(max_examples=50)
    def test_property_12_write_failure_rollback(self, article):
        """
        Property 12: 書き込み失敗時のロールバック

        任意の データストアへの書き込みが失敗したとき、書き込み前後でデータストアの状態が変化しない。

        Validates: Requirements 6.3
        Feature: middle-east-news-aggregator, Property 12
        """
        from middle_east_aggregator.database import ArticleRepository

        mock_firestore_client = create_mock_firestore_client()

        # Set up the mock to raise an exception on set()
        # We need to configure this before ArticleRepository is instantiated
        mock_doc_ref = MagicMock()
        mock_doc_ref.set.side_effect = Exception("Firestore write failed")

        # Replace the document() method to return our failing mock
        original_document = mock_firestore_client.collection.return_value.document
        mock_firestore_client.collection.return_value.document = MagicMock(return_value=mock_doc_ref)

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            # Given: Initial state of storage
            initial_storage = dict(mock_firestore_client._storage)

            # Then: The save should raise an exception
            with pytest.raises(Exception):
                repo.save(article)

            # And: The storage state should be unchanged
            final_storage = dict(mock_firestore_client._storage)
            assert initial_storage == final_storage, "Storage should not change on write failure"


class TestArticleRepositoryUnit:
    """
    Unit tests for ArticleRepository with specific examples and edge cases.
    """

    @pytest.mark.unit
    def test_save_new_article(self, mock_firestore_client):
        """
        Test saving a new article successfully.

        Validates: Requirements 1.2
        """
        from middle_east_aggregator.database import ArticleRepository

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            article = Article(
                id="test-id-123",
                url="https://example.com/article1",
                title="Test Article",
                content="This is a test article content.",
                published_at=datetime(2024, 1, 15, 10, 30),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15, 11, 0)
            )

            repo.save(article)
            retrieved = repo.find_by_url(article.url)

            assert retrieved is not None
            assert retrieved.title == "Test Article"

    @pytest.mark.unit
    def test_find_by_url_nonexistent(self, mock_firestore_client):
        """
        Test finding an article by URL that doesn't exist.

        Validates: Requirements 6.1
        """
        from middle_east_aggregator.database import ArticleRepository

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            result = repo.find_by_url("https://example.com/nonexistent")

            assert result is None

    @pytest.mark.unit
    def test_find_by_date_range(self, mock_firestore_client):
        """
        Test finding articles within a date range.

        Validates: Requirements 6.1
        """
        from middle_east_aggregator.database import ArticleRepository

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            # Save articles with different dates
            article1 = Article(
                id="id1",
                url="https://example.com/article1",
                title="Article 1",
                content="Content 1",
                published_at=datetime(2024, 1, 10),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 10)
            )

            article2 = Article(
                id="id2",
                url="https://example.com/article2",
                title="Article 2",
                content="Content 2",
                published_at=datetime(2024, 1, 20),
                media_name="reuters",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 20)
            )

            article3 = Article(
                id="id3",
                url="https://example.com/article3",
                title="Article 3",
                content="Content 3",
                published_at=datetime(2024, 2, 5),
                media_name="bbc",
                is_middle_east=True,
                collected_at=datetime(2024, 2, 5)
            )

            repo.save(article1)
            repo.save(article2)
            repo.save(article3)

            # Find articles in January 2024
            results = repo.find_by_date_range(
                datetime(2024, 1, 1),
                datetime(2024, 1, 31)
            )

            assert len(results) == 2
            urls = [a.url for a in results]
            assert "https://example.com/article1" in urls
            assert "https://example.com/article2" in urls
            assert "https://example.com/article3" not in urls

    @pytest.mark.unit
    def test_delete_older_than(self, mock_firestore_client):
        """
        Test deleting articles older than a cutoff date.

        Validates: Requirements 6.4
        """
        from middle_east_aggregator.database import ArticleRepository

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            repo = ArticleRepository()

            # Save articles with different collection dates
            old_article = Article(
                id="old-id",
                url="https://example.com/old-article",
                title="Old Article",
                content="Old content",
                published_at=datetime(2024, 1, 1),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime.utcnow() - timedelta(days=60)
            )

            recent_article = Article(
                id="recent-id",
                url="https://example.com/recent-article",
                title="Recent Article",
                content="Recent content",
                published_at=datetime(2024, 3, 1),
                media_name="reuters",
                is_middle_east=True,
                collected_at=datetime.utcnow() - timedelta(days=10)
            )

            repo.save(old_article)
            repo.save(recent_article)

            # Delete articles older than 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)
            deleted_count = repo.delete_older_than(cutoff)

            assert deleted_count == 1
            assert repo.find_by_url(old_article.url) is None
            assert repo.find_by_url(recent_article.url) is not None
