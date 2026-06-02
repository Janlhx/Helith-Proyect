import logging
from datetime import datetime, timezone

from domains.monitoring.models import TokenUsageLog
from domains.monitoring.repository import monitoring_repo

logger = logging.getLogger("helith.monitoring.service")

# Approximate free limits (tokens per day)
# Gemini Flash: ~1M tokens/day free
# NVIDIA NIM: no strict public quota — 5M as operational reference
# Groq: ~500K tokens/day free
MODEL_DAILY_LIMITS: dict[str, int] = {
    "gemini-2.5-flash": 1_000_000,
    "nvidia/deepseek-ai/deepseek-v4-flash": 5_000_000,
    "nvidia/nvidia/nemotron-3-super-120b-a12b": 5_000_000,
    "nvidia/google/gemma-4-31b-it": 5_000_000,
    "llama-3.3-70b-versatile": 500_000,
    "deepseek-r1-distill-llama-70b": 500_000,
    "llama-3.1-8b-instant": 500_000,
    "meta-llama/llama-4-scout-17b-16e-instruct": 500_000,
}
ALERT_THRESHOLD = 0.80  # Alert when exceeding 80% of daily limit


class MonitoringService:
    """Token consumption monitoring and prediction service."""

    def record_usage(
        self,
        model_name: str,
        server_id: str,
        user_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """Record token usage from an LLM call."""
        log = TokenUsageLog(
            model_name=model_name,
            server_id=server_id,
            user_id=user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        monitoring_repo.save_log(log)
        logger.info(
            f"Usage recorded — Model: {model_name}, "
            f"Tokens: {log.total_tokens} (prompt={prompt_tokens}, "
            f"completion={completion_tokens})"
        )

    def get_daily_stats(self, days: int = 7) -> dict:
        """Calculates usage statistics of the last N days."""
        logs = monitoring_repo.get_usage_last_days(days)

        # Group by day
        daily: dict[str, int] = {}
        total_messages = 0
        for log in logs:
            ts = log.get("timestamp", "")
            day = ts[:10] if ts else "unknown"  # Only the date YYYY-MM-DD
            daily[day] = daily.get(day, 0) + log.get("total_tokens", 0)
            total_messages += 1

        total = sum(daily.values())
        avg_per_day = total / days if days > 0 else 0

        return {
            "total_tokens": total,
            "messages": total_messages,
            "avg_tokens_per_day": round(avg_per_day),
            "daily_breakdown": daily,
            "by_model": monitoring_repo.get_total_by_model(days),
            "days_analyzed": days,
        }

    def predict_exhaustion(self, model_name: str) -> dict:
        """Predicts in how many days the model's free quota will be exhausted.

        Uses a simple linear regression (average of the last 7 days).
        """
        logs_7d = monitoring_repo.get_usage_last_days(7)

        model_logs = [
            entry for entry in logs_7d if entry.get("model_name") == model_name
        ]
        tokens_7d = sum(entry.get("total_tokens", 0) for entry in model_logs)
        avg_daily = tokens_7d / 7 if tokens_7d > 0 else 0

        daily_limit = MODEL_DAILY_LIMITS.get(model_name, 500_000)

        if avg_daily <= 0:
            return {
                "model": model_name,
                "avg_daily_tokens": 0,
                "daily_limit": daily_limit,
                "pct_used": 0.0,
                "days_until_exhaustion": None,
                "alert": False,
                "message": "Insufficient data for prediction.",
            }

        pct_used = avg_daily / daily_limit
        days_until = daily_limit / avg_daily if avg_daily > 0 else None

        alert = pct_used >= ALERT_THRESHOLD

        return {
            "model": model_name,
            "avg_daily_tokens": round(avg_daily),
            "daily_limit": daily_limit,
            "pct_used": round(pct_used * 100, 1),
            "days_until_exhaustion": (round(days_until, 1) if days_until else None),
            "alert": alert,
            "message": (
                f"⚠️ Alert: consuming {round(pct_used * 100, 1)}% "
                "of the daily limit."
                if alert
                else f"✅ Normal consumption: {round(pct_used * 100, 1)}% "
                "of the daily limit."
            ),
        }

    def record_rate_limit(self, server_id: str, user_id: str):
        """Records a rate limit hit."""
        monitoring_repo.save_rate_limit_hit(server_id, user_id)
        logger.warning(
            f"Rate limit reached — Server: {server_id}, User: {user_id}"
        )

    def get_server_analysis(self, days: int = 7) -> dict:
        """Analyzes behavior, token volume, and infractions per server.

        Offers mitigation recommendations (recommended cooldowns).
        Deduplicates server IDs (normalizes spacing strips in the ID).
        """
        usage_logs = monitoring_repo.get_server_usage_last_days(days)
        rate_logs = monitoring_repo.get_rate_limit_hits_last_days(days)

        # Group usage by server - normalize ID by stripping spaces
        servers: dict[str, dict] = {}
        for entry in usage_logs:
            raw_srv = entry.get("server_id", "DM")
            srv = str(raw_srv).strip() if raw_srv else "DM"
            if srv not in servers:
                servers[srv] = {
                    "total_tokens": 0,
                    "messages": 0,
                    "rate_limits": 0,
                }
            servers[srv]["total_tokens"] += entry.get("total_tokens", 0)
            servers[srv]["messages"] += 1

        # Group rate limits by server
        for entry in rate_logs:
            raw_srv = entry.get("server_id", "DM")
            srv = str(raw_srv).strip() if raw_srv else "DM"
            if srv not in servers:
                servers[srv] = {
                    "total_tokens": 0,
                    "messages": 0,
                    "rate_limits": 0,
                }
            servers[srv]["rate_limits"] += 1

        # Analyze and recommend dynamic limits
        analysis = {}
        for srv, data in servers.items():
            avg_tokens = data["total_tokens"] / days if days > 0 else 0
            avg_msg = data["messages"] / days if days > 0 else 0

            # Classify usage level and formulate preventive suggestions
            if avg_tokens > 100000 or data["rate_limits"] > 15:
                status = "CRITICAL"
                recommendation = (
                    "Increase cooldown to 180s and limit to 2 messages "
                    "per minute per user."
                )
            elif avg_tokens > 30000 or data["rate_limits"] > 5:
                status = "WARNING"
                recommendation = (
                    "Increase cooldown to 120s or limit to 3 messages "
                    "per minute per user."
                )
            else:
                status = "NORMAL"
                recommendation = (
                    "Maintain current cooldown of 60s (5 messages per minute)."
                )

            analysis[srv] = {
                "server_id": srv,
                "total_tokens": data["total_tokens"],
                "avg_tokens_per_day": round(avg_tokens),
                "messages_sent": data["messages"],
                "avg_messages_per_day": round(avg_msg, 1),
                "rate_limit_hits": data["rate_limits"],
                "status": status,
                "recommended_cooldown": recommendation,
            }

        return analysis

    def get_full_report(self) -> dict:
        """Generates the full report for the dashboard."""
        stats = self.get_daily_stats(days=7)
        stats_30d = self.get_daily_stats(days=30)

        predictions = {}
        for model in MODEL_DAILY_LIMITS:
            predictions[model] = self.predict_exhaustion(model)

        # Only include models with real data to avoid noise
        active_predictions = {
            m: p for m, p in predictions.items() if p["avg_daily_tokens"] > 0
        }

        alerts = [p for p in predictions.values() if p["alert"]]
        server_reports = self.get_server_analysis(days=7)

        # Active models sorted by consumption
        by_model = stats.get("by_model", {})
        active_models = sorted(by_model.items(), key=lambda x: x[1], reverse=True)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "daily_stats": {
                "total_tokens": stats["total_tokens"],
                "messages": stats["messages"],
                "avg_tokens_per_day": stats["avg_tokens_per_day"],
                "daily_breakdown": stats["daily_breakdown"],
                "by_model": stats["by_model"],
            },
            "monthly_stats": {
                "total_tokens": stats_30d["total_tokens"],
                "messages": stats_30d["messages"],
                "avg_tokens_per_day": stats_30d["avg_tokens_per_day"],
            },
            "predictions": predictions,
            "active_predictions": active_predictions,
            "active_alerts": len(alerts),
            "alert_models": [a["model"] for a in alerts],
            "active_models": active_models,
            "server_usage_analysis": server_reports,
        }


monitoring_service = MonitoringService()
