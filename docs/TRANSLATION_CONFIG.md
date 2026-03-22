# Translation Configuration Guide

## Overview

The Middle East News Aggregator includes Japanese translation support using Google Cloud Translation API with built-in quota management to stay within the free tier (500K characters/month).

## Environment Variables

Configure translation behavior through environment variables:

### Quota Limits

```bash
# Monthly character limit (default: 500000)
TRANSLATION_MONTHLY_LIMIT=500000

# Safe margin percentage (default: 0.80 = 80%)
# Operates at 80% of limit to provide buffer
TRANSLATION_SAFE_MARGIN=0.80

# Daily character limit (default: 20000)
# Spreads usage evenly across the month
TRANSLATION_DAILY_LIMIT=20000

# Maximum characters per article (default: 5000)
TRANSLATION_MAX_PER_ARTICLE=5000
```

### Translation Modes

```bash
# Translate only titles (default: true)
TRANSLATE_TITLES_ONLY=true

# Translate full content (default: false)
TRANSLATE_CONTENT=false

# Automatic disable threshold (default: 0.95 = 95%)
# Translation stops when this threshold is reached
TRANSLATION_DISABLE_THRESHOLD=0.95
```

### GCP Configuration

```bash
# Path to Google Cloud service account key
GOOGLE_APPLICATION_CREDENTIALS=~/gcp-key.json

# GCP project ID
GCP_PROJECT_ID=middle-east-news-aggregator
```

## Configuration Presets

### Conservative (Recommended for MVP)

Best for staying well within free tier limits.

```bash
TRANSLATION_MONTHLY_LIMIT=500000
TRANSLATION_SAFE_MARGIN=0.80
TRANSLATE_TITLES_ONLY=true
TRANSLATE_CONTENT=false
TRANSLATION_DISABLE_THRESHOLD=0.95
TRANSLATION_DAILY_LIMIT=20000
TRANSLATION_MAX_PER_ARTICLE=1000
```

**Expected usage**: ~100 chars/article × 100 articles/month = **10K chars/month (2% of limit)**

### Moderate (Titles + Summaries)

Translates titles and content summaries (first 500 characters).

```bash
TRANSLATION_MONTHLY_LIMIT=500000
TRANSLATION_SAFE_MARGIN=0.80
TRANSLATE_TITLES_ONLY=false
TRANSLATE_CONTENT=true
TRANSLATION_DISABLE_THRESHOLD=0.90
TRANSLATION_DAILY_LIMIT=50000
TRANSLATION_MAX_PER_ARTICLE=3000
```

**Expected usage**: ~1500 chars/article × 100 articles/month = **150K chars/month (30% of limit)**

### Advanced (Titles + Full Content)

Translates titles and full content with per-article limit.

```bash
TRANSLATION_MONTHLY_LIMIT=500000
TRANSLATION_SAFE_MARGIN=0.85
TRANSLATE_TITLES_ONLY=false
TRANSLATE_CONTENT=true
TRANSLATION_DISABLE_THRESHOLD=0.85
TRANSLATION_DAILY_LIMIT=100000
TRANSLATION_MAX_PER_ARTICLE=5000
```

**Expected usage**: ~2500 chars/article × 50 articles/month = **125K chars/month (25% of limit)**

## How It Works

### Automatic Degradation

The system automatically adjusts translation behavior based on quota usage:

| Usage | Mode | Behavior |
|-------|------|----------|
| < 80% | Default | Translates according to configured mode |
| 80-85% | Titles + Summary | Translates titles and first 500 chars |
| 85-95% | Titles Only | Only translates article titles |
| ≥ 95% | Disabled | No translation to prevent overage |

### Character Counting

- Characters are counted **before** sending to the API
- Failed translations do not consume quota
- Cached translations (duplicates) do not consume quota
- Audit log tracks every translation with character counts

### Quota Enforcement

1. **Before each pipeline run**: Check current month usage
2. **Before each article**: Estimate character count
3. **Quota check**: Verify daily + monthly limits
4. **After translation**: Record actual usage in Firestore

## Monitoring Quota Usage

### Check Current Status

```bash
curl https://YOUR_API_URL/api/admin/quota-status
```

Response:
```json
{
  "month": "2026-03",
  "total_limit": 500000,
  "safe_limit": 400000,
  "monthly_usage": 125000,
  "monthly_usage_percent": 0.3125,
  "daily_usage": 5000,
  "daily_limit": 20000,
  "articles_translated_month": 85,
  "remaining_chars": 275000,
  "status": "SAFE",
  "recommendations": [
    "Daily budget for rest of month: ~30555 chars/day (9 days remaining)"
  ],
  "config": {
    "monthly_limit_chars": 500000,
    "safe_limit_chars": 400000,
    ...
  }
}
```

### Status Levels

- **SAFE** (< 80%): Normal operation
- **WARNING** (80-95%): Approaching limit, degraded mode active
- **CRITICAL** (≥ 95%): Translation disabled

## Validation

The configuration validates at startup:

```python
from middle_east_aggregator.translation_config import TranslationConfig
TranslationConfig.validate()
```

Validation checks:
- Safe margin ≤ 1.0
- Safe limit ≥ 50K characters
- Google Cloud credentials file exists
- Warns if daily limit × 31 exceeds monthly limit

## Troubleshooting

### Translation not working

1. Check quota status: `curl YOUR_API_URL/api/admin/quota-status`
2. Verify credentials: `echo $GOOGLE_APPLICATION_CREDENTIALS`
3. Check logs for quota warnings
4. Ensure `TRANSLATE_TITLES_ONLY=true` or `TRANSLATE_CONTENT=true`

### Quota exceeded

1. Check audit logs in Firestore `translation_audit` collection
2. Review monthly usage: `db.collection("translation_quota").get()`
3. Reduce `TRANSLATION_SAFE_MARGIN` to allow more usage (not recommended)
4. Enable `TRANSLATE_TITLES_ONLY=true` to reduce per-article usage
5. Decrease `TRANSLATION_DAILY_LIMIT` to spread usage more evenly

### Unexpected high usage

1. Check `translation_audit` collection for spikes
2. Verify `TRANSLATION_MAX_PER_ARTICLE` is set appropriately
3. Check for duplicate articles (caching should prevent this)
4. Review pipeline execution frequency

## Best Practices

1. **Start conservative**: Use titles-only mode initially
2. **Monitor daily**: Check quota status endpoint daily
3. **Set alerts**: Configure GitHub Actions to alert at 80% usage
4. **Review monthly**: Analyze audit logs at end of each month
5. **Test with dry run**: Test configuration changes with small batches first
