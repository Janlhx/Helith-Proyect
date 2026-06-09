import logging

from domains.monitoring.models import TokenUsageLog

logger = logging.getLogger("helith.monitoring.repository")


class MonitoringRepository:
    """Handles persistence of token usage logs.

    Supports Supabase as primary database and SQLite as local fallback.
    """

    def __init__(self):
        from core.db.connection import get_supabase_client

        self.supabase = get_supabase_client()
        self._init_sqlite_db()

    def _init_sqlite_db(self):
        """Initialize fallback tables in SQLite if they don't exist."""
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            logger.warning(
                "Could not establish SQLite connection "
                "to initialize fallback."
            )
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
                    CREATE TABLE IF NOT EXISTS rate_limit_hits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
        except Exception as e:
            logger.error(f"Error initializing tables in SQLite: {e}")
        finally:
            conn.close()

    def save_log(self, log: TokenUsageLog):
        """Save a token usage record."""
        if self.supabase:
            try:
                self.supabase.table("token_usage_logs").insert(log.to_dict()).execute()
                return
            except Exception as e:
                logger.error(
                    f"Error saving token log to Supabase: {e}. Using fallback."
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
                logger.error(f"Error reading logs from Supabase: {e}. Using fallback.")

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
        """Saves the log to local SQLite."""
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            logger.critical("Could not connect to fallback SQLite database.")
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
            logger.error(f"Error saving log to SQLite: {e}")
        finally:
            conn.close()

    def _get_usage_sqlite(self, days: int = 7) -> list[dict]:
        """Retrieves usage logs from local SQLite."""
        from datetime import datetime, timedelta

        from core.db.connection import get_sqlite_connection

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
            logger.error(f"Error reading logs from SQLite: {e}")
            return []
        finally:
            conn.close()

    def get_server_usage_last_days(self, days: int = 7) -> list[dict]:
        """Retrieves token usage grouped by server."""
        if self.supabase:
            try:
                from datetime import datetime, timedelta

                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                response = (
                    self.supabase.table("token_usage_logs")
                    .select("server_id, total_tokens, timestamp")
                    .gte("timestamp", cutoff)
                    .execute()
                )
                return response.data or []
            except Exception as e:
                logger.error(f"Error in Supabase get_server_usage: {e}. Using SQLite.")

        # Fallback to SQLite
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            return []
        try:
            with conn:
                from datetime import datetime, timedelta

                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                cursor = conn.execute(
                    "SELECT server_id, total_tokens, timestamp "
                    "FROM token_usage_logs WHERE timestamp >= ?",
                    (cutoff,),
                )
                return [
                    {
                        "server_id": r["server_id"],
                        "total_tokens": r["total_tokens"],
                        "timestamp": r["timestamp"],
                    }
                    for r in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error reading server usage from SQLite: {e}")
            return []
        finally:
            conn.close()

    def save_rate_limit_hit(self, server_id: str, user_id: str):
        """Registers a rate limit hit in the database."""
        if self.supabase:
            try:
                self.supabase.table("rate_limit_hits").insert(
                    {"server_id": server_id, "user_id": user_id}
                ).execute()
                return
            except Exception as e:
                logger.error(f"Error in Supabase rate limit save: {e}. Using SQLite.")

        # Fallback to SQLite
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            return
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_limit_hits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.execute(
                    "INSERT INTO rate_limit_hits (server_id, user_id) VALUES (?, ?)",
                    (server_id, user_id),
                )
        except Exception as e:
            logger.error(f"Error saving rate limit to SQLite: {e}")
        finally:
            conn.close()

    def get_rate_limit_hits_last_days(self, days: int = 7) -> list[dict]:
        """Retrieves rate limit hits from the last N days."""
        if self.supabase:
            try:
                from datetime import datetime, timedelta

                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                response = (
                    self.supabase.table("rate_limit_hits")
                    .select("server_id, user_id, timestamp")
                    .gte("timestamp", cutoff)
                    .execute()
                )
                return response.data or []
            except Exception as e:
                logger.error(f"Error in Supabase get_rate_limit: {e}. Using SQLite.")

        # Fallback to SQLite
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            return []
        try:
            with conn:
                from datetime import datetime, timedelta

                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                cursor = conn.execute(
                    "SELECT server_id, user_id, timestamp "
                    "FROM rate_limit_hits WHERE timestamp >= ?",
                    (cutoff,),
                )
                return [
                    {
                        "server_id": r["server_id"],
                        "user_id": r["user_id"],
                        "timestamp": r["timestamp"],
                    }
                    for r in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error reading rate limit hits from SQLite: {e}")
            return []
        finally:
            conn.close()


monitoring_repo = MonitoringRepository()
