import logging

logger = logging.getLogger("helith.conversation.repository")


class ConversationRepository:
    """Maneja la persistencia de los mensajes de conversación.

    Soporta Supabase como base principal y SQLite como fallback local.
    """

    def __init__(self):
        # Importación diferida para evitar problemas de linter y circulares
        from core.db.connection import get_supabase_client

        self.supabase = get_supabase_client()

    def save_message(self, channel_id: str, user_id: str, role: str, content: str):
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
                logger.error(f"Error al guardar en Supabase: {e}. Usando fallback.")

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
                logger.error(f"Error al leer de Supabase: {e}. Usando fallback.")

        # Fallback a SQLite
        return self._get_history_sqlite(channel_id, limit)

    def _save_sqlite(self, channel_id: str, user_id: str, role: str, content: str):
        """Guarda el mensaje en la base de datos SQLite local."""
        from core.db.connection import get_sqlite_connection

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
        from core.db.connection import get_sqlite_connection

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
                    {"role": row["role"], "content": row["content"]} for row in rows
                ]
                return list(reversed(history))
        except Exception as e:
            logger.error(f"Error al leer de SQLite: {e}")
            return []
        finally:
            conn.close()

    def save_memory(
        self,
        server_id: str,
        channel_id: str,
        user_id: str,
        content: str,
        embedding: list[float],
    ):
        """Guarda un embedding de memoria semántica en la base de datos."""
        if self.supabase:
            try:
                data = {
                    "server_id": server_id,
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "content": content,
                    "embedding": embedding,
                }
                self.supabase.table("conversation_memories").insert(data).execute()
                return
            except Exception as e:
                logger.error(
                    f"Error al guardar memoria en Supabase: {e}. Usando fallback."
                )

        # Fallback a SQLite
        self._save_memory_sqlite(server_id, channel_id, user_id, content, embedding)

    def search_memories(
        self,
        server_id: str,
        query_embedding: list[float],
        limit: int = 3,
        threshold: float = 0.7,
    ):
        """Busca memorias semánticas similares en el servidor actual."""
        if self.supabase:
            try:
                response = self.supabase.rpc(
                    "match_memories",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": threshold,
                        "match_count": limit,
                        "p_server_id": server_id,
                    },
                ).execute()
                return response.data if response.data else []
            except Exception as e:
                logger.error(
                    f"Error al buscar memorias en Supabase: {e}. Usando fallback."
                )

        # Fallback a SQLite
        return self._search_memories_sqlite(
            server_id, query_embedding, limit, threshold
        )

    def _save_memory_sqlite(
        self,
        server_id: str,
        channel_id: str,
        user_id: str,
        content: str,
        embedding: list[float],
    ):
        """Guarda la memoria en SQLite serializando el embedding en JSON."""
        import json

        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            logger.critical("No se pudo conectar a SQLite para guardar memoria.")
            return

        try:
            with conn:
                self._ensure_memories_table(conn)
                embedding_json = json.dumps(embedding)
                conn.execute(
                    """
                    INSERT INTO conversation_memories
                    (server_id, channel_id, user_id, content, embedding)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (server_id, channel_id, user_id, content, embedding_json),
                )
        except Exception as e:
            logger.error(f"Error al guardar memoria en SQLite: {e}")
        finally:
            conn.close()

    def _search_memories_sqlite(
        self,
        server_id: str,
        query_embedding: list[float],
        limit: int = 3,
        threshold: float = 0.7,
    ):
        """Busca memorias en SQLite calculando similitud en Python puro."""
        import json

        from core.db.connection import get_sqlite_connection

        conn = get_sqlite_connection()
        if not conn:
            return []

        try:
            with conn:
                self._ensure_memories_table(conn)
                cursor = conn.execute(
                    """
                    SELECT id, server_id, channel_id, user_id, content, embedding
                    FROM conversation_memories
                    WHERE server_id = ?
                """,
                    (server_id,),
                )
                rows = cursor.fetchall()

            memories = []
            for row in rows:
                try:
                    emb = json.loads(row["embedding"])
                    similarity = self._cosine_similarity(query_embedding, emb)
                    if similarity >= threshold:
                        memories.append(
                            {
                                "id": row["id"],
                                "server_id": row["server_id"],
                                "channel_id": row["channel_id"],
                                "user_id": row["user_id"],
                                "content": row["content"],
                                "similarity": similarity,
                            }
                        )
                except Exception as ex:
                    logger.error(
                        f"Error procesando fila de memoria SQLite {row['id']}: {ex}"
                    )

            # Ordenar por similitud y limitar
            memories.sort(key=lambda x: x["similarity"], reverse=True)
            return memories[:limit]
        except Exception as e:
            logger.error(f"Error al buscar memorias en SQLite: {e}")
            return []
        finally:
            conn.close()

    def _ensure_memories_table(self, conn):
        """Asegura que la tabla de memorias exista en SQLite."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        """Calcula la similitud de coseno entre dos vectores en Python puro."""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude_v1 = sum(a * a for a in v1) ** 0.5
        magnitude_v2 = sum(b * b for b in v2) ** 0.5
        if magnitude_v1 == 0 or magnitude_v2 == 0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)


conversation_repo = ConversationRepository()
