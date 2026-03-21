"""
Pytest configuration and shared fixtures.
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from google.cloud import firestore
from hypothesis import strategies as st

from middle_east_aggregator.models import (
    Article,
    Report,
    Cluster,
    ComparisonResult,
    SentimentResult,
    Entity,
)


# Hypothesis strategies for generating test data

@st.composite
def article_strategy(draw):
    """
    Hypothesis strategy for generating valid Article instances.

    Feature: middle-east-news-aggregator
    """
    media_names = st.sampled_from(["aljazeera", "reuters", "bbc"])

    # Generate valid article data
    article_id = draw(st.uuids()).hex
    url = draw(st.text(min_size=10, max_size=200).map(lambda x: f"https://example.com/{x.replace(' ', '-')}"))
    title = draw(st.text(min_size=5, max_size=200))
    content = draw(st.text(min_size=20, max_size=1000))

    # Generate datetime within last 365 days
    days_ago = draw(st.integers(min_value=0, max_value=365))
    published_at = datetime.utcnow() - timedelta(days=days_ago)

    media_name = draw(media_names)
    is_middle_east = draw(st.booleans())

    collected_at = datetime.utcnow()

    return Article(
        id=article_id,
        url=url,
        title=title,
        content=content,
        published_at=published_at,
        media_name=media_name,
        is_middle_east=is_middle_east,
        collected_at=collected_at
    )


@st.composite
def sentiment_result_strategy(draw):
    """Hypothesis strategy for generating SentimentResult."""
    polarity = draw(st.floats(min_value=-1.0, max_value=1.0))
    subjectivity = draw(st.floats(min_value=0.0, max_value=1.0))

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


@st.composite
def entity_strategy(draw):
    """Hypothesis strategy for generating Entity."""
    text = draw(st.text(min_size=2, max_size=50))
    label = draw(st.sampled_from(["PERSON", "GPE", "ORG", "LOC"]))
    count = draw(st.integers(min_value=1, max_value=20))

    return Entity(text=text, label=label, count=count)


@st.composite
def cluster_strategy(draw):
    """Hypothesis strategy for generating Cluster."""
    cluster_id = draw(st.uuids()).hex
    topic_name = draw(st.text(min_size=5, max_size=100))

    # Generate 1-5 articles
    num_articles = draw(st.integers(min_value=1, max_value=5))
    articles = [draw(article_strategy()) for _ in range(num_articles)]

    # Extract unique media names from articles
    media_names = list(set(a.media_name for a in articles))

    created_at = datetime.utcnow()

    return Cluster(
        id=cluster_id,
        topic_name=topic_name,
        articles=articles,
        media_names=media_names,
        created_at=created_at
    )


@st.composite
def comparison_result_strategy(draw, media_names=None):
    """Hypothesis strategy for generating ComparisonResult."""
    if media_names is None:
        media_names = draw(st.lists(
            st.sampled_from(["aljazeera", "reuters", "bbc"]),
            min_size=1,
            max_size=3,
            unique=True
        ))

    # Generate bias scores for each media
    media_bias_scores = {
        media: draw(sentiment_result_strategy())
        for media in media_names
    }

    # Generate entities
    num_common = draw(st.integers(min_value=0, max_value=5))
    common_entities = [draw(entity_strategy()) for _ in range(num_common)]

    unique_entities_by_media = {
        media: [draw(entity_strategy()) for _ in range(draw(st.integers(min_value=0, max_value=3)))]
        for media in media_names
    }

    # Calculate bias_diff (max polarity difference)
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


@st.composite
def report_strategy(draw):
    """Hypothesis strategy for generating Report."""
    report_id = draw(st.uuids()).hex
    cluster = draw(cluster_strategy())
    comparison = draw(comparison_result_strategy(media_names=cluster.media_names))
    generated_at = datetime.utcnow()
    summary = draw(st.text(min_size=10, max_size=500))

    return Report(
        id=report_id,
        cluster=cluster,
        comparison=comparison,
        generated_at=generated_at,
        summary=summary
    )


def create_mock_firestore_client():
    """
    Create a mock Firestore client for testing without actual GCP connection.

    Returns a mock client with in-memory document storage.
    This is a factory function instead of a fixture to work with Hypothesis.
    """
    # Create in-memory storage for documents
    storage = {}

    class MockDocumentReference:
        def __init__(self, doc_id):
            self.id = doc_id
            self._storage = storage

        def set(self, data, merge=False):
            self._storage[self.id] = data.copy()

        def get(self):
            mock_snapshot = MagicMock()
            mock_snapshot.exists = self.id in self._storage
            if mock_snapshot.exists:
                mock_snapshot.to_dict.return_value = self._storage[self.id]
                mock_snapshot.id = self.id
            return mock_snapshot

        def delete(self):
            if self.id in self._storage:
                del self._storage[self.id]

    class MockQuery:
        def __init__(self, storage, filters=None, limit_count=None):
            self._storage = storage
            self._filters = filters or []
            self._limit_count = limit_count

        def where(self, field, op, value):
            new_filters = self._filters + [(field, op, value)]
            return MockQuery(self._storage, new_filters, self._limit_count)

        def limit(self, count):
            return MockQuery(self._storage, self._filters, count)

        def stream(self):
            results = []
            for doc_id, data in self._storage.items():
                # Apply filters
                include = True
                for field, op, value in self._filters:
                    if field not in data:
                        include = False
                        break
                    if op == "==":
                        if data[field] != value:
                            include = False
                            break
                    elif op == "<":
                        if not (data[field] < value):
                            include = False
                            break
                    elif op == ">":
                        if not (data[field] > value):
                            include = False
                            break
                    elif op == "<=":
                        if not (data[field] <= value):
                            include = False
                            break
                    elif op == ">=":
                        if not (data[field] >= value):
                            include = False
                            break

                if include:
                    mock_snapshot = MagicMock()
                    mock_snapshot.id = doc_id
                    mock_snapshot.to_dict.return_value = data
                    # Add reference to the document for delete operations
                    mock_snapshot.reference = MockDocumentReference(doc_id)
                    results.append(mock_snapshot)

            # Apply limit if specified
            if self._limit_count is not None:
                results = results[:self._limit_count]

            return iter(results)

    class MockCollectionReference:
        def __init__(self, storage):
            self._storage = storage

        def document(self, doc_id):
            return MockDocumentReference(doc_id)

        def where(self, field, op, value):
            return MockQuery(self._storage, [(field, op, value)], None)

        def stream(self):
            """Allow iterating over all documents in the collection."""
            results = []
            for doc_id, data in self._storage.items():
                mock_snapshot = MagicMock()
                mock_snapshot.id = doc_id
                mock_snapshot.to_dict.return_value = data
                # Add reference to the document for delete operations
                mock_snapshot.reference = MockDocumentReference(doc_id)
                results.append(mock_snapshot)
            return iter(results)

    mock_client = MagicMock(spec=firestore.Client)
    mock_client.collection.return_value = MockCollectionReference(storage)

    # Add storage reference for test inspection
    mock_client._storage = storage

    return mock_client


@pytest.fixture
def mock_firestore_client():
    """
    Pytest fixture wrapper around create_mock_firestore_client.

    For use in regular unit tests (not property tests).
    """
    return create_mock_firestore_client()


@pytest.fixture(autouse=True)
def mock_firestore_env(monkeypatch):
    """
    Automatically set mock environment variables for Firestore.
    """
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "localhost:8080")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
