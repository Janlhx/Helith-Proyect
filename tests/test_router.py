from unittest.mock import Mock

from domains.bot.router import intent_router


def test_classify_intent_admin():
    """Prueba que los mensajes con prefijo vayan a admin."""
    mock_message = Mock()
    mock_message.content = "h.setup"
    intent = intent_router.classify_intent(mock_message)
    assert intent == "admin"


def test_classify_intent_osu():
    """Prueba que palabras clave de osu! deriven a ese dominio."""
    mock_message = Mock()
    mock_message.content = "¿cuánto tiempo para llegar a rank 1 en osu?"
    intent = intent_router.classify_intent(mock_message)
    assert intent == "osu"


def test_classify_intent_monitoring():
    """Prueba que palabras clave de métricas deriven a monitoreo."""
    mock_message = Mock()
    mock_message.content = "¿cuántos tokens he consumido?"
    intent = intent_router.classify_intent(mock_message)
    assert intent == "monitoring"


def test_classify_intent_conversation():
    """Prueba que mensajes genéricos vayan a conversación."""
    mock_message = Mock()
    mock_message.content = "hola helith, ¿cómo estás?"
    intent = intent_router.classify_intent(mock_message)
    assert intent == "conversation"
