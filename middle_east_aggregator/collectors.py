"""
News collectors for fetching articles from RSS feeds.

Provides collector classes for Al Jazeera, Reuters, and BBC.
"""

import logging
from datetime import datetime
from typing import Literal
import httpx
import feedparser
from email.utils import parsedate_to_datetime

from middle_east_aggregator.models import RawArticle

logger = logging.getLogger(__name__)


class BaseCollector:
    """
    Base class for news collectors.

    Handles common RSS feed fetching and parsing logic.
    """

    def __init__(self, media_name: Literal["aljazeera", "reuters", "bbc"], feed_urls: list[str]):
        """
        Initialize collector with media name and feed URLs.

        Args:
            media_name: Name of the media source
            feed_urls: List of RSS feed URLs to collect from
        """
        self.media_name = media_name
        self.feed_urls = feed_urls
        self.timeout = 30.0  # 30 second timeout as per requirements

    def fetch(self) -> list[RawArticle]:
        """
        Fetch articles from all configured RSS feeds.

        Returns:
            List of RawArticle objects collected from feeds.
            Returns empty list if all feeds fail.
        """
        all_articles = []

        for feed_url in self.feed_urls:
            try:
                articles = self._parse_feed(feed_url)
                all_articles.extend(articles)
                logger.info(f"Successfully fetched {len(articles)} articles from {feed_url}")

            except httpx.TimeoutException as e:
                logger.error(f"Timeout fetching {feed_url}: {e}")
                # Continue with other feeds
                continue

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching {feed_url}: {e}")
                # Continue with other feeds
                continue

            except Exception as e:
                logger.error(f"Unexpected error fetching {feed_url}: {e}")
                # Continue with other feeds
                continue

        return all_articles

    def _parse_feed(self, feed_url: str) -> list[RawArticle]:
        """
        Parse a single RSS feed and extract articles.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            List of RawArticle objects

        Raises:
            httpx.TimeoutException: If request times out
            httpx.HTTPStatusError: If HTTP error occurs
        """
        # Fetch feed content with timeout
        response = httpx.get(feed_url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()

        # Parse RSS feed
        feed = feedparser.parse(response.text)

        articles = []
        for entry in feed.entries:
            try:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)

            except Exception as e:
                logger.warning(f"Error parsing entry from {feed_url}: {e}")
                # Skip malformed entries
                continue

        return articles

    def _parse_entry(self, entry) -> RawArticle | None:
        """
        Parse a single RSS entry into a RawArticle.

        Args:
            entry: feedparser entry object

        Returns:
            RawArticle if parsing succeeds, None otherwise
        """
        try:
            # Extract title
            title = entry.get('title', '').strip()
            if not title:
                return None

            # Extract URL
            url = entry.get('link', '').strip()
            if not url:
                return None

            # Extract content (try description, summary, or content)
            content = ''
            if 'description' in entry:
                content = entry.description
            elif 'summary' in entry:
                content = entry.summary
            elif 'content' in entry and entry.content:
                content = entry.content[0].value

            content = content.strip()
            if not content:
                return None

            # Extract published date
            published_at = None
            if 'published_parsed' in entry and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6])
            elif 'published' in entry:
                try:
                    published_at = parsedate_to_datetime(entry.published)
                except Exception:
                    pass

            # Fallback to current time if no date found
            if not published_at:
                published_at = datetime.utcnow()

            return RawArticle(
                url=url,
                title=title,
                content=content,
                published_at=published_at,
                media_name=self.media_name
            )

        except Exception as e:
            logger.warning(f"Error parsing entry: {e}")
            return None


class AlJazeeraCollector(BaseCollector):
    """
    Collector for Al Jazeera news articles.

    Fetches from Al Jazeera's RSS feeds.
    """

    def __init__(self):
        """Initialize Al Jazeera collector with feed URLs."""
        super().__init__(
            media_name="aljazeera",
            feed_urls=[
                "https://www.aljazeera.com/xml/rss/all.xml"
            ]
        )


class ReutersCollector(BaseCollector):
    """
    Collector for Reuters news articles.

    Fetches from Reuters' RSS feeds.
    """

    def __init__(self):
        """Initialize Reuters collector with feed URLs."""
        super().__init__(
            media_name="reuters",
            feed_urls=[
                "https://feeds.reuters.com/reuters/topNews"
            ]
        )


class BBCCollector(BaseCollector):
    """
    Collector for BBC news articles.

    Fetches from BBC's Middle East RSS feed.
    """

    def __init__(self):
        """Initialize BBC collector with feed URLs."""
        super().__init__(
            media_name="bbc",
            feed_urls=[
                "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"
            ]
        )
