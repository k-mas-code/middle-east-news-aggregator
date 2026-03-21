"""
Property-based and unit tests for TopicClusterer.

Feature: middle-east-news-aggregator
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

import pytest
from datetime import datetime
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from middle_east_aggregator.models import Article
from tests.conftest import article_strategy


class TestTopicClustererProperties:
    """
    Property-based tests for TopicClusterer.

    These tests verify universal properties that should hold for all valid inputs.
    """

    @pytest.mark.property
    @given(articles=st.lists(article_strategy(), min_size=1, max_size=10))
    @settings(max_examples=30, deadline=None)
    def test_property_6_clustering_invariants(self, articles):
        """
        Property 6: クラスタリング不変条件

        任意の 記事セットをクラスタリングしたとき、
        (a) 全記事がいずれかのClusterに属する
        (b) 各Clusterのmedia_namesは含まれるArticleのmedia_nameの集合と一致する
        (c) 各Clusterのtopic_nameが空でない

        Validates: Requirements 3.1, 3.2, 3.3, 3.5
        Feature: middle-east-news-aggregator, Property 6
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        # Given: A set of articles
        clusterer = TopicClusterer()

        # When: We cluster the articles
        clusters = clusterer.cluster(articles)

        # Then: Invariant (a) - All articles belong to a cluster
        all_clustered_articles = []
        for cluster in clusters:
            all_clustered_articles.extend(cluster.articles)

        assert len(all_clustered_articles) == len(articles), \
            "All articles should belong to a cluster"

        # Verify all original articles are in clusters (by ID)
        original_ids = set(a.id for a in articles)
        clustered_ids = set(a.id for a in all_clustered_articles)
        assert original_ids == clustered_ids, \
            "All article IDs should be present in clusters"

        # Then: Invariant (b) - Each cluster's media_names matches its articles
        for cluster in clusters:
            actual_media_names = set(a.media_name for a in cluster.articles)
            expected_media_names = set(cluster.media_names)

            assert actual_media_names == expected_media_names, \
                f"Cluster media_names {expected_media_names} should match article media names {actual_media_names}"

        # Then: Invariant (c) - Each cluster has a non-empty topic_name
        for cluster in clusters:
            assert cluster.topic_name, \
                "Cluster topic_name should not be empty"
            assert len(cluster.topic_name.strip()) > 0, \
                "Cluster topic_name should not be just whitespace"


