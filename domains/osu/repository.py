import logging
from typing import Any, Dict, List

from domains.osu.models import OsuSnapshot

logger = logging.getLogger("helith.osu.repository")


class OsuRepository:
    """Handles persistence of osu! progress snapshots.

    Uses Supabase as the primary backend and SQLite as a resilient local fallback.
    """

    def __init__(self):
        # Deferred import to avoid circular dependencies and make Supabase optional
        from core.db.connection import get_supabase_client

        self.supabase = get_supabase_client()

    def save_snapshot(self, snapshot: OsuSnapshot) -> None:
        """Saves a player snapshot to the database."""
        if self.supabase:
            try:
                data = snapshot.to_dict()
                self.supabase.table("osu_snapshots").insert(data).execute()
                logger.info(
                    f"osu! snapshot for '{snapshot.username}' saved to Supabase."
                )
                return
            except Exception as e:
                logger.error(
                    f"Error saving snapshot to Supabase: {e}. "
                    "Falling back to local SQLite."
                )

        # Fallback local a SQLite
        self._save_sqlite(snapshot)

    def get_history(self, username: str, limit: int = 90) -> List[Dict[str, Any]]:
        """Retrieves historical progress snapshots for a player."""
        cleaned_username = username.strip().lower()

        if self.supabase:
            try:
                # Query case-insensitively
                response = (
                    self.supabase.table("osu_snapshots")
                    .select("*")
                    .ilike("username", cleaned_username)
                    .order("recorded_at", desc=True)
                    .limit(limit)
                    .execute()
                )

                # Return chronologically (oldest first)
                return list(reversed(response.data))
            except Exception as e:
                logger.error(
                    f"Error reading snapshots from Supabase: {e}. "
                    "Falling back to local SQLite."
                )

        # Fallback local a SQLite
        return self._get_history_sqlite(cleaned_username, limit)

    def _save_sqlite(self, snapshot: OsuSnapshot) -> None:
        """Saves the snapshot to the local SQLite database."""
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            logger.critical(
                "Could not connect to SQLite for local osu! persistence."
            )
            return

        try:
            with conn:
                # Make sure the table exists
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS osu_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        osu_id INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        global_rank INTEGER NOT NULL,
                        pp REAL NOT NULL,
                        play_time INTEGER NOT NULL,
                        improvement_indicator REAL NOT NULL,
                        recorded_at TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                data = snapshot.to_dict()
                conn.execute(
                    """
                    INSERT INTO osu_snapshots 
                    (osu_id, username, global_rank, pp, play_time, 
                     improvement_indicator, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["osu_id"],
                        data["username"].lower(),  # Case-insensitive searches
                        data["global_rank"],
                        data["pp"],
                        data["play_time"],
                        data["improvement_indicator"],
                        data["recorded_at"],
                    ),
                )
                logger.info(
                    f"osu! snapshot for '{snapshot.username}' "
                    "saved to local SQLite."
                )
        except Exception as e:
            logger.error(f"Error writing snapshot to SQLite: {e}")
        finally:
            conn.close()

    def _get_history_sqlite(
        self, username: str, limit: int = 90
    ) -> List[Dict[str, Any]]:
        """Retrieves snapshot history from local SQLite."""
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            return []

        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS osu_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        osu_id INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        global_rank INTEGER NOT NULL,
                        pp REAL NOT NULL,
                        play_time INTEGER NOT NULL,
                        improvement_indicator REAL NOT NULL,
                        recorded_at TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                cursor = conn.execute(
                    """
                    SELECT * FROM osu_snapshots
                    WHERE username = ?
                    ORDER BY recorded_at DESC
                    LIMIT ?
                """,
                    (username, limit),
                )
                rows = cursor.fetchall()

                # Map to compatible dictionaries
                history = []
                for row in rows:
                    history.append(
                        {
                            "id": row["id"],
                            "osu_id": row["osu_id"],
                            "username": row["username"],
                            "global_rank": row["global_rank"],
                            "pp": row["pp"],
                            "play_time": row["play_time"],
                            "improvement_indicator": row["improvement_indicator"],
                            "recorded_at": row["recorded_at"],
                        }
                    )

                # Return chronologically (oldest first)
                return list(reversed(history))
        except Exception as e:
            logger.error(f"Error reading snapshots from SQLite: {e}")
            return []
        finally:
            conn.close()


osu_repo = OsuRepository()
