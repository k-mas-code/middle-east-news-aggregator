"""
Filters for identifying Middle East related articles.

Provides keyword-based filtering to identify relevant news articles.
"""

import logging
from middle_east_aggregator.models import RawArticle

logger = logging.getLogger(__name__)


class MiddleEastFilter:
    """
    Filter for identifying Middle East related articles.

    Uses keyword matching to determine if articles are relevant to
    Middle East news coverage.
    """

    # Middle East related keywords
    KEYWORDS = [
        "Israel",
        "Palestine",
        "Gaza",
        "West Bank",
        "Lebanon",
        "Syria",
        "Iran",
        "Iraq",
        "Yemen",
        "Saudi Arabia",
        "Saudi",
        "Egypt",
        "Jordan",
        "Middle East",
        "Hezbollah",
        "Hamas",
        "Netanyahu",
        "Assad",
        "Tehran",
        "Baghdad",
        "Damascus",
        "Beirut",
        "Jerusalem",
        "Tel Aviv",
        "West Bank",
        "Golan Heights",
        "Arab",
        "Israeli",
        "Palestinian",
    ]

    def filter(self, articles: list[RawArticle]) -> list[RawArticle]:
        """
        Filter articles to include only Middle East related content.

        Args:
            articles: List of raw articles to filter

        Returns:
            List of articles that contain Middle East keywords
        """
        if not articles:
            logger.info("No articles to filter")
            return []

        filtered = [article for article in articles if self.is_relevant(article)]

        included_count = len(filtered)
        excluded_count = len(articles) - included_count

        logger.info(
            f"Filtered {len(articles)} articles: "
            f"{included_count} included, {excluded_count} excluded"
        )

        if included_count == 0:
            logger.warning("No articles matched Middle East keywords")

        return filtered

    def is_relevant(self, article: RawArticle) -> bool:
        """
        Check if an article is relevant to Middle East news.

        Searches for Middle East keywords in both title and content.
        Matching is case-insensitive.

        Args:
            article: The article to check

        Returns:
            True if article contains at least one Middle East keyword,
            False otherwise
        """
        # Combine title and content for searching
        text = f"{article.title} {article.content}".lower()

        # Check if any keyword is present
        for keyword in self.KEYWORDS:
            if keyword.lower() in text:
                return True

        return False
