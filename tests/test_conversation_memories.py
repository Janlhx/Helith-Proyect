import os

import pytest

from domains.conversation.repository import ConversationRepository


@pytest.fixture
def temp_repo(tmp_path):
    """Fixture que crea un ConversationRepository usando una base SQLite temporal."""
    db_file = tmp_path / "test_memories.db"
    os.environ["SQLITE_DB_PATH"] = str(db_file)

    # Creamos repositorio forzando que supabase sea None para usar el fallback
    repo = ConversationRepository()
    repo.supabase = None

    yield repo

    # Limpieza
    if db_file.exists():
        try:
            os.remove(db_file)
        except Exception:
            pass


def test_cosine_similarity(temp_repo):
    """Verifica matemáticamente los cálculos de similitud de coseno."""
    # Similitud idéntica
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    assert pytest.approx(temp_repo._cosine_similarity(v1, v2)) == 1.0

    # Ortogonales (similitud 0)
    v3 = [1.0, 0.0]
    v4 = [0.0, 1.0]
    assert temp_repo._cosine_similarity(v3, v4) == 0.0

    # Opuestos (similitud -1.0)
    v5 = [1.0, 0.0]
    v6 = [-1.0, 0.0]
    assert pytest.approx(temp_repo._cosine_similarity(v5, v6)) == -1.0


def test_sqlite_save_and_retrieve_memories(temp_repo):
    """Valida el almacenamiento de memorias y búsqueda semántica en SQLite."""
    # Guardar memorias de prueba en diferentes servidores
    # Dimensión 768 para alinearlo con Gemini models/text-embedding-004
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

    # Este está en un servidor diferente
    temp_repo.save_memory(
        server_id="servidor_b",
        channel_id="canal_2",
        user_id="user_2",
        content="mi carro es de color rojo brillante",
        embedding=emb_rojo,
    )

    # 1. Búsqueda con query cercana a "verde" (emb_verde) en servidor_a
    # Query de búsqueda
    query_emb = [1.0] + [0.0] * 767
    results = temp_repo.search_memories(
        server_id="servidor_a",
        query_embedding=query_emb,
        limit=2,
        threshold=0.5,
    )

    # Debería retornar solo la memoria del verde, ya que la del azul es ortogonal (0.0)
    # y la del rojo pertenece a servidor_b
    assert len(results) == 1
    assert results[0]["content"] == "mi color favorito es el verde oscuro"
    assert results[0]["server_id"] == "servidor_a"
    assert pytest.approx(results[0]["similarity"]) == 1.0

    # 2. Búsqueda en servidor_b con query cercana a "rojo"
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
