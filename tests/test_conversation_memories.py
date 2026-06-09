import os

import pytest

from domains.conversation.repository import ConversationRepository


@pytest.fixture
def temp_repo(tmp_path):
    """Fixture that creates a ConversationRepository using a temporary SQLite db."""
    db_file = tmp_path / "test_memories.db"
    os.environ["SQLITE_DB_PATH"] = str(db_file)

    # Create repository forcing supabase to be None to use the fallback
    repo = ConversationRepository()
    repo.supabase = None

    yield repo

    # Cleanup
    if db_file.exists():
        try:
            os.remove(db_file)
        except Exception:
            pass


def test_cosine_similarity(temp_repo):
    """Mathematically verifies cosine similarity calculations."""
    # Identical similarity
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    assert pytest.approx(temp_repo._cosine_similarity(v1, v2)) == 1.0

    # Orthogonal (similarity 0)
    v3 = [1.0, 0.0]
    v4 = [0.0, 1.0]
    assert temp_repo._cosine_similarity(v3, v4) == 0.0

    # Opposite (similarity -1.0)
    v5 = [1.0, 0.0]
    v6 = [-1.0, 0.0]
    assert pytest.approx(temp_repo._cosine_similarity(v5, v6)) == -1.0


def test_sqlite_save_and_retrieve_memories(temp_repo):
    """Validates memory storage and semantic search in SQLite."""
    # Save test memories in different servers
    # Dimension 768 to align with Gemini models/text-embedding-004
    emb_verde = [0.9] + [0.0] * 767
    emb_azul = [0.0, 0.9] + [0.0] * 766
    emb_rojo = [-0.9] + [0.0] * 767

    temp_repo.save_memory(
        server_id="servidor_a",
        channel_id="canal_1",
        user_id="user_1",
        content="mi color favorito es el verde oscuro",
        embedding=emb_verde,
    )

    temp_repo.save_memory(
        server_id="servidor_a",
        channel_id="canal_1",
        user_id="user_1",
        content="me encanta el color azul marino",
        embedding=emb_azul,
    )

    # This one is in a different server
    temp_repo.save_memory(
        server_id="servidor_b",
        channel_id="canal_2",
        user_id="user_2",
        content="mi carro es de color rojo brillante",
        embedding=emb_rojo,
    )

    # 1. Search with a query close to "green" (emb_verde) in servidor_a
    # Search query
    query_emb = [1.0] + [0.0] * 767
    results = temp_repo.search_memories(
        server_id="servidor_a",
        query_embedding=query_emb,
        limit=2,
        threshold=0.5,
    )

    # Should return only the green memory, as blue is orthogonal (0.0)
    # and red belongs to servidor_b
    assert len(results) == 1
    assert results[0]["content"] == "mi color favorito es el verde oscuro"
    assert results[0]["server_id"] == "servidor_a"
    assert pytest.approx(results[0]["similarity"]) == 1.0

    # 2. Search in servidor_b with query close to "red"
    query_emb_rojo = [-1.0] + [0.0] * 767
    results_b = temp_repo.search_memories(
        server_id="servidor_b",
        query_embedding=query_emb_rojo,
        limit=2,
        threshold=0.5,
    )

    assert len(results_b) == 1
    assert results_b[0]["content"] == "mi carro es de color rojo brillante"
    assert pytest.approx(results_b[0]["similarity"]) == 1.0
