"""
Core data models for the Middle East News Aggregator system.

These models define the data structures used throughout the system,
from raw article collection to final report generation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class RawArticle:
    """
    Raw article data as collected from RSS feeds.

    Represents the initial article data before normalization and filtering.
    """
    url: str
    title: str
    content: str
    published_at: datetime
    media_name: Literal["aljazeera", "reuters", "bbc"]


@dataclass
class Article:
    """
    Normalized article with metadata.

    Represents a fully processed article with unique ID and classification.
    """
    id: str  # UUID
    url: str
    title: str
    content: str
    published_at: datetime
    media_name: Literal["aljazeera", "reuters", "bbc"]
    is_middle_east: bool
    collected_at: datetime


@dataclass
class SentimentResult:
    """
    Sentiment analysis result for an article.

    Attributes:
        polarity: Sentiment polarity score from -1.0 (negative) to +1.0 (positive)
        subjectivity: Subjectivity score from 0.0 (objective) to 1.0 (subjective)
        label: Sentiment classification label
    """
    polarity: float  # -1.0 (ネガティブ) 〜 +1.0 (ポジティブ)
    subjectivity: float  # 0.0 (客観的) 〜 1.0 (主観的)
    label: Literal["positive", "negative", "neutral"]


@dataclass
class Entity:
    """
    Named entity extracted from article text.

    Attributes:
        text: The entity text (e.g., "Israel", "Gaza")
        label: Entity type (PERSON, GPE, ORG, LOC)
        count: Number of occurrences in the text
    """
    text: str
    label: Literal["PERSON", "GPE", "ORG", "LOC"]
    count: int


@dataclass
class Cluster:
    """
    Topic cluster grouping related articles.

    Represents a set of articles covering the same topic from different media sources.
    """
    id: str
    topic_name: str
    articles: list[Article]
    media_names: list[str]
    created_at: datetime


@dataclass
class ComparisonResult:
    """
    Comparative analysis result for a cluster.

    Contains bias scores and entity differences across media sources.
    """
    media_bias_scores: dict[str, SentimentResult]  # メディア名 -> スコア
    unique_entities_by_media: dict[str, list[Entity]]
    common_entities: list[Entity]
    bias_diff: float  # メディア間のpolarity差の最大値


@dataclass
class Report:
    """
    Final analysis report for a topic cluster.

    Combines cluster data with comparative analysis and generated summary.
    """
    id: str
    cluster: Cluster
    comparison: ComparisonResult
    generated_at: datetime
    summary: str  # 自動生成サマリーテキスト
