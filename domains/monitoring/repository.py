import logging

from domains.monitoring.models import TokenUsageLog

logger = logging.getLogger("helith.monitoring.repository")


class MonitoringRepository:
    """Maneja la persistencia de los logs de uso de tokens.

    Soporta Supabase como base principal y SQLite como fallback local.
    """

    def __init__(self):
        from core.db.connection import get_supabase_client

        self.supabase = get_supabase_client()

    def save_log(self, log: TokenUsageLog):
        """Guarda un registro de uso de tokens."""
        if self.supabase:
            try:
                self.supabase.table("token_usage_logs").insert(
                    log.to_dict()
                ).execute()
                return
            except Exception as e:
                logger.error(
                    f"Error al guardar log de tokens en Supabase: {e}. Usando fallback."
                )

        self._save_sqlite(log)

    def get_usage_last_days(self, days: int = 7) -> list[dict]:
        """Recupera los logs de los últimos N días agrupados por día y modelo."""
        if self.supabase:
            try:
                from datetime import datetime, timedelta

                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                response = (
                    self.supabase.table("token_usage_logs")
                    .select("model_name, total_tokens, timestamp")
                    .gte("timestamp", cutoff)
                    .order("timestamp", desc=False)
                    .execute()
                )
                return response.data or []
            except Exception as e:
                logger.error(
                    f"Error al leer logs de Supabase: {e}. Usando fallback."
                )

        return self._get_usage_sqlite(days)

    def get_total_by_model(self, days: int = 30) -> dict[str, int]:
        """Devuelve el total de tokens consumidos por modelo en los últimos N días."""
        logs = self.get_usage_last_days(days)
        totals: dict[str, int] = {}
        for log in logs:
            model = log.get("model_name", "unknown")
            totals[model] = totals.get(model, 0) + log.get("total_tokens", 0)
        return totals

    def _save_sqlite(self, log: TokenUsageLog):
        """Guarda el log en SQLite local."""
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            logger.critical("No se pudo conectar a SQLite de fallback.")
            return

        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS token_usage_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_name TEXT NOT NULL,
                        server_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        prompt_tokens INTEGER NOT NULL,
                        completion_tokens INTEGER NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.execute(
                    """
                    INSERT INTO token_usage_logs
                    (model_name, server_id, user_id,
                     prompt_tokens, completion_tokens, total_tokens, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log.model_name,
                        log.server_id,
                        log.user_id,
                        log.prompt_tokens,
                        log.completion_tokens,
                        log.total_tokens,
                        log.timestamp.isoformat(),
                    ),
                )
        except Exception as e:
            logger.error(f"Error al guardar log en SQLite: {e}")
        finally:
            conn.close()

    def _get_usage_sqlite(self, days: int = 7) -> list[dict]:
        """Recupera los logs de SQLite local."""
        from core.db.connection import get_sqlite_connection
        from datetime import datetime, timedelta

        conn = get_sqlite_connection()
        if not conn:
            return []

        try:
            with conn:
                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                cursor = conn.execute(
                    """
                    SELECT model_name, total_tokens, timestamp
                    FROM token_usage_logs
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """,
                    (cutoff,),
                )
                rows = cursor.fetchall()
                return [
                    {
                        "model_name": row["model_name"],
                        "total_tokens": row["total_tokens"],
                        "timestamp": row["timestamp"],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error al leer logs de SQLite: {e}")
            return []
        finally:
            conn.close()


monitoring_repo = MonitoringRepository()
