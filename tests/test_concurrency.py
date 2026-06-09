import asyncio
import os
import sqlite3
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
from main import user_cooldown, guild_cooldown
from domains.conversation.service import ConversationService
from core.db.connection import get_sqlite_connection

# Mock Discord classes for rate limit testing
class MockAuthor:
    def __init__(self, author_id):
        self.id = author_id

class MockGuild:
    def __init__(self, guild_id):
        self.id = guild_id

class MockMessage:
    def __init__(self, author_id, guild_id=None):
        self.author = MockAuthor(author_id)
        self.guild = MockGuild(guild_id) if guild_id else None

def test_cooldown_rate_limiting():
    """Verify that per-user and per-guild rate limiting blocks spam."""
    # 1. Test user rate limit (5 messages per minute)
    user_msg = MockMessage(author_id=12345)
    
    # First 5 messages should be allowed (update_rate_limit returns None)
    for _ in range(5):
        assert user_cooldown.get_bucket(user_msg).update_rate_limit() is None
        
    # The 6th message must trigger rate limiting (returns positive retry_after float)
    retry_after = user_cooldown.get_bucket(user_msg).update_rate_limit()
    assert retry_after is not None
    assert retry_after > 0.0

    # 2. Test guild rate limit (20 messages per minute)
    guild_msg = MockMessage(author_id=99999, guild_id=67890)
    
    # First 20 messages should be allowed
    for _ in range(20):
        assert guild_cooldown.get_bucket(guild_msg).update_rate_limit() is None
        
    # The 21st message must trigger rate limiting
    guild_retry = guild_cooldown.get_bucket(guild_msg).update_rate_limit()
    assert guild_retry is not None
    assert guild_retry > 0.0


@pytest.mark.asyncio
@patch("domains.conversation.service.generate_embedding")
@patch("domains.conversation.service.intent_router")
@patch("domains.conversation.service.conversation_repo")
@patch("domains.conversation.service.llm_pool")
async def test_concurrent_message_processing(
    mock_llm_pool, mock_repo, mock_router, mock_embed
):
    """Verify concurrent async conversation requests execute cleanly and in parallel."""
    # Mocking behaviors with a simulated delay to test async concurrency
    async def delayed_generate(*args, **kwargs):
        # Introduce a sleep to force async tasks to run concurrently
        await asyncio.sleep(0.05)
        user_id = kwargs.get("user_id", "")
        if user_id == "user_1":
            return "resp_1"
        elif user_id == "user_2":
            return "resp_2"
        return "resp_generic"

    mock_llm_pool.generate_response = AsyncMock(side_effect=delayed_generate)
    mock_embed.return_value = [0.0] * 768
    mock_router.needs_web_search.return_value = False
    
    # Store dynamic histories for each channel
    histories = {
        "channel_A": [{"role": "user", "content": "hi"}],
        "channel_B": [{"role": "user", "content": "hello"}]
    }
    
    def get_history_mock(channel_id, *args, **kwargs):
        return histories.get(channel_id, [])
        
    mock_repo.get_history.side_effect = get_history_mock
    mock_repo.search_memories.return_value = []
    
    service = ConversationService()
    
    # Trigger concurrent requests for different channels and users
    task1 = service.process_message("channel_A", "server_1", "user_1", "msg_1")
    task2 = service.process_message("channel_B", "server_1", "user_2", "msg_2")
    
    results = await asyncio.gather(task1, task2)
    
    assert results[0] == "resp_1"
    assert results[1] == "resp_2"
    
    # Confirm repo saved messages for both sessions properly
    assert mock_repo.save_message.call_count == 4  # 2 per conversation call (user message + assistant response)


@pytest.mark.asyncio
async def test_sqlite_db_concurrency(tmp_path):
    """Test that SQLite fallback works under heavy concurrent reads/writes without lock crashes."""
    db_file = tmp_path / "test_sqlite_concurrency.db"
    
    # Override environmental db path to temp db
    with patch.dict(os.environ, {"SQLITE_DB_PATH": str(db_file)}):
        # Create test table
        conn = get_sqlite_connection()
        conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT);")
        conn.commit()
        conn.close()
        
        # Define concurrent worker
        async def db_writer(worker_id):
            loop = asyncio.get_running_loop()
            
            # Write to database inside executor to simulate non-blocking database pool operations
            def write():
                c = get_sqlite_connection()
                try:
                    c.execute("INSERT INTO test_table (value) VALUES (?);", (f"val_{worker_id}",))
                    c.commit()
                finally:
                    c.close()
                    
            await loop.run_in_executor(None, write)

        async def db_reader():
            loop = asyncio.get_running_loop()
            
            def read():
                c = get_sqlite_connection()
                try:
                    res = c.execute("SELECT COUNT(*) as cnt FROM test_table;").fetchone()
                    return res["cnt"]
                finally:
                    c.close()
                    
            return await loop.run_in_executor(None, read)

        # Run 30 writers and 20 readers concurrently
        tasks = []
        for i in range(30):
            tasks.append(db_writer(i))
        for _ in range(20):
            tasks.append(db_reader())
            
        # Execute all concurrently
        await asyncio.gather(*tasks)
        
        # Verify result
        final_conn = get_sqlite_connection()
        total_rows = final_conn.execute("SELECT COUNT(*) as cnt FROM test_table;").fetchone()["cnt"]
        final_conn.close()
        
        assert total_rows == 30
