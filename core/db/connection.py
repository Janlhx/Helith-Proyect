import logging
import os
import sqlite3

from core.config import settings

logger = logging.getLogger("helith.db")


def get_supabase_client():
    """Initializes and returns the Supabase client if credentials exist."""
    # Deferred import to avoid requiring the library if only SQLite is used
    try:
        from supabase import Client, create_client
    except ImportError:
        logger.warning("Library 'supabase' not installed. Operating in fallback mode.")
        return None

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Incomplete Supabase credentials. Operating in fallback mode."
        )
        return None

    try:
        client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return client
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {e}")
        return None


def get_sqlite_connection():
    """Returns a connection to the local SQLite database."""
    db_path = os.environ.get("SQLITE_DB_PATH", "helith_fallback.db")
    try:
        # Increase timeout to 30s to avoid multi-threaded locking issues
        conn = sqlite3.connect(db_path, timeout=30.0)
        # Return dictionaries instead of tuples for convenience
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Exception as e:
        logger.critical(f"Error connecting to SQLite: {e}")
        return None
