"""
Data access layer using Google Cloud Firestore.

Provides repository classes for persisting and retrieving articles and reports.
"""

from datetime import datetime
from typing import Optional
from google.cloud import firestore
from google.api_core import exceptions as gcp_exceptions

from middle_east_aggregator.models import Article, Report


class ArticleRepository:
    """
    Repository for Article persistence using Firestore.

    Handles CRUD operations and queries for news articles.
    """

    def __init__(self):
        """Initialize Firestore client and collection reference."""
        self.db = firestore.Client()
        self.collection = self.db.collection("articles")

    def save(self, article: Article) -> None:
        """
        Save or update an article in Firestore.

        Uses upsert logic: if an article with the same URL exists, updates it;
        otherwise, creates a new document.

        Args:
            article: The article to save

        Raises:
            Exception: If Firestore write fails
        """
        try:
            # Convert Article to dictionary for Firestore
            article_dict = {
                "id": article.id,
                "url": article.url,
                "title": article.title,
                "content": article.content,
                "published_at": article.published_at,
                "media_name": article.media_name,
                "is_middle_east": article.is_middle_east,
                "collected_at": article.collected_at,
            }

            # Use article.id as document ID for idempotent saves
            doc_ref = self.collection.document(article.id)
            doc_ref.set(article_dict, merge=True)

        except Exception as e:
            # Re-raise to ensure Property 12 (write failure rollback) is testable
            raise

    def find_by_url(self, url: str) -> Optional[Article]:
        """
        Find an article by its URL.

        Args:
            url: The article URL to search for

        Returns:
            The matching Article if found, None otherwise
        """
        try:
            # Query by URL field
            query = self.collection.where("url", "==", url).limit(1)
            docs = list(query.stream())

            if not docs:
                return None

            doc = docs[0]
            data = doc.to_dict()

            return Article(
                id=data["id"],
                url=data["url"],
                title=data["title"],
                content=data["content"],
                published_at=data["published_at"],
                media_name=data["media_name"],
                is_middle_east=data["is_middle_east"],
                collected_at=data["collected_at"],
            )

        except Exception:
            return None

    def find_by_date_range(
        self, start: datetime, end: datetime
    ) -> list[Article]:
        """
        Find all articles published within a date range.

        Args:
            start: Start of date range (inclusive)
            end: End of date range (inclusive)

        Returns:
            List of articles published between start and end dates
        """
        try:
            query = (
                self.collection.where("published_at", ">=", start)
                .where("published_at", "<=", end)
            )

            articles = []
            for doc in query.stream():
                data = doc.to_dict()
                article = Article(
                    id=data["id"],
                    url=data["url"],
                    title=data["title"],
                    content=data["content"],
                    published_at=data["published_at"],
                    media_name=data["media_name"],
                    is_middle_east=data["is_middle_east"],
                    collected_at=data["collected_at"],
                )
                articles.append(article)

            return articles

        except Exception:
            return []

    def delete_older_than(self, cutoff_date: datetime) -> int:
        """
        Delete articles collected before a cutoff date.

        Implements data retention policy (e.g., delete articles older than 30 days).

        Args:
            cutoff_date: Articles collected before this date will be deleted

        Returns:
            Number of articles deleted
        """
        try:
            query = self.collection.where("collected_at", "<", cutoff_date)

            deleted_count = 0
            for doc in query.stream():
                doc.reference.delete()
                deleted_count += 1

            return deleted_count

        except Exception:
            return 0


