# Middle East News Aggregator

🌍 Automated news collection and bias analysis system for Middle East coverage from Al Jazeera, Reuters, and BBC.

[![Tests](https://img.shields.io/badge/tests-91%20passing-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-86%25-green)](htmlcov/)
[![Python](https://img.shields.io/badge/python-3.11-blue)](requirements.txt)
[![React](https://img.shields.io/badge/react-19-61dafb)](frontend/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## ✅ Implementation Complete

**All 13 tasks completed with Test-Driven Development (TDD)**

- ✅ Backend (Python): 8 components, 78 tests, 86% coverage
- ✅ Frontend (React): 4 views, 13 tests
- ✅ CI/CD: GitHub Actions (6h collection + auto-deploy)
- ✅ Deployment: Docker + Cloud Run + Firebase Hosting

## 🚀 Quick Start

### Backend
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
pytest  # Run 78 tests
uvicorn middle_east_aggregator.api:app --reload
```

### Frontend
```bash
cd frontend
npm install && npm test  # Run 13 tests
npm run dev
```

### Manual Collection
```bash
python -m middle_east_aggregator.cli collect
```

## 📊 Features

**Automated Workflow (Every 6 Hours):**
1. **Collect** - RSS feeds from 3 media sources
2. **Filter** - Middle East keyword matching
3. **Cluster** - TF-IDF topic grouping
4. **Analyze** - Sentiment + entity extraction
5. **Generate** - Comparative bias reports
6. **Publish** - REST API + React dashboard

**API Endpoints:**
- `GET /api/reports` - List all reports
- `GET /api/reports/{id}` - Report details
- `GET /api/reports/search?q={keyword}` - Search
- `GET /api/articles` - Article list
- `GET /api/status` - System status
- `POST /api/collect` - Manual trigger

**Frontend Views:**
- Report list with filters
- Detailed report with bias charts
- Keyword search

## 🏗️ Architecture

```
GitHub Actions (6h) → Collectors → Filter → Clusterer → Analyzer
                                                            ↓
                                                       Firestore
                                                            ↓
                                                    FastAPI (Cloud Run)
                                                            ↓
                                                    React (Firebase Hosting)
```

## 🧪 Testing

**91 tests total:**
- 78 backend tests (86% coverage)
  - 13 property-based tests (Hypothesis)
  - 58 unit tests
  - 7 integration tests
- 13 frontend tests (API client)

```bash
# Backend
pytest --cov=middle_east_aggregator

# Frontend
cd frontend && npm test
```

## 🌐 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide.

**Quick deploy:**
```bash
# Push to main triggers auto-deployment
git push origin main

# Or manual:
gcloud builds submit --config cloudbuild.yaml
firebase deploy --only hosting
```

**Cost:** $0/month (GCP free tier)

## 📚 Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11, FastAPI, spaCy, TextBlob, scikit-learn |
| **Frontend** | React 19, TypeScript, Vite, Recharts, React Router |
| **Database** | Google Cloud Firestore |
| **Hosting** | Cloud Run (backend), Firebase Hosting (frontend) |
| **CI/CD** | GitHub Actions |
| **Testing** | Pytest, Hypothesis, Vitest, React Testing Library |

## 📖 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [design.md](design.md) - System design
- [requirements.md](requirements.md) - Functional requirements
- [tasks.md](tasks.md) - Implementation checklist
- [frontend/README.md](frontend/README.md) - Frontend docs

## 🎓 Development Philosophy

**Test-Driven Development (TDD):**
1. Red - Write failing test
2. Green - Minimal implementation
3. Refactor - Improve quality

**Property-Based Testing:**
12 formal properties validated with Hypothesis

## 🤝 Contributing

1. Fork repository
2. Write tests first (TDD)
3. Implement feature
4. Submit PR

## 📄 License

MIT License

---

**Built with TDD using Claude Code** 🚀
