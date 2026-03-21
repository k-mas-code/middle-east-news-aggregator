"""
Topic clustering for grouping related articles.

Uses TF-IDF vectorization and cosine similarity to cluster articles by topic.
"""

import logging
import uuid
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from middle_east_aggregator.models import Article, Cluster

logger = logging.getLogger(__name__)


class TopicClusterer:
    """
    Clusters articles by topic using TF-IDF and cosine similarity.

    Groups similar articles together and assigns topic names based on
    common terms.
    """

    def __init__(self, similarity_threshold: float = 0.3):
        """
        Initialize clusterer with similarity threshold.

        Args:
            similarity_threshold: Minimum similarity score (0-1) for articles
                                to be considered part of the same cluster.
                                Higher values create more granular clusters.
        """
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            min_df=1,
            max_df=0.8
        )

    def cluster(self, articles: list[Article]) -> list[Cluster]:
        """
        Cluster articles by topic similarity.

        Args:
            articles: List of articles to cluster

        Returns:
            List of Cluster objects, each containing related articles
        """
        if not articles:
            logger.info("No articles to cluster")
            return []

        if len(articles) == 1:
            # Single article becomes its own cluster
            logger.info("Single article, creating single cluster")
            return [self._create_cluster([articles[0]])]

        # Combine title and content for better clustering
        texts = [f"{article.title} {article.content}" for article in articles]

        try:
            # Vectorize texts using TF-IDF
            tfidf_matrix = self.vectorizer.fit_transform(texts)

            # Calculate cosine similarity matrix
            similarity_matrix = cosine_similarity(tfidf_matrix)

            # Perform clustering based on similarity
            clusters_dict = self._group_by_similarity(articles, similarity_matrix)

            # Convert to Cluster objects
            clusters = [
                self._create_cluster(cluster_articles)
                for cluster_articles in clusters_dict.values()
            ]

            logger.info(f"Created {len(clusters)} clusters from {len(articles)} articles")

            return clusters

        except Exception as e:
            logger.error(f"Error during clustering: {e}")
            # Fallback: treat each article as separate cluster
            return [self._create_cluster([article]) for article in articles]

    def _group_by_similarity(
        self, articles: list[Article], similarity_matrix: np.ndarray
    ) -> dict[int, list[Article]]:
        """
        Group articles into clusters based on similarity matrix.

        Uses a simple greedy algorithm: iterate through articles and assign
        to existing cluster if similar enough, or create new cluster.

        Args:
            articles: List of articles
            similarity_matrix: NxN matrix of cosine similarities

        Returns:
            Dictionary mapping cluster ID to list of articles
        """
        clusters = {}
        article_to_cluster = {}
        next_cluster_id = 0

        for i, article in enumerate(articles):
            if i in article_to_cluster:
                # Already assigned to a cluster
                continue

            # Check if similar to any existing cluster
            assigned = False
            for cluster_id, cluster_articles in clusters.items():
                # Get representative article index from cluster
                representative_idx = articles.index(cluster_articles[0])

                # Check similarity
                if similarity_matrix[i, representative_idx] >= self.similarity_threshold:
                    clusters[cluster_id].append(article)
                    article_to_cluster[i] = cluster_id
                    assigned = True
                    break

            if not assigned:
                # Create new cluster
                clusters[next_cluster_id] = [article]
                article_to_cluster[i] = next_cluster_id
                next_cluster_id += 1

        return clusters

    def _create_cluster(self, articles: list[Article]) -> Cluster:
        """
        Create a Cluster object from a list of articles.

        Args:
            articles: List of articles in the cluster

        Returns:
            Cluster object with generated topic name
        """
        # Extract unique media names
        media_names = list(set(article.media_name for article in articles))

        # Generate topic name from articles
        topic_name = self._assign_topic_name(articles)

        return Cluster(
            id=uuid.uuid4().hex,
            topic_name=topic_name,
            articles=articles,
            media_names=media_names,
            created_at=datetime.utcnow()
        )

    def _assign_topic_name(self, articles: list[Article]) -> str:
        """
        Generate a topic name for a cluster based on common terms.

        Extracts top TF-IDF terms from the cluster's articles.

        Args:
            articles: List of articles in the cluster

        Returns:
            Generated topic name string
        """
        if not articles:
            return "Unknown Topic"

        if len(articles) == 1:
            # Use first few words of the title
            title_words = articles[0].title.split()[:5]
            return " ".join(title_words)

        # Combine all texts
        texts = [f"{article.title} {article.content}" for article in articles]
        combined_text = " ".join(texts)

        try:
            # Create a small vectorizer for this cluster
            vectorizer = TfidfVectorizer(
                max_features=5,
                stop_words='english',
                ngram_range=(1, 2)  # Include bigrams for better context
            )

            tfidf = vectorizer.fit_transform([combined_text])

            # Get feature names (terms)
            feature_names = vectorizer.get_feature_names_out()

            if len(feature_names) > 0:
                # Use top 3 terms as topic name
                top_terms = feature_names[:3]
                topic_name = " ".join(top_terms).title()
                return topic_name if topic_name else articles[0].title.split()[0]
            else:
                # Fallback to first article's title
                return articles[0].title.split()[0]

        except Exception as e:
            logger.warning(f"Error generating topic name: {e}")
            # Fallback to first article's title
            title_words = articles[0].title.split()[:3]
            return " ".join(title_words) if title_words else "Unknown Topic"