class ReportRepository:
    """
    Repository for Report persistence using Firestore.

    Handles CRUD operations and queries for analysis reports.
    """

    def __init__(self):
        """Initialize Firestore client and collection reference."""
        self.db = firestore.Client()
        self.collection = self.db.collection("reports")

    def save(self, report: Report) -> None:
        """
        Save a report in Firestore.

        Args:
            report: The report to save

        Raises:
            Exception: If Firestore write fails
        """
        try:
            # Convert Report to dictionary (will need custom serialization for nested objects)
            report_dict = {
                "id": report.id,
                "cluster_id": report.cluster.id,
                "summary": report.summary,
                "generated_at": report.generated_at,
                # Store comparison and cluster as nested structures
                "comparison": self._serialize_comparison(report.comparison),
                "cluster": self._serialize_cluster(report.cluster),
            }

            doc_ref = self.collection.document(report.id)
            doc_ref.set(report_dict, merge=True)

        except Exception as e:
            raise

    def find_all(self) -> list[Report]:
        """
        Retrieve all reports.

        Returns:
            List of all reports
        """
        try:
            reports = []
            for doc in self.collection.stream():
                data = doc.to_dict()
                report = self._deserialize_report(data)
                if report:
                    reports.append(report)

            return reports

        except Exception:
            return []

    def find_by_id(self, report_id: str) -> Optional[Report]:
        """
        Find a report by its ID.

        Args:
            report_id: The report ID to search for

        Returns:
            The matching Report if found, None otherwise
        """
        try:
            doc = self.collection.document(report_id).get()

            if not doc.exists:
                return None

            data = doc.to_dict()
            return self._deserialize_report(data)

        except Exception:
            return None

    def search(self, keyword: str) -> list[Report]:
        """
        Search reports by keyword in topic_name or article titles.

        Note: Firestore does not support full-text search natively.
        This is a simplified implementation that filters results client-side.

        Args:
            keyword: The keyword to search for

        Returns:
            List of reports matching the keyword
        """
        try:
            # Fetch all reports and filter client-side
            # (Firestore doesn't have native full-text search)
            all_reports = self.find_all()

            keyword_lower = keyword.lower()
            matching_reports = []

            for report in all_reports:
                # Search in topic_name
                if keyword_lower in report.cluster.topic_name.lower():
                    matching_reports.append(report)
                    continue

                # Search in article titles
                for article in report.cluster.articles:
                    if keyword_lower in article.title.lower():
                        matching_reports.append(report)
                        break

            return matching_reports

        except Exception:
            return []

    def _serialize_comparison(self, comparison) -> dict:
        """Serialize ComparisonResult to dictionary."""
        from middle_east_aggregator.models import ComparisonResult

        return {
            "media_bias_scores": {
                media: {
                    "polarity": score.polarity,
                    "subjectivity": score.subjectivity,
                    "label": score.label,
                }
                for media, score in comparison.media_bias_scores.items()
            },
            "unique_entities_by_media": {
                media: [
                    {"text": e.text, "label": e.label, "count": e.count}
                    for e in entities
                ]
                for media, entities in comparison.unique_entities_by_media.items()
            },
            "common_entities": [
                {"text": e.text, "label": e.label, "count": e.count}
                for e in comparison.common_entities
            ],
            "bias_diff": comparison.bias_diff,
        }

    def _serialize_cluster(self, cluster) -> dict:
        """Serialize Cluster to dictionary."""
        return {
            "id": cluster.id,
            "topic_name": cluster.topic_name,
            "media_names": cluster.media_names,
            "created_at": cluster.created_at,
            "articles": [
                {
                    "id": a.id,
                    "url": a.url,
                    "title": a.title,
                    "content": a.content,
                    "published_at": a.published_at,
                    "media_name": a.media_name,
                    "is_middle_east": a.is_middle_east,
                    "collected_at": a.collected_at,
                }
                for a in cluster.articles
            ],
        }

    def _deserialize_report(self, data: dict) -> Optional[Report]:
        """Deserialize dictionary to Report."""
        try:
            from middle_east_aggregator.models import (
                Report,
                Cluster,
                Article,
                ComparisonResult,
                SentimentResult,
                Entity,
            )

            # Deserialize cluster
            cluster_data = data["cluster"]
            articles = [
                Article(
                    id=a["id"],
                    url=a["url"],
                    title=a["title"],
                    content=a["content"],
                    published_at=a["published_at"],
                    media_name=a["media_name"],
                    is_middle_east=a["is_middle_east"],
                    collected_at=a["collected_at"],
                )
                for a in cluster_data["articles"]
            ]

            cluster = Cluster(
                id=cluster_data["id"],
                topic_name=cluster_data["topic_name"],
                articles=articles,
                media_names=cluster_data["media_names"],
                created_at=cluster_data["created_at"],
            )

            # Deserialize comparison
            comp_data = data["comparison"]
            media_bias_scores = {
                media: SentimentResult(
                    polarity=score["polarity"],
                    subjectivity=score["subjectivity"],
                    label=score["label"],
                )
                for media, score in comp_data["media_bias_scores"].items()
            }

            unique_entities_by_media = {
                media: [
                    Entity(text=e["text"], label=e["label"], count=e["count"])
                    for e in entities
                ]
                for media, entities in comp_data["unique_entities_by_media"].items()
            }

            common_entities = [
                Entity(text=e["text"], label=e["label"], count=e["count"])
                for e in comp_data["common_entities"]
            ]

            comparison = ComparisonResult(
                media_bias_scores=media_bias_scores,
                unique_entities_by_media=unique_entities_by_media,
                common_entities=common_entities,
                bias_diff=comp_data["bias_diff"],
            )

            # Create Report
            report = Report(
                id=data["id"],
                cluster=cluster,
                comparison=comparison,
                generated_at=data["generated_at"],
                summary=data["summary"],
            )

            return report

        except Exception:
            return None
