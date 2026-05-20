from unittest.mock import AsyncMock, patch

import pytest

from domains.conversation.service import ConversationService


@pytest.fixture
def service():
    return ConversationService()


@pytest.mark.asyncio
@patch("domains.conversation.service.generate_embedding")
@patch("domains.conversation.service.intent_router")
@patch("domains.conversation.service.conversation_repo")
@patch("domains.conversation.service.llm_pool")
async def test_process_message_success(
    mock_llm_pool, mock_repo, mock_router, mock_embed, service
):
    """Prueba el flujo feliz de la conversación con memorias."""
    # 1. Configurar mocks
    mock_repo.get_history.return_value = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola, qué hay"},
        {"role": "user", "content": "¿qué tal?"},
    ]
    mock_repo.search_memories.return_value = []
    mock_embed.return_value = [0.0] * 768
    mock_router.needs_web_search.return_value = False

    # Simulamos la respuesta de la IA
    mock_llm_pool.generate_response = AsyncMock(
        return_value="todo bien por acá, tranquila"
    )

    # 2. Ejecutar
    response = await service.process_message(
        "canal_1", "server_1", "user_1", "¿qué tal?"
    )

    # 3. Verificar resultados
    assert response == "todo bien por acá, tranquila"

    # Verificar llamadas al repositorio
    assert mock_repo.save_message.call_count == 2
    mock_repo.save_message.assert_any_call("canal_1", "user_1", "user", "¿qué tal?")
    mock_repo.save_message.assert_any_call(
        "canal_1", "helith", "assistant", "todo bien por acá, tranquila"
    )

    # Verificar guardado en memorias (2 veces: user y assistant)
    assert mock_repo.save_memory.call_count == 2
    mock_repo.save_memory.assert_any_call(
        server_id="server_1",
        channel_id="canal_1",
        user_id="user_1",
        content="¿qué tal?",
        embedding=[0.0] * 768,
    )
    mock_repo.save_memory.assert_any_call(
        server_id="server_1",
        channel_id="canal_1",
        user_id="helith",
        content="todo bien por acá, tranquila",
        embedding=[0.0] * 768,
    )

    # Verificar que el LLM fue llamado con el historial
    mock_llm_pool.generate_response.assert_called_once()
    args, kwargs = mock_llm_pool.generate_response.call_args
    assert "prompt" in kwargs
    assert "system_prompt" in kwargs
    assert "Tú (Helith): hola, qué hay" in kwargs["prompt"]


@pytest.mark.asyncio
@patch("domains.conversation.service.generate_embedding")
@patch("domains.conversation.service.intent_router")
@patch("domains.conversation.service.conversation_repo")
@patch("domains.conversation.service.llm_pool")
async def test_process_message_fallback_error(
    mock_llm_pool, mock_repo, mock_router, mock_embed, service
):
    """Prueba que el bot responda con el mensaje de emergencia si las APIs fallan."""
    mock_embed.return_value = [0.0] * 768
    mock_router.needs_web_search.return_value = False
    mock_repo.search_memories.return_value = []

    # Simular que el LLM tira una excepción (API caída, sin saldo, etc.)
    mock_llm_pool.generate_response = AsyncMock(
        side_effect=Exception("Todas las APIs fallaron")
    )

    # 2. Ejecutar
    response = await service.process_message("canal_1", "server_1", "user_1", "mensaje")

    # 3. Verificar que responde la frase por defecto y no rompe el programa
    assert response == "Me cuesta procesar eso ahora mismo. Inténtalo de nuevo."