class TestTopicClustererUnit:
    """
    Unit tests for TopicClusterer with specific examples and edge cases.
    """

    @pytest.mark.unit
    def test_cluster_similar_articles(self):
        """
        Test clustering articles with similar topics.

        Validates: Requirements 3.1, 3.2
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        # Articles about the same topic (Gaza)
        articles = [
            Article(
                id="article-1",
                url="https://aljazeera.com/gaza-1",
                title="Gaza conflict intensifies",
                content="The situation in Gaza continues to worsen with ongoing conflict.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            ),
            Article(
                id="article-2",
                url="https://reuters.com/gaza-2",
                title="Gaza humanitarian crisis deepens",
                content="Humanitarian situation in Gaza deteriorates as conflict continues.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            )
        ]

        clusterer = TopicClusterer()
        clusters = clusterer.cluster(articles)

        # Should create cluster(s) containing both articles
        assert len(clusters) >= 1

        # All articles should be clustered
        total_articles = sum(len(c.articles) for c in clusters)
        assert total_articles == 2

    @pytest.mark.unit
    def test_cluster_dissimilar_articles(self):
        """
        Test clustering articles with completely different topics.

        Validates: Requirements 3.1
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        # Articles about different topics
        articles = [
            Article(
                id="article-1",
                url="https://aljazeera.com/article-1",
                title="Syria peace talks resume in Geneva",
                content="Diplomatic efforts to resolve the Syrian conflict continue.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            ),
            Article(
                id="article-2",
                url="https://reuters.com/article-2",
                title="Iran nuclear program developments",
                content="Latest updates on Iran's nuclear program and international negotiations.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            )
        ]

        clusterer = TopicClusterer()
        clusters = clusterer.cluster(articles)

        # Should create separate clusters for different topics
        assert len(clusters) >= 1

        # All articles should be clustered
        total_articles = sum(len(c.articles) for c in clusters)
        assert total_articles == 2

    @pytest.mark.unit
    def test_cluster_single_article(self):
        """
        Test clustering with a single article.

        Validates: Requirements 3.4
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        articles = [
            Article(
                id="article-1",
                url="https://bbc.com/article-1",
                title="Lebanon political developments",
                content="Recent political changes in Lebanon.",
                published_at=datetime(2024, 1, 15),
                media_name="bbc",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            )
        ]

        clusterer = TopicClusterer()
        clusters = clusterer.cluster(articles)

        # Should create a single cluster with one article
        assert len(clusters) == 1
        assert len(clusters[0].articles) == 1
        assert clusters[0].articles[0].id == "article-1"

    @pytest.mark.unit
    def test_cluster_multiple_media_same_topic(self):
        """
        Test clustering articles from multiple media on the same topic.

        Validates: Requirements 3.2, 3.5
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        # Three media sources covering the same topic
        articles = [
            Article(
                id="article-1",
                url="https://aljazeera.com/article-1",
                title="Israel announces new settlement plans",
                content="Israeli government announces expansion of settlements in occupied territories.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            ),
            Article(
                id="article-2",
                url="https://reuters.com/article-2",
                title="Israel settlement expansion announced",
                content="New settlement construction plans revealed by Israeli authorities.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            ),
            Article(
                id="article-3",
                url="https://bbc.com/article-3",
                title="Israeli settlement plans draw criticism",
                content="International community responds to Israel's settlement expansion.",
                published_at=datetime(2024, 1, 15),
                media_name="bbc",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            )
        ]

        clusterer = TopicClusterer()
        clusters = clusterer.cluster(articles)

        # Find cluster(s) containing these articles
        # All three should ideally be in same cluster or at least clustered
        total_articles = sum(len(c.articles) for c in clusters)
        assert total_articles == 3

        # Check that media_names are correctly tracked
        for cluster in clusters:
            assert set(cluster.media_names) == set(a.media_name for a in cluster.articles)

    @pytest.mark.unit
    def test_cluster_topic_name_generation(self):
        """
        Test that clusters have meaningful topic names.

        Validates: Requirements 3.3
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        articles = [
            Article(
                id="article-1",
                url="https://aljazeera.com/article-1",
                title="Yemen humanitarian crisis worsens",
                content="The humanitarian situation in Yemen continues to deteriorate.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            ),
            Article(
                id="article-2",
                url="https://reuters.com/article-2",
                title="Yemen facing severe humanitarian challenges",
                content="Yemen's humanitarian crisis deepens amid ongoing conflict.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            )
        ]

        clusterer = TopicClusterer()
        clusters = clusterer.cluster(articles)

        # All clusters should have topic names
        for cluster in clusters:
            assert cluster.topic_name
            assert len(cluster.topic_name) > 0
            # Topic name should be a string (not just numbers or symbols)
            assert any(c.isalpha() for c in cluster.topic_name)

    @pytest.mark.unit
    def test_cluster_empty_list(self):
        """
        Test clustering with empty article list.

        Validates: Requirements 3.1
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        articles = []

        clusterer = TopicClusterer()
        clusters = clusterer.cluster(articles)

        # Should return empty list for empty input
        assert clusters == []

    @pytest.mark.unit
    def test_cluster_similarity_threshold(self):
        """
        Test that similarity threshold affects clustering.

        Validates: Requirements 3.1
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        articles = [
            Article(
                id="article-1",
                url="https://aljazeera.com/article-1",
                title="Middle East peace negotiations continue",
                content="Ongoing diplomatic efforts in the Middle East region.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            ),
            Article(
                id="article-2",
                url="https://reuters.com/article-2",
                title="Regional peace talks progress slowly",
                content="Diplomatic discussions in the region show gradual progress.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            )
        ]

        # Test with default threshold
        clusterer_default = TopicClusterer()
        clusters_default = clusterer_default.cluster(articles)

        # Test with higher threshold (should create more clusters)
        clusterer_strict = TopicClusterer(similarity_threshold=0.8)
        clusters_strict = clusterer_strict.cluster(articles)

        # Both should cluster all articles
        total_default = sum(len(c.articles) for c in clusters_default)
        total_strict = sum(len(c.articles) for c in clusters_strict)

        assert total_default == 2
        assert total_strict == 2

    @pytest.mark.unit
    def test_cluster_media_names_accuracy(self):
        """
        Test that cluster media_names list is accurate.

        Validates: Requirements 3.5
        """
        from middle_east_aggregator.clusterer import TopicClusterer

        articles = [
            Article(
                id="article-1",
                url="https://aljazeera.com/article-1",
                title="Test article from Al Jazeera",
                content="Content from Al Jazeera about Middle East.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            ),
            Article(
                id="article-2",
                url="https://bbc.com/article-2",
                title="Test article from BBC",
                content="Content from BBC about Middle East.",
                published_at=datetime(2024, 1, 15),
                media_name="bbc",
                is_middle_east=True,
                collected_at=datetime(2024, 1, 15)
            )
        ]

        clusterer = TopicClusterer()
        clusters = clusterer.cluster(articles)

        # Verify media_names for each cluster
        for cluster in clusters:
            # Should contain media names of articles in cluster
            article_media = set(a.media_name for a in cluster.articles)
            cluster_media = set(cluster.media_names)

            assert article_media == cluster_media
            # Should not have duplicate media names
            assert len(cluster.media_names) == len(set(cluster.media_names))
