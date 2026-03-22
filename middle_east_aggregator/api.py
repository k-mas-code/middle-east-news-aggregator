"""
FastAPI backend for Middle East News Aggregator.

Provides REST API endpoints for accessing reports, articles, and system status.
"""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from middle_east_aggregator.database import ArticleRepository, ReportRepository
from middle_east_aggregator.pipeline import NewsPipeline
from middle_east_aggregator.models import Article, Report, Cluster, ComparisonResult, SentimentResult, Entity
from middle_east_aggregator.translation_quota import QuotaTracker
from middle_east_aggregator.translation_config import TranslationConfig

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Middle East News Aggregator API",
    description="API for accessing comparative news analysis from Al Jazeera, Reuters, and BBC",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic response models
class EntityResponse(BaseModel):
    """Entity extracted from article text."""
    text: str
    label: str
    count: int


class SentimentResponse(BaseModel):
    """Sentiment analysis result."""
    polarity: float
    subjectivity: float
    label: str


class ArticleResponse(BaseModel):
    """Article response model."""
    id: str
    url: str
    title: str
    content: str
    published_at: datetime
    media_name: str
    is_middle_east: bool
    collected_at: datetime
    title_ja: Optional[str] = None
    content_ja: Optional[str] = None
    char_count_input: int = 0
    translation_status: str = "pending"


class ClusterResponse(BaseModel):
    """Cluster response model."""
    id: str
    topic_name: str
    articles: List[ArticleResponse]
    media_names: List[str]
    created_at: datetime


class ComparisonResponse(BaseModel):
    """Comparison result response model."""
    media_bias_scores: dict[str, SentimentResponse]
    unique_entities_by_media: dict[str, List[EntityResponse]]
    common_entities: List[EntityResponse]
    bias_diff: float


class ReportResponse(BaseModel):
    """Report response model."""
    id: str
    cluster: ClusterResponse
    comparison: ComparisonResponse
    generated_at: datetime
    summary: str


class StatusResponse(BaseModel):
    """System status response."""
    status: str
    last_collection: Optional[datetime] = None
    total_articles: int = 0
    total_reports: int = 0


class CollectionResponse(BaseModel):
    """Collection trigger response."""
    status: str
    articles_collected: int = 0
    articles_filtered: int = 0
    clusters_created: int = 0
    reports_generated: int = 0
    duration_seconds: float = 0


# Helper functions to convert models to response models
def article_to_response(article: Article) -> ArticleResponse:
    """Convert Article model to ArticleResponse."""
    return ArticleResponse(
        id=article.id,
        url=article.url,
        title=article.title,
        content=article.content,
        published_at=article.published_at,
        media_name=article.media_name,
        is_middle_east=article.is_middle_east,
        collected_at=article.collected_at,
        title_ja=article.title_ja,
        content_ja=article.content_ja,
        char_count_input=article.char_count_input,
        translation_status=article.translation_status
    )


def entity_to_response(entity: Entity) -> EntityResponse:
    """Convert Entity model to EntityResponse."""
    return EntityResponse(
        text=entity.text,
        label=entity.label,
        count=entity.count
    )


def sentiment_to_response(sentiment: SentimentResult) -> SentimentResponse:
    """Convert SentimentResult to SentimentResponse."""
    return SentimentResponse(
        polarity=sentiment.polarity,
        subjectivity=sentiment.subjectivity,
        label=sentiment.label
    )


def cluster_to_response(cluster: Cluster) -> ClusterResponse:
    """Convert Cluster model to ClusterResponse."""
    return ClusterResponse(
        id=cluster.id,
        topic_name=cluster.topic_name,
        articles=[article_to_response(a) for a in cluster.articles],
        media_names=cluster.media_names,
        created_at=cluster.created_at
    )


def comparison_to_response(comparison: ComparisonResult) -> ComparisonResponse:
    """Convert ComparisonResult to ComparisonResponse."""
    return ComparisonResponse(
        media_bias_scores={
            media: sentiment_to_response(sentiment)
            for media, sentiment in comparison.media_bias_scores.items()
        },
        unique_entities_by_media={
            media: [entity_to_response(e) for e in entities]
            for media, entities in comparison.unique_entities_by_media.items()
        },
        common_entities=[entity_to_response(e) for e in comparison.common_entities],
        bias_diff=comparison.bias_diff
    )


def report_to_response(report: Report) -> ReportResponse:
    """Convert Report model to ReportResponse."""
    return ReportResponse(
        id=report.id,
        cluster=cluster_to_response(report.cluster),
        comparison=comparison_to_response(report.comparison),
        generated_at=report.generated_at,
        summary=report.summary
    )


# API Endpoints

@app.get("/api/reports", response_model=List[ReportResponse])
async def get_reports():
    """
    Get list of all reports.

    Returns:
        List of reports with cluster analysis and bias comparison

    Validates: Requirement 5.1 - レポート一覧表示
    """
    try:
        repo = ReportRepository()
        reports = repo.find_all()

        return [report_to_response(r) for r in reports]

    except Exception as e:
        logger.error(f"Error fetching reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch reports")


@app.get("/api/reports/search", response_model=List[ReportResponse])
async def search_reports(q: str = Query(..., min_length=1, description="Search keyword")):
    """
    Search reports by keyword.

    Args:
        q: Search keyword

    Returns:
        List of reports matching the keyword

    Validates: Requirement 5.5 - キーワード検索

    Note: This route must come BEFORE /api/reports/{report_id} in FastAPI
    """
    try:
        repo = ReportRepository()
        reports = repo.search(q)

        return [report_to_response(r) for r in reports]

    except Exception as e:
        logger.error(f"Error searching reports with keyword '{q}': {e}")
        raise HTTPException(status_code=500, detail="Failed to search reports")


