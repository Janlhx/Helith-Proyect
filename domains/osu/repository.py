import logging
from typing import List, Dict, Any
from domains.osu.models import OsuSnapshot

logger = logging.getLogger("helith.osu.repository")

class OsuRepository:
    """Maneja la persistencia de los snapshots de progreso osu!.
    
    Usa Supabase como base principal y SQLite como fallback local resiliente.
    """

    def __init__(self):
        # Importación diferida para evitar ciclos y opcionalidad
        from core.db.connection import get_supabase_client
        self.supabase = get_supabase_client()

    def save_snapshot(self, snapshot: OsuSnapshot) -> None:
        """Guarda un snapshot de jugador en la base de datos."""
        if self.supabase:
            try:
                data = snapshot.to_dict()
                self.supabase.table("osu_snapshots").insert(data).execute()
                logger.info(f"Snapshot de osu! para '{snapshot.username}' guardado en Supabase.")
                return
            except Exception as e:
                logger.error(
                    f"Error al guardar snapshot en Supabase: {e}. Usando fallback local a SQLite."
                )

        # Fallback local a SQLite
        self._save_sqlite(snapshot)

    def get_history(self, username: str, limit: int = 90) -> List[Dict[str, Any]]:
        """Recupera los snapshots de progreso históricos de un jugador."""
        cleaned_username = username.strip().lower()
        
        if self.supabase:
            try:
                # Consultamos de forma que coincida sin distinguir mayúsculas/minúsculas
                response = (
                    self.supabase.table("osu_snapshots")
                    .select("*")
                    .ilike("username", cleaned_username)
                    .order("recorded_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                
                # Devolvemos cronológicamente (más antiguos primero) para la regresión
                return list(reversed(response.data))
            except Exception as e:
                logger.error(
                    f"Error al leer snapshots de Supabase: {e}. Usando fallback local a SQLite."
                )

        # Fallback local a SQLite
        return self._get_history_sqlite(cleaned_username, limit)

    def _save_sqlite(self, snapshot: OsuSnapshot) -> None:
        """Guarda el snapshot en la base de datos SQLite local."""
        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            logger.critical("No se pudo conectar a SQLite para persistencia local de osu!.")
            return

        try:
            with conn:
                # Nos aseguramos de que la tabla exista
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
                    (osu_id, username, global_rank, pp, play_time, improvement_indicator, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["osu_id"],
                        data["username"].lower(),  # Guardar en minúsculas para búsquedas ilike
                        data["global_rank"],
                        data["pp"],
                        data["play_time"],
                        data["improvement_indicator"],
                        data["recorded_at"],
                    ),
                )
                logger.info(f"Snapshot de osu! para '{snapshot.username}' guardado en SQLite local.")
        except Exception as e:
            logger.error(f"Error al escribir snapshot en SQLite: {e}")
        finally:
            conn.close()

    def _get_history_sqlite(self, username: str, limit: int = 90) -> List[Dict[str, Any]]:
        """Recupera el historial de snapshots desde SQLite local."""
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
                
                # Mapear a diccionarios compatibles
                history = []
                for row in rows:
                    history.append({
                        "id": row["id"],
                        "osu_id": row["osu_id"],
                        "username": row["username"],
                        "global_rank": row["global_rank"],
                        "pp": row["pp"],
                        "play_time": row["play_time"],
                        "improvement_indicator": row["improvement_indicator"],
                        "recorded_at": row["recorded_at"],
                    })
                
                # Devolvemos cronológicamente (más antiguo al principio)
                return list(reversed(history))
        except Exception as e:
            logger.error(f"Error al leer snapshots de SQLite: {e}")
            return []
        finally:
            conn.close()

osu_repo = OsuRepository()
