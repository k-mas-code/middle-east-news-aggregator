"""
Bias analysis and sentiment detection for news articles.

Provides sentiment analysis, entity extraction, and comparative bias detection.
"""

import logging
import uuid
from datetime import datetime
from collections import Counter
from typing import Literal
import spacy
from textblob import TextBlob

from middle_east_aggregator.models import (
    Cluster,
    Article,
    Report,
    ComparisonResult,
    SentimentResult,
    Entity,
)

logger = logging.getLogger(__name__)

# Load spaCy model (using small English model)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
    # Create a blank English model as fallback
    nlp = spacy.blank("en")


class BiasAnalyzer:
    """
    Analyzes articles for sentiment bias and entity coverage.

    Uses TextBlob for sentiment analysis and spaCy for entity extraction.
    """

    def analyze(self, cluster: Cluster) -> Report:
        """
        Analyze a cluster of articles and generate a comparative report.

        Args:
            cluster: Cluster of related articles to analyze

        Returns:
            Report containing bias analysis and comparison results
        """
        if not cluster.articles:
            logger.warning("Empty cluster provided for analysis")
            # Return minimal report for empty cluster
            return self._create_empty_report(cluster)

        # Perform comparative analysis
        comparison = self._compare_articles(cluster.articles)

        # Generate summary
        summary = self._generate_summary(cluster, comparison)

        # Create report
        report = Report(
            id=uuid.uuid4().hex,
            cluster=cluster,
            comparison=comparison,
            generated_at=datetime.utcnow(),
            summary=summary
        )

        logger.info(f"Generated report for cluster '{cluster.topic_name}' with {len(cluster.articles)} articles")

        return report

    def _sentiment_score(self, text: str) -> SentimentResult:
        """
        Calculate sentiment score for text using TextBlob.

        Args:
            text: Text to analyze

        Returns:
            SentimentResult with polarity, subjectivity, and label
        """
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # Range: -1.0 to 1.0
            subjectivity = blob.sentiment.subjectivity  # Range: 0.0 to 1.0

            # Determine label based on polarity
            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"

            return SentimentResult(
                polarity=polarity,
                subjectivity=subjectivity,
                label=label
            )

        except Exception as e:
            logger.error(f"Error calculating sentiment: {e}")
            # Return neutral sentiment on error
            return SentimentResult(polarity=0.0, subjectivity=0.5, label="neutral")

    def _extract_entities(self, text: str) -> list[Entity]:
        """
        Extract named entities from text using spaCy.

        Args:
            text: Text to extract entities from

        Returns:
            List of Entity objects with text, label, and count
        """
        try:
            doc = nlp(text)

            # Count entities by (text, label) pair
            entity_counts = Counter()

            for ent in doc.ents:
                # Only extract specific entity types
                if ent.label_ in ["PERSON", "GPE", "ORG", "LOC"]:
                    entity_counts[(ent.text, ent.label_)] += 1

            # Convert to Entity objects
            entities = [
                Entity(text=text, label=label, count=count)
                for (text, label), count in entity_counts.items()
            ]

            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    def _compare_articles(self, articles: list[Article]) -> ComparisonResult:
        """
        Compare articles and calculate bias differences.

        Args:
            articles: List of articles to compare

        Returns:
            ComparisonResult with media bias scores and entity differences
        """
        # Group articles by media
        articles_by_media = {}
        for article in articles:
            if article.media_name not in articles_by_media:
                articles_by_media[article.media_name] = []
            articles_by_media[article.media_name].append(article)

        # Calculate bias scores for each media
        media_bias_scores = {}
        for media_name, media_articles in articles_by_media.items():
            # Combine text from all articles by this media
            combined_text = " ".join(
                f"{article.title} {article.content}" for article in media_articles
            )
            media_bias_scores[media_name] = self._sentiment_score(combined_text)

        # Extract entities by media
        unique_entities_by_media = {}
        all_entities = []

        for media_name, media_articles in articles_by_media.items():
            media_entities = []
            for article in media_articles:
                text = f"{article.title} {article.content}"
                entities = self._extract_entities(text)
                media_entities.extend(entities)
                all_entities.extend(entities)

            unique_entities_by_media[media_name] = media_entities

        # Find common entities (entities mentioned by multiple media)
        entity_text_counts = Counter()
        for entity in all_entities:
            entity_text_counts[entity.text] += 1

        # Common entities are those mentioned multiple times
        common_entity_texts = {
            text for text, count in entity_text_counts.items() if count > 1
        }

        common_entities = [
            Entity(text=text, label="GPE", count=entity_text_counts[text])
            for text in common_entity_texts
        ]

        # Calculate bias_diff (maximum polarity difference)
        if len(media_bias_scores) >= 2:
            polarities = [score.polarity for score in media_bias_scores.values()]
            bias_diff = max(polarities) - min(polarities)
        else:
            bias_diff = 0.0

        return ComparisonResult(
            media_bias_scores=media_bias_scores,
            unique_entities_by_media=unique_entities_by_media,
            common_entities=common_entities,
            bias_diff=bias_diff
        )

    def _generate_summary(self, cluster: Cluster, comparison: ComparisonResult) -> str:
        """
        Generate a text summary of the analysis.

        Args:
            cluster: The analyzed cluster
            comparison: Comparison results

        Returns:
            Summary text
        """
        num_articles = len(cluster.articles)
        num_media = len(cluster.media_names)

        summary_parts = [
            f"Analysis of '{cluster.topic_name}' covering {num_articles} articles from {num_media} media source(s)."
        ]

        # Add bias information
        if comparison.bias_diff > 0.3:
            summary_parts.append(f"Significant bias difference detected (diff: {comparison.bias_diff:.2f}).")
        elif comparison.bias_diff > 0.1:
            summary_parts.append(f"Moderate bias difference detected (diff: {comparison.bias_diff:.2f}).")
        else:
            summary_parts.append("Minimal bias difference across media sources.")

        # Add sentiment information
        sentiment_labels = [score.label for score in comparison.media_bias_scores.values()]
        if all(label == sentiment_labels[0] for label in sentiment_labels):
            summary_parts.append(f"All sources show {sentiment_labels[0]} sentiment.")
        else:
            summary_parts.append(f"Mixed sentiment across sources: {', '.join(set(sentiment_labels))}.")

        return " ".join(summary_parts)

    def _create_empty_report(self, cluster: Cluster) -> Report:
        """
        Create a minimal report for an empty cluster.

        Args:
            cluster: Empty cluster

        Returns:
            Minimal Report object
        """
        comparison = ComparisonResult(
            media_bias_scores={},
            unique_entities_by_media={},
            common_entities=[],
            bias_diff=0.0
        )

        return Report(
            id=uuid.uuid4().hex,
            cluster=cluster,
            comparison=comparison,
            generated_at=datetime.utcnow(),
            summary="Empty cluster - no articles to analyze."
        )
