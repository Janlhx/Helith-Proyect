import logging
import os
import sqlite3

from core.config import settings

logger = logging.getLogger("helith.db")


def get_supabase_client():
    """Inicializa y retorna el cliente de Supabase si existen credenciales."""
    # Importación diferida para no exigir la librería si solo se usa SQLite
    try:
        from supabase import Client, create_client
    except ImportError:
        logger.warning("Librería 'supabase' no instalada. Operando en modo fallback.")
        return None

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Credenciales de Supabase incompletas. Operando en modo fallback."
        )
        return None

    try:
        client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return client
    except Exception as e:
        logger.error(f"Error al conectar a Supabase: {e}")
        return None


def get_sqlite_connection():
    """Retorna una conexión a la base de datos SQLite local."""
    db_path = os.environ.get("SQLITE_DB_PATH", "helith_fallback.db")
    try:
        # Aumentamos timeout a 30s para evitar problemas de bloqueo multi-hilo
        conn = sqlite3.connect(db_path, timeout=30.0)
        # Retornar diccionarios en lugar de tuplas para mayor comodidad
        conn.row_factory = sqlite3.Row
        # Activar claves foráneas
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Exception as e:
        logger.critical(f"Error al conectar a SQLite: {e}")
        return None
