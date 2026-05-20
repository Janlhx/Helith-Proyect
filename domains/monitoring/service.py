import logging
from datetime import datetime

from domains.monitoring.models import TokenUsageLog
from domains.monitoring.repository import monitoring_repo

logger = logging.getLogger("helith.monitoring.service")

# Límites gratuitos aproximados (tokens por día)
# Gemini Flash: ~1M tokens/día gratis, Groq: ~500K tokens/día gratis
MODEL_DAILY_LIMITS: dict[str, int] = {
    "gemini-2.5-flash": 1_000_000,
    "llama-3.3-70b-versatile": 500_000,
    "deepseek-r1-distill-llama-70b": 500_000,
    "llama-3.1-8b-instant": 500_000,
    "meta-llama/llama-4-scout-17b-16e-instruct": 500_000,
}
ALERT_THRESHOLD = 0.80  # Alertar cuando se supera el 80% del límite diario


class MonitoringService:
    """Servicio de monitoreo y predicción del consumo de tokens."""

    def record_usage(
        self,
        model_name: str,
        server_id: str,
        user_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """Registra el uso de tokens de una llamada al LLM."""
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
            f"Uso registrado — Modelo: {model_name}, "
            f"Tokens: {log.total_tokens} (prompt={prompt_tokens}, "
            f"completion={completion_tokens})"
        )

    def get_daily_stats(self, days: int = 7) -> dict:
        """Calcula estadísticas de uso de los últimos N días."""
        logs = monitoring_repo.get_usage_last_days(days)

        # Agrupar por día
        daily: dict[str, int] = {}
        for log in logs:
            ts = log.get("timestamp", "")
            day = ts[:10] if ts else "unknown"  # Solo la fecha YYYY-MM-DD
            daily[day] = daily.get(day, 0) + log.get("total_tokens", 0)

        total = sum(daily.values())
        avg_per_day = total / days if days > 0 else 0

        return {
            "total_tokens": total,
            "avg_tokens_per_day": round(avg_per_day),
            "daily_breakdown": daily,
            "by_model": monitoring_repo.get_total_by_model(days),
            "days_analyzed": days,
        }

    def predict_exhaustion(self, model_name: str) -> dict:
        """Predice en cuántos días se agotará la cuota gratuita del modelo.

        Usa una regresión lineal simple (promedio de los últimos 7 días).
        """
        logs_7d = monitoring_repo.get_usage_last_days(7)

        model_logs = [
            entry for entry in logs_7d
            if entry.get("model_name") == model_name
        ]
        tokens_7d = sum(
            entry.get("total_tokens", 0) for entry in model_logs
        )
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
                "message": "Sin datos suficientes para predicción.",
            }

        pct_used = avg_daily / daily_limit
        days_until = daily_limit / avg_daily if avg_daily > 0 else None

        alert = pct_used >= ALERT_THRESHOLD

        return {
            "model": model_name,
            "avg_daily_tokens": round(avg_daily),
            "daily_limit": daily_limit,
            "pct_used": round(pct_used * 100, 1),
            "days_until_exhaustion": (
                round(days_until, 1) if days_until else None
            ),
            "alert": alert,
            "message": (
                f"⚠️ Alerta: consumiendo el {round(pct_used*100,1)}% del límite diario."
                if alert
                else f"✅ Consumo normal: {round(pct_used*100,1)}% del límite diario."
            ),
        }

    def record_rate_limit(self, server_id: str, user_id: str):
        """Registra un impacto de rate-limit."""
        monitoring_repo.save_rate_limit_hit(server_id, user_id)
        logger.warning(f"Rate limit alcanzado — Servidor: {server_id}, Usuario: {user_id}")

    def get_server_analysis(self, days: int = 7) -> dict:
        """Analiza el comportamiento, volumen de tokens e infracciones por servidor.
        
        Ofrece recomendaciones de mitigación (cooldowns recomendados).
        """
        usage_logs = monitoring_repo.get_server_usage_last_days(days)
        rate_logs = monitoring_repo.get_rate_limit_hits_last_days(days)

        # Agrupar uso por servidor
        servers: dict[str, dict] = {}
        for entry in usage_logs:
            srv = entry.get("server_id", "DM")
            if srv not in servers:
                servers[srv] = {"total_tokens": 0, "messages": 0, "rate_limits": 0}
            servers[srv]["total_tokens"] += entry.get("total_tokens", 0)
            servers[srv]["messages"] += 1

        # Agrupar rate limits por servidor
        for entry in rate_logs:
            srv = entry.get("server_id", "DM")
            if srv not in servers:
                servers[srv] = {"total_tokens": 0, "messages": 0, "rate_limits": 0}
            servers[srv]["rate_limits"] += 1

        # Analizar y recomendar límites dinámicos
        analysis = {}
        for srv, data in servers.items():
            avg_tokens = data["total_tokens"] / days if days > 0 else 0
            avg_msg = data["messages"] / days if days > 0 else 0
            
            # Clasificar nivel de uso y formular sugerencias preventivas
            if avg_tokens > 100000 or data["rate_limits"] > 15:
                status = "CRÍTICO"
                recommendation = "Incrementar cooldown a 180s y limitar a 2 mensajes por minuto por usuario."
            elif avg_tokens > 30000 or data["rate_limits"] > 5:
                status = "ADVERTENCIA"
                recommendation = "Incrementar cooldown a 120s o limitar a 3 mensajes por minuto por usuario."
            else:
                status = "NORMAL"
                recommendation = "Mantener cooldown actual de 60s (5 mensajes por minuto)."

            analysis[srv] = {
                "server_id": srv,
                "total_tokens": data["total_tokens"],
                "avg_tokens_per_day": round(avg_tokens),
                "messages_sent": data["messages"],
                "avg_messages_per_day": round(avg_msg, 1),
                "rate_limit_hits": data["rate_limits"],
                "status": status,
                "recommended_cooldown": recommendation
            }

        return analysis

    def get_full_report(self) -> dict:
        """Genera el reporte completo para el dashboard."""
        stats = self.get_daily_stats(days=7)
        predictions = {}
        for model in MODEL_DAILY_LIMITS:
            predictions[model] = self.predict_exhaustion(model)

        alerts = [p for p in predictions.values() if p["alert"]]
        server_reports = self.get_server_analysis(days=7)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "stats_7d": stats,
            "predictions": predictions,
            "active_alerts": len(alerts),
            "alert_models": [a["model"] for a in alerts],
            "server_usage_analysis": server_reports,
        }


monitoring_service = MonitoringService()
