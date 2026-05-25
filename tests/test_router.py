from unittest.mock import AsyncMock, Mock, patch

import pytest

from domains.admin.router import admin_router
from domains.bot.router import intent_router
from domains.monitoring.router import monitoring_router
from domains.osu.router import osu_router


def test_classify_intent_conversation():
    """Prueba que los mensajes por defecto vayan a conversación (Fase 6)."""
    mock_message = Mock()
    mock_message.content = "hola helith, ¿cómo estás?"
    intent = intent_router.classify_intent(mock_message)
    assert intent == "conversation"


@pytest.mark.asyncio
@patch("domains.admin.router.admin_service")
async def test_admin_slash_help(mock_admin_service):
    """Prueba que el slash command de ayuda envíe el panel interactivo."""
    mock_interaction = AsyncMock()
    await admin_router.handle_slash_help(mock_interaction)
    mock_interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
@patch("domains.monitoring.router.monitoring_service")
async def test_monitoring_text_metrics(mock_monitoring_service):
    """Prueba que el comando de texto h.metrics responda enviando un embed."""
    mock_monitoring_service.get_full_report.return_value = {
        "server_usage_analysis": {"server1": {"status": "NORMAL"}}
    }
    mock_message = AsyncMock()
    await monitoring_router.handle_text_metrics(mock_message, "server1")

    mock_message.reply.assert_called_once()
    args, kwargs = mock_message.reply.call_args
    assert "embed" in kwargs or len(args) > 0


@pytest.mark.asyncio
@patch("domains.osu.router.osu_service")
async def test_osu_slash_predict(mock_osu_service):
    """Prueba que el slash command de osu responda usando defer()."""
    mock_osu_service.process_slash_predict = AsyncMock(
        return_value="Predicción simulada."
    )
    mock_interaction = AsyncMock()

    await osu_router.handle_slash_predict(
        mock_interaction, "test_user", 5000, "server1", "user1"
    )

    # Debe avisar a Discord con un defer() para evitar timeouts
    mock_interaction.response.defer.assert_called_once()
    # Luego debe enviar la respuesta en el followup
    mock_interaction.followup.send.assert_called_once_with("Predicción simulada.")
