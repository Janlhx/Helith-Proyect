import logging
from core.db.connection import get_supabase_client, get_sqlite_connection

logger = logging.getLogger("helith.conversation.repository")


class ConversationRepository:
    """Maneja la persistencia de los mensajes de conversación.

    Soporta Supabase como base principal y SQLite como fallback local.
    """

    def __init__(self):
        self.supabase = get_supabase_client()

    def save_message(
        self, channel_id: str, user_id: str, role: str, content: str
    ):
        """Guarda un mensaje en el historial."""
        if self.supabase:
            try:
                data = {
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                }
                self.supabase.table("conversation_history").insert(data).execute()
                return
            except Exception as e:
                logger.error(
                    f"Error al guardar en Supabase: {e}. Usando fallback."
                )

        # Fallback a SQLite
        self._save_sqlite(channel_id, user_id, role, content)

    def get_history(self, channel_id: str, limit: int = 10):
        """Recupera los últimos N mensajes de un canal para dar contexto."""
        if self.supabase:
            try:
                response = (
                    self.supabase.table("conversation_history")
                    .select("role", "content")
                    .eq("channel_id", channel_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                # Volteamos la lista para que quede en orden cronológico
                return list(reversed(response.data))
            except Exception as e:
                logger.error(
                    f"Error al leer de Supabase: {e}. Usando fallback."
                )

        # Fallback a SQLite
        return self._get_history_sqlite(channel_id, limit)

    def _save_sqlite(
        self, channel_id: str, user_id: str, role: str, content: str
    ):
        """Guarda el mensaje en la base de datos SQLite local."""
        conn = get_sqlite_connection()
        if not conn:
            logger.critical("No se pudo conectar a SQLite de fallback.")
            return

        try:
            with conn:
                # Nos aseguramos de que la tabla exista
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.execute(
                    """
                    INSERT INTO conversation_history 
                    (channel_id, user_id, role, content)
                    VALUES (?, ?, ?, ?)
                """,
                    (channel_id, user_id, role, content),
                )
        except Exception as e:
            logger.error(f"Error al guardar en SQLite: {e}")
        finally:
            conn.close()

    def _get_history_sqlite(self, channel_id: str, limit: int = 10):
        """Recupera el historial de SQLite local."""
        conn = get_sqlite_connection()
        if not conn:
            return []

        try:
            with conn:
                # Nos aseguramos de que la tabla exista
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                cursor = conn.execute(
                    """
                    SELECT role, content FROM conversation_history
                    WHERE channel_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (channel_id, limit),
                )
                rows = cursor.fetchall()
                # Convertimos a formato de diccionario compatible con Supabase
                history = [
                    {"role": row["role"], "content": row["content"]}
                    for row in rows
                ]
                return list(reversed(history))
        except Exception as e:
            logger.error(f"Error al leer de SQLite: {e}")
            return []
        finally:
            conn.close()


conversation_repo = ConversationRepository()
