from unittest.mock import AsyncMock, patch

import pytest

from domains.conversation.service import ConversationService


@pytest.fixture
def service():
    return ConversationService()


@pytest.mark.asyncio
@patch("domains.conversation.service.conversation_repo")
@patch("domains.conversation.service.llm_pool")
async def test_process_message_success(mock_llm_pool, mock_repo, service):
    """Prueba el flujo feliz de la conversación (historial + LLM + guardado)."""
    # 1. Configurar mocks
    mock_repo.get_history.return_value = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola, qué hay"},
        {"role": "user", "content": "¿qué tal?"},
    ]
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

    # Verificar llamadas al repositorio (debería guardar el input y el output)
    assert mock_repo.save_message.call_count == 2
    mock_repo.save_message.assert_any_call(
        "canal_1", "user_1", "user", "¿qué tal?"
    )
    mock_repo.save_message.assert_any_call(
        "canal_1", "helith", "assistant", "todo bien por acá, tranquila"
    )

    # Verificar que el LLM fue llamado con el historial
    mock_llm_pool.generate_response.assert_called_once()
    args, kwargs = mock_llm_pool.generate_response.call_args
    assert "prompt" in kwargs
    assert "system_prompt" in kwargs
    # El prompt debería contener partes del historial simulado
    assert "Tú (Helith): hola, qué hay" in kwargs["prompt"]


@pytest.mark.asyncio
@patch("domains.conversation.service.conversation_repo")
@patch("domains.conversation.service.llm_pool")
async def test_process_message_fallback_error(mock_llm_pool, mock_repo, service):
    """Prueba que el bot responda con el mensaje de emergencia si las APIs fallan."""
    # 1. Simular que el LLM tira una excepción (API caída, sin saldo, etc.)
    mock_llm_pool.generate_response = AsyncMock(
        side_effect=Exception("Todas las APIs fallaron")
    )

    # 2. Ejecutar
    response = await service.process_message(
        "canal_1", "server_1", "user_1", "mensaje"
    )

    # 3. Verificar que responde la frase por defecto y no rompe el programa
    assert response == "Me cuesta procesar eso ahora mismo. Inténtalo de nuevo."