@app.get("/api/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """
    Get specific report by ID.

    Args:
        report_id: Report ID

    Returns:
        Report details with articles and bias analysis

    Validates: Requirement 5.2 - レポート詳細表示

    Note: This route must come AFTER /api/reports/search in FastAPI
    """
    try:
        repo = ReportRepository()
        report = repo.find_by_id(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        return report_to_response(report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch report")


@app.get("/api/articles", response_model=List[ArticleResponse])
async def get_articles(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of articles to return")
):
    """
    Get list of recent articles.

    Args:
        limit: Maximum number of articles (default 100, max 1000)

    Returns:
        List of articles with original URLs

    Validates: Requirement 5.4 - 原文リンク提供
    """
    try:
        repo = ArticleRepository()

        # Get articles from recent 30 days
        from datetime import timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        articles = repo.find_by_date_range(start_date, end_date)

        # Limit results
        articles = articles[:limit]

        return [article_to_response(a) for a in articles]

    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch articles")


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """
    Get system status and last update time.

    Returns:
        System status with last collection timestamp

    Validates: Requirement 5.6 - 最終更新日時表示
    """
    try:
        article_repo = ArticleRepository()
        report_repo = ReportRepository()

        # Get recent articles to determine last collection time
        from datetime import timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        articles = article_repo.find_by_date_range(start_date, end_date)
        reports = report_repo.find_all()

        # Determine last collection time
        last_collection = None
        if articles:
            last_collection = max(a.collected_at for a in articles)

        return StatusResponse(
            status="ok",
            last_collection=last_collection,
            total_articles=len(articles),
            total_reports=len(reports)
        )

    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        # Return degraded status instead of error
        return StatusResponse(
            status="degraded",
            last_collection=None,
            total_articles=0,
            total_reports=0
        )


@app.post("/api/collect", response_model=CollectionResponse)
async def trigger_collection():
    """
    Manually trigger article collection and analysis.

    Returns:
        Collection results with statistics

    Validates: Manual collection trigger
    """
    try:
        logger.info("Manual collection triggered via API")

        # Run the pipeline
        pipeline = NewsPipeline()
        result = pipeline.run()

        return CollectionResponse(
            status=result.get('status', 'unknown'),
            articles_collected=result.get('articles_collected', 0),
            articles_filtered=result.get('articles_filtered', 0),
            clusters_created=result.get('clusters_created', 0),
            reports_generated=result.get('reports_generated', 0),
            duration_seconds=result.get('duration_seconds', 0)
        )

    except Exception as e:
        logger.error(f"Error during manual collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")


class QuotaStatusResponse(BaseModel):
    """Translation quota status response."""
    month: str
    total_limit: int
    safe_limit: int
    monthly_usage: int
    monthly_usage_percent: float
    daily_usage: int
    daily_limit: int
    articles_translated_month: int
    remaining_chars: int
    status: str
    recommendations: List[str]
    config: dict


@app.get("/api/admin/quota-status", response_model=QuotaStatusResponse)
async def get_quota_status():
    """
    Get translation quota status and usage statistics.

    Returns:
        Current quota usage, limits, and recommendations

    Admin endpoint for monitoring translation API usage
    """
    try:
        quota_tracker = QuotaTracker()
        status = quota_tracker.get_quota_status()
        daily_usage = quota_tracker.get_daily_usage()
        recommendations = quota_tracker.get_recommendations(status)

        return QuotaStatusResponse(
            month=status.month,
            total_limit=TranslationConfig.MONTHLY_LIMIT_CHARS,
            safe_limit=TranslationConfig.get_safe_limit_chars(),
            monthly_usage=status.usage,
            monthly_usage_percent=status.usage_percent,
            daily_usage=daily_usage,
            daily_limit=TranslationConfig.DAILY_LIMIT_CHARS,
            articles_translated_month=status.article_count,
            remaining_chars=status.remaining_chars,
            status=status.status,
            recommendations=recommendations,
            config=TranslationConfig.to_dict()
        )

    except Exception as e:
        logger.error(f"Error fetching quota status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch quota status")


class QuotaForecastResponse(BaseModel):
    """Translation quota usage forecast response."""
    current_usage: int
    current_day: int
    days_in_month: int
    days_remaining: int
    daily_average: int
    forecast_month_end: int
    forecast_percent: float
    safe_limit: int
    risk_level: str
    recommendation: str


@app.get("/api/admin/quota-forecast", response_model=QuotaForecastResponse)
async def get_quota_forecast():
    """
    Get translation quota usage forecast for month-end.

    Returns:
        Forecast based on current usage trends with risk assessment

    Admin endpoint for proactive quota management
    """
    try:
        quota_tracker = QuotaTracker()
        forecast = quota_tracker.get_usage_forecast()

        return QuotaForecastResponse(**forecast)

    except Exception as e:
        logger.error(f"Error generating quota forecast: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate forecast")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Middle East News Aggregator API",
        "version": "1.0.0",
        "endpoints": {
            "reports": "/api/reports",
            "report_detail": "/api/reports/{id}",
            "search": "/api/reports/search?q={keyword}",
            "articles": "/api/articles",
            "status": "/api/status",
            "collect": "/api/collect (POST)",
            "quota_status": "/api/admin/quota-status",
            "quota_forecast": "/api/admin/quota-forecast"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
