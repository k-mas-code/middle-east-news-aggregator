"""
Demo API server for local testing without Firestore.

Uses in-memory mock data for demonstration purposes.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from demo_data import generate_demo_reports

# Generate demo data
DEMO_REPORTS = {r.id: r for r in generate_demo_reports()}
DEMO_ARTICLES = []
for report in DEMO_REPORTS.values():
    DEMO_ARTICLES.extend(report.cluster.articles)

# Import response models from main API
from middle_east_aggregator.api import (
    ReportResponse,
    ArticleResponse,
    StatusResponse,
    report_to_response,
    article_to_response
)

app = FastAPI(
    title="Middle East News Aggregator - DEMO",
    description="Demo API with mock data for local testing",
    version="1.0.0-demo"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Middle East News Aggregator API (DEMO MODE)",
        "version": "1.0.0-demo",
        "note": "Using mock data for demonstration",
        "reports_count": len(DEMO_REPORTS),
        "endpoints": {
            "reports": "/api/reports",
            "report_detail": "/api/reports/{id}",
            "search": "/api/reports/search?q={keyword}",
            "articles": "/api/articles",
            "status": "/api/status"
        }
    }


@app.get("/api/reports", response_model=list[ReportResponse])
async def get_reports():
    """Get list of all demo reports."""
    return [report_to_response(r) for r in DEMO_REPORTS.values()]


@app.get("/api/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Get specific report by ID."""
    if report_id not in DEMO_REPORTS:
        raise HTTPException(status_code=404, detail="Report not found")

    return report_to_response(DEMO_REPORTS[report_id])


@app.get("/api/reports/search", response_model=list[ReportResponse])
async def search_reports(q: str):
    """Search reports by keyword."""
    results = []
    q_lower = q.lower()

    for report in DEMO_REPORTS.values():
        # Search in topic name, summary, and article titles
        if (q_lower in report.cluster.topic_name.lower() or
            q_lower in report.summary.lower() or
            any(q_lower in article.title.lower() for article in report.cluster.articles)):
            results.append(report_to_response(report))

    return results


@app.get("/api/articles", response_model=list[ArticleResponse])
async def get_articles(limit: int = 100):
    """Get list of demo articles."""
    articles = DEMO_ARTICLES[:limit]
    return [article_to_response(a) for a in articles]


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get demo system status."""
    from datetime import datetime

    # Get latest article timestamp
    latest = max(a.collected_at for a in DEMO_ARTICLES) if DEMO_ARTICLES else None

    return StatusResponse(
        status="ok (demo mode)",
        last_collection=latest,
        total_articles=len(DEMO_ARTICLES),
        total_reports=len(DEMO_REPORTS)
    )


if __name__ == "__main__":
    import uvicorn
    print("🎬 Starting DEMO API server...")
    print(f"📊 Loaded {len(DEMO_REPORTS)} demo reports")
    print(f"📰 Loaded {len(DEMO_ARTICLES)} demo articles")
    print("🌐 Access at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
