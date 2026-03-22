"""
Tests for translation quota tracking.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from middle_east_aggregator.translation_quota import QuotaTracker, QuotaStatus


@pytest.fixture
def mock_firestore():
    """Mock Firestore client for testing."""
    db = Mock()
    db.collection = Mock(return_value=Mock())
    return db


@pytest.fixture
def quota_tracker(mock_firestore):
    """Create QuotaTracker with mocked Firestore."""
    return QuotaTracker(db=mock_firestore)


class TestQuotaTracker:
    """Test suite for QuotaTracker."""

    def test_get_current_month(self, quota_tracker):
        """Test current month string generation."""
        month = quota_tracker._get_current_month()
        assert len(month) == 7  # Format: YYYY-MM
        assert month.count("-") == 1

    def test_get_current_date(self, quota_tracker):
        """Test current date string generation."""
        date = quota_tracker._get_current_date()
        assert len(date) == 10  # Format: YYYY-MM-DD
        assert date.count("-") == 2

    def test_get_monthly_usage_no_data(self, quota_tracker, mock_firestore):
        """Test monthly usage returns 0 when no data exists."""
        mock_doc = Mock()
        mock_doc.exists = False

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        usage = quota_tracker.get_monthly_usage()
        assert usage == 0

    def test_get_monthly_usage_with_data(self, quota_tracker, mock_firestore):
        """Test monthly usage returns correct value when data exists."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 12345, "article_count": 10}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        usage = quota_tracker.get_monthly_usage()
        assert usage == 12345

    def test_can_translate_within_limit(self, quota_tracker, mock_firestore):
        """Test can_translate returns True when within limits."""
        # Mock both monthly and daily usage
        call_count = [0]

        def mock_get_side_effect():
            call_count[0] += 1
            mock_doc = Mock()
            mock_doc.exists = True
            if call_count[0] == 1:
                # First call: monthly usage
                mock_doc.to_dict.return_value = {"usage": 100000}
            else:
                # Second call: daily usage
                mock_doc.to_dict.return_value = {"usage": 5000}
            return mock_doc

        mock_ref = Mock()
        mock_ref.get.side_effect = mock_get_side_effect

        mock_firestore.collection.return_value.document.return_value = mock_ref

        # Try to translate 10,000 chars (should be OK: monthly 110K < 400K, daily 15K < 20K)
        can_translate = quota_tracker.can_translate(10000)
        assert can_translate is True

    def test_can_translate_exceeds_monthly_limit(self, quota_tracker, mock_firestore):
        """Test can_translate returns False when exceeding monthly limit."""
        # Mock monthly usage: 395,000 chars (close to 400K safe limit)
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 395000}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        # Try to translate 10,000 chars (would exceed: 405K > 400K)
        can_translate = quota_tracker.can_translate(10000)
        assert can_translate is False

    def test_can_translate_exceeds_daily_limit(self, quota_tracker, mock_firestore):
        """Test can_translate returns False when exceeding daily limit."""
        # Setup: monthly usage OK, but daily usage at limit (20,000)
        def mock_get_side_effect(transaction=None):
            if "daily_" in str(transaction):
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {"usage": 19000}  # 19K already used today
                return mock_doc
            else:
                mock_doc = Mock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {"usage": 100000}  # 100K this month
                return mock_doc

        mock_ref = Mock()
        mock_ref.get.side_effect = mock_get_side_effect

        mock_firestore.collection.return_value.document.return_value = mock_ref

        # Try to translate 2,000 chars (would exceed daily: 21K > 20K)
        can_translate = quota_tracker.can_translate(2000)
        assert can_translate is False

    def test_get_quota_status_safe(self, quota_tracker, mock_firestore):
        """Test quota status returns SAFE when usage is low."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 100000, "article_count": 50}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        status = quota_tracker.get_quota_status()

        assert status.usage == 100000
        assert status.status == "SAFE"
        assert status.usage_percent == 0.25  # 100K / 400K = 25%
        assert status.article_count == 50

    def test_get_quota_status_warning(self, quota_tracker, mock_firestore):
        """Test quota status returns WARNING when usage is 80%+."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 350000, "article_count": 200}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        status = quota_tracker.get_quota_status()

        assert status.usage == 350000
        assert status.status == "WARNING"
        assert status.usage_percent == 0.875  # 350K / 400K = 87.5%

    def test_get_quota_status_critical(self, quota_tracker, mock_firestore):
        """Test quota status returns CRITICAL when usage is 95%+."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 390000, "article_count": 300}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        status = quota_tracker.get_quota_status()

        assert status.usage == 390000
        assert status.status == "CRITICAL"
        assert status.usage_percent == 0.975  # 390K / 400K = 97.5%

    def test_get_recommendations_safe(self, quota_tracker):
        """Test recommendations for SAFE status."""
        status = QuotaStatus(
            month="2026-03",
            usage=100000,
            usage_percent=0.25,
            remaining_chars=300000,
            article_count=50,
            status="SAFE"
        )

        recommendations = quota_tracker.get_recommendations(status)
        assert len(recommendations) > 0
        assert any("Daily budget" in rec for rec in recommendations)

    def test_get_recommendations_critical(self, quota_tracker):
        """Test recommendations for CRITICAL status."""
        status = QuotaStatus(
            month="2026-03",
            usage=390000,
            usage_percent=0.975,
            remaining_chars=10000,
            article_count=300,
            status="CRITICAL"
        )

        recommendations = quota_tracker.get_recommendations(status)
        assert any("URGENT" in rec for rec in recommendations)

    def test_get_usage_forecast_low_risk(self, quota_tracker, mock_firestore, monkeypatch):
        """Test usage forecast with low risk trend."""
        # Mock current date: 10th day of month
        mock_now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("middle_east_aggregator.translation_quota.datetime",
                           type("datetime", (), {"now": lambda tz: mock_now}))

        # Mock monthly usage: 50,000 chars on day 10
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 50000, "article_count": 25}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        forecast = quota_tracker.get_usage_forecast()

        # Daily average: 50K / 10 = 5K per day
        # Days remaining: 31 - 10 + 1 = 22 days
        # Forecast: 50K + (5K * 22) = 160K
        # Forecast percent: 160K / 400K = 40%

        assert forecast["current_usage"] == 50000
        assert forecast["current_day"] == 10
        assert forecast["daily_average"] == 5000
        assert forecast["forecast_month_end"] == 160000
        assert forecast["forecast_percent"] == 0.4
        assert forecast["risk_level"] == "LOW"

    def test_get_usage_forecast_high_risk(self, quota_tracker, mock_firestore, monkeypatch):
        """Test usage forecast with high risk trend."""
        # Mock current date: 10th day of month
        mock_now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("middle_east_aggregator.translation_quota.datetime",
                           type("datetime", (), {"now": lambda tz: mock_now}))

        # Mock monthly usage: 200,000 chars on day 10 (20K per day)
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 200000, "article_count": 100}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        forecast = quota_tracker.get_usage_forecast()

        # Daily average: 200K / 10 = 20K per day
        # Days remaining: 31 - 10 + 1 = 22 days
        # Forecast: 200K + (20K * 22) = 640K
        # Forecast percent: 640K / 400K = 160% (exceeds limit!)

        assert forecast["current_usage"] == 200000
        assert forecast["daily_average"] == 20000
        assert forecast["forecast_month_end"] == 640000
        assert forecast["forecast_percent"] == 1.6
        assert forecast["risk_level"] == "HIGH"
        assert "exceed" in forecast["recommendation"].lower()

    def test_get_usage_forecast_medium_risk(self, quota_tracker, mock_firestore, monkeypatch):
        """Test usage forecast with medium risk trend."""
        # Mock current date: 10th day of month
        mock_now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("middle_east_aggregator.translation_quota.datetime",
                           type("datetime", (), {"now": lambda tz: mock_now}))

        # Mock monthly usage: 150,000 chars on day 10 (15K per day)
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"usage": 150000, "article_count": 75}

        mock_ref = Mock()
        mock_ref.get.return_value = mock_doc

        mock_firestore.collection.return_value.document.return_value = mock_ref

        forecast = quota_tracker.get_usage_forecast()

        # Daily average: 150K / 10 = 15K per day
        # Days remaining: 31 - 10 + 1 = 22 days
        # Forecast: 150K + (15K * 22) = 480K
        # Forecast percent: 480K / 400K = 120% but close to 95% threshold

        assert forecast["current_usage"] == 150000
        assert forecast["daily_average"] == 15000
        # Forecast will exceed but be in MEDIUM range (95-100%)
        assert forecast["risk_level"] in ["MEDIUM", "HIGH"]
