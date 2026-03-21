"""
Main pipeline for news aggregation, filtering, clustering, and analysis.

Orchestrates the complete workflow from RSS collection to report generation.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from middle_east_aggregator.collectors import (
    AlJazeeraCollector,
    ReutersCollector,
    BBCCollector,
)
from middle_east_aggregator.filters import MiddleEastFilter
from middle_east_aggregator.clusterer import TopicClusterer
from middle_east_aggregator.analyzer import BiasAnalyzer
from middle_east_aggregator.database import ArticleRepository, ReportRepository
from middle_east_aggregator.models import Article, RawArticle

logger = logging.getLogger(__name__)


class NewsPipeline:
    """
    Complete news aggregation and analysis pipeline.

    Orchestrates: Collection → Filtering → Clustering → Analysis → Storage
    """

    def __init__(self):
        """Initialize pipeline with all components."""
        # Collectors for each media source
        self.collectors = [
            AlJazeeraCollector(),
            ReutersCollector(),
            BBCCollector(),
        ]

        # Processing components
        self.filter = MiddleEastFilter()
        self.clusterer = TopicClusterer()
        self.analyzer = BiasAnalyzer()

        # Data repositories
        self.article_repo = ArticleRepository()
        self.report_repo = ReportRepository()

        logger.info("Pipeline initialized with all components")

    def run(self) -> dict:
        """
        Execute the complete pipeline.

        Returns:
            Dictionary with pipeline execution results and statistics
        """
        logger.info("Starting pipeline execution")
        start_time = datetime.utcnow()

        result = {
            'status': 'success',
            'started_at': start_time,
            'articles_collected': 0,
            'articles_filtered': 0,
            'clusters_created': 0,
            'reports_generated': 0,
            'articles_saved': 0,
            'reports_saved': 0,
            'reports': [],
            'errors': []
        }

        try:
            # Step 1: Collect articles from all sources
            logger.info("Step 1: Collecting articles from RSS feeds")
            raw_articles = self._collect_articles()
            result['articles_collected'] = len(raw_articles)
            logger.info(f"Collected {len(raw_articles)} articles")

            if not raw_articles:
                logger.warning("No articles collected, pipeline ending")
                result['status'] = 'no_articles'
                return result

            # Step 2: Convert to Article objects and filter for Middle East content
            logger.info("Step 2: Converting and filtering articles")
            articles = self._convert_to_articles(raw_articles)
            filtered_articles = self.filter.filter(articles)
            result['articles_filtered'] = len(filtered_articles)
            logger.info(f"Filtered to {len(filtered_articles)} Middle East articles")

            if not filtered_articles:
                logger.warning("No Middle East articles after filtering")
                result['status'] = 'no_relevant_articles'
                return result

            # Step 3: Save filtered articles to database
            logger.info("Step 3: Saving articles to database")
            saved_count = self._save_articles(filtered_articles)
            result['articles_saved'] = saved_count
            logger.info(f"Saved {saved_count} articles to database")

            # Step 4: Cluster articles by topic
            logger.info("Step 4: Clustering articles by topic")
            clusters = self.clusterer.cluster(filtered_articles)
            result['clusters_created'] = len(clusters)
            logger.info(f"Created {len(clusters)} topic clusters")

            if not clusters:
                logger.warning("No clusters created")
                return result

            # Step 5: Analyze clusters and generate reports
            logger.info("Step 5: Analyzing clusters and generating reports")
            reports = []
            for cluster in clusters:
                try:
                    report = self.analyzer.analyze(cluster)
                    reports.append(report)
                except Exception as e:
                    logger.error(f"Error analyzing cluster {cluster.id}: {e}")
                    result['errors'].append(str(e))

            result['reports_generated'] = len(reports)
            result['reports'] = reports
            logger.info(f"Generated {len(reports)} analysis reports")

            # Step 6: Save reports to database
            logger.info("Step 6: Saving reports to database")
            reports_saved = self._save_reports(reports)
            result['reports_saved'] = reports_saved
            logger.info(f"Saved {reports_saved} reports to database")

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            result['status'] = 'error'
            result['errors'].append(str(e))

        # Calculate execution time
        end_time = datetime.utcnow()
        result['completed_at'] = end_time
        result['duration_seconds'] = (end_time - start_time).total_seconds()

        logger.info(f"Pipeline completed with status: {result['status']}")
        logger.info(f"Execution time: {result['duration_seconds']:.2f} seconds")

        return result

    def _collect_articles(self) -> list[RawArticle]:
        """
        Collect articles from all configured collectors.

        Returns:
            List of raw articles from all sources
        """
        all_articles = []

        for collector in self.collectors:
            try:
                articles = collector.fetch()
                all_articles.extend(articles)
                logger.info(f"Collected {len(articles)} articles from {collector.media_name}")

            except Exception as e:
                logger.error(f"Error collecting from {collector.media_name}: {e}")
                # Continue with other collectors

        return all_articles

    def _convert_to_articles(self, raw_articles: list[RawArticle]) -> list[Article]:
        """
        Convert RawArticle objects to Article objects with IDs.

        Args:
            raw_articles: List of raw articles

        Returns:
            List of Article objects with generated IDs
        """
        articles = []

        for raw in raw_articles:
            article = Article(
                id=uuid.uuid4().hex,
                url=raw.url,
                title=raw.title,
                content=raw.content,
                published_at=raw.published_at,
                media_name=raw.media_name,
                is_middle_east=False,  # Will be determined by filter
                collected_at=datetime.utcnow()
            )
            articles.append(article)

        return articles

    def _save_articles(self, articles: list[Article]) -> int:
        """
        Save articles to database.

        Args:
            articles: List of articles to save

        Returns:
            Number of articles successfully saved
        """
        saved_count = 0

        for article in articles:
            try:
                # Mark as Middle East article since it passed filter
                article.is_middle_east = True
                self.article_repo.save(article)
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving article {article.id}: {e}")

        return saved_count

    def _save_reports(self, reports: list) -> int:
        """
        Save reports to database.

        Args:
            reports: List of Report objects to save

        Returns:
            Number of reports successfully saved
        """
        saved_count = 0

        for report in reports:
            try:
                self.report_repo.save(report)
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving report {report.id}: {e}")

        return saved_count
