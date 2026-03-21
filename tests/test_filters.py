"""
Property-based and unit tests for MiddleEastFilter.

Feature: middle-east-news-aggregator
Validates: Requirements 2.1, 2.2, 2.3, 2.4
"""

import pytest
from datetime import datetime
from hypothesis import given, settings
from hypothesis import strategies as st

from middle_east_aggregator.models import RawArticle
from tests.conftest import article_strategy


class TestMiddleEastFilterProperties:
    """
    Property-based tests for MiddleEastFilter.

    These tests verify universal properties that should hold for all valid inputs.
    """

    @pytest.mark.property
    @given(keyword=st.sampled_from([
        "Israel", "Palestine", "Gaza", "Lebanon", "Syria", "Iran",
        "Iraq", "Yemen", "Saudi Arabia", "Egypt", "Jordan", "Middle East"
    ]))
    @settings(max_examples=50)
    def test_property_5_filtering_accuracy(self, keyword):
        """
        Property 5: フィルタリング正確性

        任意の 記事セットに対してフィルタリングを適用したとき、
        返される全記事のタイトルまたは本文に中東関連キーワードが少なくとも1つ含まれる。

        Validates: Requirements 2.1, 2.2
        Feature: middle-east-news-aggregator, Property 5
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        # Given: Articles with and without middle east keywords
        articles = [
            RawArticle(
                url=f"https://example.com/article-with-{keyword.replace(' ', '-')}",
                title=f"Article about {keyword}",
                content=f"This article discusses {keyword} and related topics.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera"
            ),
            RawArticle(
                url="https://example.com/article-without",
                title="Article about Sports",
                content="This article is about football and basketball.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters"
            )
        ]

        # When: We apply the filter
        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        # Then: All filtered articles contain middle east keywords
        for article in filtered:
            keyword_lower = keyword.lower()
            found_in_title = keyword_lower in article.title.lower()
            found_in_content = keyword_lower in article.content.lower()

            assert found_in_title or found_in_content, \
                f"Filtered article should contain keyword '{keyword}' in title or content"


class TestMiddleEastFilterUnit:
    """
    Unit tests for MiddleEastFilter with specific examples and edge cases.
    """

    @pytest.mark.unit
    def test_filter_with_israel_keyword(self):
        """
        Test filtering articles with 'Israel' keyword.

        Validates: Requirements 2.1
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = [
            RawArticle(
                url="https://example.com/israel-article",
                title="Israel announces new policy",
                content="Details about Israel's new policy.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera"
            ),
            RawArticle(
                url="https://example.com/sports-article",
                title="Football match results",
                content="The match ended 2-1.",
                published_at=datetime(2024, 1, 15),
                media_name="bbc"
            )
        ]

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        assert len(filtered) == 1
        assert "Israel" in filtered[0].title

    @pytest.mark.unit
    def test_filter_case_insensitive(self):
        """
        Test that filter is case-insensitive.

        Validates: Requirements 2.1
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = [
            RawArticle(
                url="https://example.com/article1",
                title="Article about gaza situation",  # lowercase
                content="Details about the situation.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters"
            ),
            RawArticle(
                url="https://example.com/article2",
                title="Article about SYRIA conflict",  # uppercase
                content="Conflict details.",
                published_at=datetime(2024, 1, 15),
                media_name="bbc"
            )
        ]

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        assert len(filtered) == 2

    @pytest.mark.unit
    def test_filter_keyword_in_content(self):
        """
        Test filtering when keyword is only in content, not title.

        Validates: Requirements 2.2
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = [
            RawArticle(
                url="https://example.com/article",
                title="Political developments",
                content="The situation in Lebanon continues to evolve.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera"
            )
        ]

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        assert len(filtered) == 1

    @pytest.mark.unit
    def test_filter_multiple_keywords(self):
        """
        Test article with multiple middle east keywords.

        Validates: Requirements 2.1
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = [
            RawArticle(
                url="https://example.com/article",
                title="Iran and Iraq discuss regional cooperation",
                content="Leaders from Iran and Iraq met to discuss cooperation.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters"
            )
        ]

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        assert len(filtered) == 1

    @pytest.mark.unit
    def test_filter_empty_list(self):
        """
        Test filtering with empty article list.

        Validates: Requirements 2.4
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = []

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        assert filtered == []

    @pytest.mark.unit
    def test_filter_no_matches(self):
        """
        Test filtering when no articles match.

        Validates: Requirements 2.4
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = [
            RawArticle(
                url="https://example.com/tech",
                title="New smartphone released",
                content="Technology company releases new device.",
                published_at=datetime(2024, 1, 15),
                media_name="bbc"
            ),
            RawArticle(
                url="https://example.com/weather",
                title="Weather forecast",
                content="Sunny weather expected tomorrow.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters"
            )
        ]

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        # Should return empty list when no matches
        assert filtered == []

    @pytest.mark.unit
    def test_is_relevant_method(self):
        """
        Test the is_relevant helper method.

        Validates: Requirements 2.1, 2.2
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        filter_instance = MiddleEastFilter()

        # Relevant article (keyword in title)
        relevant_article = RawArticle(
            url="https://example.com/article1",
            title="Palestine news update",
            content="News content.",
            published_at=datetime(2024, 1, 15),
            media_name="aljazeera"
        )

        # Relevant article (keyword in content)
        relevant_article2 = RawArticle(
            url="https://example.com/article2",
            title="Regional news",
            content="Developments in Yemen are significant.",
            published_at=datetime(2024, 1, 15),
            media_name="reuters"
        )

        # Non-relevant article
        non_relevant_article = RawArticle(
            url="https://example.com/article3",
            title="Technology news",
            content="New app released.",
            published_at=datetime(2024, 1, 15),
            media_name="bbc"
        )

        assert filter_instance.is_relevant(relevant_article) is True
        assert filter_instance.is_relevant(relevant_article2) is True
        assert filter_instance.is_relevant(non_relevant_article) is False

    @pytest.mark.unit
    def test_filter_compound_keywords(self):
        """
        Test filtering with compound keywords like 'Middle East'.

        Validates: Requirements 2.1
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = [
            RawArticle(
                url="https://example.com/article",
                title="Middle East peace talks continue",
                content="Diplomatic efforts ongoing.",
                published_at=datetime(2024, 1, 15),
                media_name="aljazeera"
            )
        ]

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        assert len(filtered) == 1

    @pytest.mark.unit
    def test_filter_partial_word_match(self):
        """
        Test that partial word matches are handled correctly.

        For example, 'Iranian' should match 'Iran'.

        Validates: Requirements 2.1
        """
        from middle_east_aggregator.filters import MiddleEastFilter

        articles = [
            RawArticle(
                url="https://example.com/article",
                title="Iranian officials make statement",
                content="Officials from the Iranian government spoke.",
                published_at=datetime(2024, 1, 15),
                media_name="reuters"
            )
        ]

        filter_instance = MiddleEastFilter()
        filtered = filter_instance.filter(articles)

        # Should match because 'Iran' is in 'Iranian'
        assert len(filtered) == 1
