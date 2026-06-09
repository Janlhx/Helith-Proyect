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
    """Test the happy path of conversation with memories."""
    # 1. Configure mocks
    mock_repo.get_history.return_value = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola, qué hay"},
        {"role": "user", "content": "¿qué tal?"},
    ]
    mock_repo.search_memories.return_value = []
    mock_embed.return_value = [0.0] * 768
    mock_router.needs_web_search.return_value = False

    # Mock AI response
    mock_llm_pool.generate_response = AsyncMock(
        return_value="all good here, relax"
    )

    # 2. Run
    response = await service.process_message(
        "canal_1", "server_1", "user_1", "¿qué tal?"
    )

    # 3. Verify results
    assert response == "all good here, relax"

    # Verify repository calls
    assert mock_repo.save_message.call_count == 2
    mock_repo.save_message.assert_any_call("canal_1", "user_1", "user", "¿qué tal?")
    mock_repo.save_message.assert_any_call(
        "canal_1", "helith", "assistant", "all good here, relax"
    )

    # Verify memory saving (2 times: user and assistant)
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
        content="all good here, relax",
        embedding=[0.0] * 768,
    )

    # Verify the LLM was called with the history
    mock_llm_pool.generate_response.assert_called_once()
    args, kwargs = mock_llm_pool.generate_response.call_args
    assert "prompt" in kwargs
    assert "system_prompt" in kwargs
    assert "You (Helith): hola, qué hay" in kwargs["prompt"]


@pytest.mark.asyncio
@patch("domains.conversation.service.generate_embedding")
@patch("domains.conversation.service.intent_router")
@patch("domains.conversation.service.conversation_repo")
@patch("domains.conversation.service.llm_pool")
async def test_process_message_fallback_error(
    mock_llm_pool, mock_repo, mock_router, mock_embed, service
):
    """Test that the bot responds with the fallback message if APIs fail."""
    mock_embed.return_value = [0.0] * 768
    mock_router.needs_web_search.return_value = False
    mock_repo.search_memories.return_value = []

    # Simulating LLM throwing an exception
    mock_llm_pool.generate_response = AsyncMock(
        side_effect=Exception("Todas las APIs fallaron")
    )

    # 2. Run
    response = await service.process_message("canal_1", "server_1", "user_1", "message")

    # 3. Verify it responds with the default fallback and doesn't crash
    assert response == "I'm having trouble processing that right now. Please try again."
