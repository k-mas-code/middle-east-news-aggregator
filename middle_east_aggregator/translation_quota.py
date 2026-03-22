"""
Translation quota tracking and management.

Implements hard limits and monitoring to ensure we never exceed the
Google Cloud Translation API free tier (500K characters/month).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from google.cloud import firestore

from .translation_config import TranslationConfig

logger = logging.getLogger(__name__)


@dataclass
class QuotaStatus:
    """Current quota usage status."""
    month: str  # Format: "YYYY-MM"
    usage: int  # Characters used this month
    usage_percent: float  # Percentage of safe limit used
    remaining_chars: int  # Characters remaining in safe limit
    article_count: int  # Number of articles translated this month
    status: str  # "SAFE" | "WARNING" | "CRITICAL"


class QuotaTracker:
    """
    Quota tracking with Firestore persistence.

    Tracks daily and monthly translation usage to enforce free tier limits.
    All writes use transactions to prevent race conditions.
    """

    def __init__(self, db: Optional[firestore.Client] = None):
        """
        Initialize quota tracker.

        Args:
            db: Firestore client. If None, creates a new client.
        """
        self.db = db or firestore.Client(project=TranslationConfig.GCP_PROJECT_ID)
        self.quota_collection = self.db.collection("translation_quota")
        self.audit_collection = self.db.collection("translation_audit")

    def _get_current_month(self) -> str:
        """Get current month string in YYYY-MM format."""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _get_current_date(self) -> str:
        """Get current date string in YYYY-MM-DD format."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def get_monthly_usage(self) -> int:
        """
        Get total character usage for current month.

        Returns:
            Total characters translated this month
        """
        month = self._get_current_month()
        doc_ref = self.quota_collection.document(month)
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict().get("usage", 0)
        return 0

    def get_daily_usage(self) -> int:
        """
        Get total character usage for today.

        Returns:
            Total characters translated today
        """
        date = self._get_current_date()
        doc_ref = self.quota_collection.document(f"daily_{date}")
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict().get("usage", 0)
        return 0

    @firestore.transactional
    def _increment_usage_transaction(
        self,
        transaction: firestore.Transaction,
        month_ref: firestore.DocumentReference,
        daily_ref: firestore.DocumentReference,
        char_count: int
    ) -> None:
        """
        Atomically increment monthly and daily usage.

        This is called within a Firestore transaction to prevent race conditions.
        """
        # Read current values
        month_doc = month_ref.get(transaction=transaction)
        daily_doc = daily_ref.get(transaction=transaction)

        month_data = month_doc.to_dict() if month_doc.exists else {
            "usage": 0,
            "article_count": 0,
            "created_at": firestore.SERVER_TIMESTAMP
        }

        daily_data = daily_doc.to_dict() if daily_doc.exists else {
            "usage": 0,
            "article_count": 0,
            "created_at": firestore.SERVER_TIMESTAMP
        }

        # Increment values
        month_data["usage"] += char_count
        month_data["article_count"] += 1
        month_data["updated_at"] = firestore.SERVER_TIMESTAMP

        daily_data["usage"] += char_count
        daily_data["article_count"] += 1
        daily_data["updated_at"] = firestore.SERVER_TIMESTAMP

        # Write back
        transaction.set(month_ref, month_data)
        transaction.set(daily_ref, daily_data)

    def can_translate(self, char_count: int) -> bool:
        """
        Check if we can translate without exceeding limits.

        Args:
            char_count: Number of characters to translate

        Returns:
            True if translation would stay within limits
        """
        monthly_usage = self.get_monthly_usage()
        daily_usage = self.get_daily_usage()
        safe_limit = TranslationConfig.get_safe_limit_chars()

        # Check monthly limit
        if monthly_usage + char_count > safe_limit:
            logger.warning(
                f"Translation would exceed monthly safe limit: "
                f"{monthly_usage + char_count} > {safe_limit}"
            )
            return False

        # Check daily limit
        if daily_usage + char_count > TranslationConfig.DAILY_LIMIT_CHARS:
            logger.warning(
                f"Translation would exceed daily limit: "
                f"{daily_usage + char_count} > {TranslationConfig.DAILY_LIMIT_CHARS}"
            )
            return False

        return True

    def record_translation(
        self,
        char_count: int,
        article_id: str,
        translation_mode: str,
        success: bool
    ) -> None:
        """
        Record a translation in quota tracking and audit log.

        Uses Firestore transaction to ensure atomic increment.

        Args:
            char_count: Number of input characters translated
            article_id: ID of the article that was translated
            translation_mode: Translation mode used
            success: Whether the translation succeeded
        """
        month = self._get_current_month()
        date = self._get_current_date()

        month_ref = self.quota_collection.document(month)
        daily_ref = self.quota_collection.document(f"daily_{date}")

        # Use transaction for atomic increment
        transaction = self.db.transaction()
        self._increment_usage_transaction(
            transaction,
            month_ref,
            daily_ref,
            char_count
        )

        # Record in audit log (outside transaction for performance)
        try:
            self.audit_collection.add({
                "article_id": article_id,
                "char_count": char_count,
                "mode": translation_mode,
                "success": success,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "month": month,
                "date": date
            })
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            # Don't fail the whole operation if audit fails

    def get_quota_status(self) -> QuotaStatus:
        """
        Get comprehensive quota status.

        Returns:
            QuotaStatus with current usage and limits
        """
        month = self._get_current_month()
        usage = self.get_monthly_usage()
        safe_limit = TranslationConfig.get_safe_limit_chars()
        usage_percent = usage / safe_limit if safe_limit > 0 else 0
        remaining = max(0, safe_limit - usage)

        # Get article count
        doc_ref = self.quota_collection.document(month)
        doc = doc_ref.get()
        article_count = 0
        if doc.exists:
            article_count = doc.to_dict().get("article_count", 0)

        # Determine status
        if usage_percent >= 0.95:
            status = "CRITICAL"
        elif usage_percent >= 0.80:
            status = "WARNING"
        else:
            status = "SAFE"

        return QuotaStatus(
            month=month,
            usage=usage,
            usage_percent=usage_percent,
            remaining_chars=remaining,
            article_count=article_count,
            status=status
        )

    def get_recommendations(self, status: QuotaStatus) -> list[str]:
        """
        Generate recommendations based on quota status.

        Args:
            status: Current quota status

        Returns:
            List of recommended actions
        """
        recommendations = []

        if status.status == "CRITICAL":
            recommendations.append(
                "URGENT: Quota at 95%+. Translation is disabled. "
                "Review usage in audit logs and consider upgrading plan."
            )
        elif status.status == "WARNING":
            recommendations.append(
                "WARNING: Quota at 80%+. Consider switching to titles-only mode "
                "or reducing translation frequency."
            )

        if status.usage_percent >= 0.70:
            recommendations.append(
                "Approaching quota limit. Monitor daily usage closely."
            )

        # Calculate days remaining in month
        now = datetime.now(timezone.utc)
        days_in_month = 31  # Conservative estimate
        day_of_month = now.day
        days_remaining = days_in_month - day_of_month + 1

        if days_remaining > 0:
            daily_budget = status.remaining_chars / days_remaining
            recommendations.append(
                f"Daily budget for rest of month: ~{int(daily_budget)} chars/day "
                f"({days_remaining} days remaining)"
            )

        return recommendations

    def get_usage_forecast(self) -> dict:
        """
        Forecast month-end usage based on current trends.

        Returns:
            Dictionary with forecast data and recommendations
        """
        now = datetime.now(timezone.utc)
        day_of_month = now.day
        current_usage = self.get_monthly_usage()
        safe_limit = TranslationConfig.get_safe_limit_chars()

        # Calculate daily average usage so far
        daily_average = current_usage / day_of_month if day_of_month > 0 else 0

        # Estimate days in month (conservative: 31)
        days_in_month = 31
        days_remaining = days_in_month - day_of_month + 1

        # Forecast month-end usage
        forecast_usage = current_usage + (daily_average * days_remaining)
        forecast_percent = forecast_usage / safe_limit if safe_limit > 0 else 0

        # Determine risk level
        if forecast_percent > 1.0:
            risk_level = "HIGH"
            recommendation = (
                f"Current trend will exceed safe limit by {int((forecast_percent - 1.0) * 100)}%. "
                f"Reduce translation mode immediately."
            )
        elif forecast_percent > 0.95:
            risk_level = "MEDIUM"
            recommendation = (
                "Current trend approaches safe limit. "
                "Consider switching to titles-only mode."
            )
        else:
            risk_level = "LOW"
            recommendation = "Current usage trend is within safe limits."

        return {
            "current_usage": current_usage,
            "current_day": day_of_month,
            "days_in_month": days_in_month,
            "days_remaining": days_remaining,
            "daily_average": int(daily_average),
            "forecast_month_end": int(forecast_usage),
            "forecast_percent": forecast_percent,
            "safe_limit": safe_limit,
            "risk_level": risk_level,
            "recommendation": recommendation
        }
