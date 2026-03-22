# Translation Quota Management

## Overview

This document describes the quota tracking system that ensures the Middle East News Aggregator stays within the Google Cloud Translation API free tier (500K characters/month).

## Architecture

### Components

1. **QuotaTracker** (`translation_quota.py`): Tracks monthly and daily usage in Firestore
2. **TranslationConfig** (`translation_config.py`): Configuration with safety limits
3. **Translator** (`translator.py`): Translation service with character counting
4. **Pipeline** (`pipeline.py`): Orchestrates translation with quota checks

### Data Storage

Firestore collections:

#### `translation_quota`

Monthly and daily quota documents:

```javascript
// Monthly document (ID: "2026-03")
{
  usage: 125000,              // Total characters translated this month
  article_count: 85,          // Number of articles translated
  created_at: Timestamp,
  updated_at: Timestamp
}

// Daily document (ID: "daily_2026-03-22")
{
  usage: 5000,                // Characters translated today
  article_count: 10,          // Articles translated today
  created_at: Timestamp,
  updated_at: Timestamp
}
```

#### `translation_audit`

Detailed audit log for every translation:

```javascript
{
  article_id: "a1b2c3d4",
  char_count: 150,            // Input characters sent to API
  mode: "titles_only",        // Translation mode used
  success: true,              // Whether translation succeeded
  timestamp: Timestamp,
  month: "2026-03",
  date: "2026-03-22"
}
```

## Quota Enforcement Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Starts                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Check Monthly Usage (QuotaTracker.get_quota_status())   │
│     - Calculate usage_percent = usage / safe_limit          │
│     - Determine status: SAFE / WARNING / CRITICAL           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Select Translation Mode                                 │
│     - If ≥95%: DISABLED                                     │
│     - If ≥85%: TITLES_ONLY                                  │
│     - If ≥80%: TITLES_AND_SUMMARY                           │
│     - Else: Configured default                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. For Each Article                                        │
│     a) Estimate character count                             │
│     b) QuotaTracker.can_translate(estimated_chars)          │
│        - Check monthly: usage + chars <= safe_limit         │
│        - Check daily: daily_usage + chars <= daily_limit    │
│     c) If YES → Translate                                   │
│     d) If NO → Skip (status="skipped")                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Translate (Translator.translate_article())              │
│     - Count input characters BEFORE API call                │
│     - Call Google Cloud Translation API                     │
│     - Store result in Article fields                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Record Usage                                            │
│     - QuotaTracker.record_translation()                     │
│     - Firestore transaction: increment monthly + daily      │
│     - Write audit log entry                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Save Article (with translation fields populated)        │
└─────────────────────────────────────────────────────────────┘
```

## Quota Status API

### Endpoint

```
GET /api/admin/quota-status
```

### Response Structure

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
    "safe_margin_percent": 0.8,
    "safe_limit_chars": 400000,
    "translate_titles_only": true,
    "translate_content": false,
    "disable_threshold_percent": 0.95,
    "daily_limit_chars": 20000,
    "max_chars_per_article": 5000,
    "default_mode": "titles_only",
    "gcp_project_id": "middle-east-news-aggregator"
  }
}
```

### Status Interpretation

| Field | Description |
|-------|-------------|
| `month` | Current month in YYYY-MM format |
| `total_limit` | Absolute limit (500K for free tier) |
| `safe_limit` | Operating limit (total × safe_margin) |
| `monthly_usage` | Characters used this month |
| `monthly_usage_percent` | Percentage of **safe limit** used |
| `daily_usage` | Characters used today |
| `daily_limit` | Maximum characters per day |
| `articles_translated_month` | Number of articles translated this month |
| `remaining_chars` | Characters remaining in safe limit |
| `status` | SAFE / WARNING / CRITICAL |
| `recommendations` | Actionable suggestions |

## Recommendations Engine

The quota tracker provides context-aware recommendations:

### SAFE (< 80%)

```
- Daily budget for rest of month: ~30555 chars/day (9 days remaining)
```

### WARNING (80-95%)

```
- WARNING: Quota at 80%+. Consider switching to titles-only mode or reducing translation frequency.
- Approaching quota limit. Monitor daily usage closely.
- Daily budget for rest of month: ~5555 chars/day (9 days remaining)
```

### CRITICAL (≥ 95%)

```
- URGENT: Quota at 95%+. Translation is disabled. Review usage in audit logs and consider upgrading plan.
- Daily budget for rest of month: ~1111 chars/day (9 days remaining)
```

## Monitoring and Alerting

### Daily Monitoring

Check quota status daily via API or Firestore console:

```bash
curl https://YOUR_API_URL/api/admin/quota-status
```

### Monthly Audit

At end of month, export audit logs for analysis:

```javascript
// Firestore query
db.collection("translation_audit")
  .where("month", "==", "2026-03")
  .orderBy("timestamp", "desc")
  .get()
```

Analyze:
- Total characters used
- Articles translated per day
- Average characters per article
- Translation mode distribution
- Success vs. failure rate

### GitHub Actions Alert

Add quota check to workflow (see Phase 4 in implementation plan):

```yaml
- name: Check Translation Quota
  run: |
    STATUS=$(curl -s https://YOUR_API_URL/api/admin/quota-status | jq -r '.status')
    if [ "$STATUS" = "CRITICAL" ]; then
      echo "CRITICAL: Translation quota exceeded"
      exit 1
    elif [ "$STATUS" = "WARNING" ]; then
      echo "WARNING: Translation quota approaching limit"
    fi
```

## Firestore Transactions

To prevent race conditions when multiple pipelines run simultaneously, quota updates use Firestore transactions:

```python
@firestore.transactional
def _increment_usage_transaction(
    self,
    transaction: firestore.Transaction,
    month_ref: firestore.DocumentReference,
    daily_ref: firestore.DocumentReference,
    char_count: int
) -> None:
    # Read current values
    month_doc = month_ref.get(transaction=transaction)
    daily_doc = daily_ref.get(transaction=transaction)

    # Increment usage
    # ...

    # Write back atomically
    transaction.set(month_ref, month_data)
    transaction.set(daily_ref, daily_data)
```

This ensures that concurrent translations don't overwrite each other's quota updates.

## Emergency Procedures

See [QUOTA_EMERGENCY.md](./QUOTA_EMERGENCY.md) for detailed emergency procedures if quota is exceeded or approaching critical levels.

## Testing

Quota tracking is thoroughly tested:

- Unit tests: `tests/test_translation_quota.py`
- Integration tests: `tests/test_translation_pipeline.py` (Phase 5)
- All tests use Firestore test emulator for isolation

Run tests:

```bash
python -m pytest tests/test_translation_quota.py -v
```
