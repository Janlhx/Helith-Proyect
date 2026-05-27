from domains.admin.service import admin_service


def test_admin_help_embed_home():
    """Prueba que el embed principal sea correcto en inglés."""
    embed = admin_service.get_help_embed("home")
    assert "USER MANUAL" in embed.title
    assert "diagnostics" in embed.description
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "🏠 Home"


def test_admin_help_embed_osu():
    """Prueba el embed de la sección de predicciones de osu!"""
    embed = admin_service.get_help_embed("osu")
    assert "osu! Predictions" in embed.title
    assert "/predict" in embed.fields[1].value


def test_admin_help_embed_monitoring():
    """Prueba el embed de la sección de monitoreo de red."""
    embed = admin_service.get_help_embed("monitoring")
    assert "Monitoring & Telemetry" in embed.title
    assert "administrator" in embed.fields[0].value


def test_admin_help_embed_chat():
    """Prueba el embed de la sección conversacional."""
    embed = admin_service.get_help_embed("chat")
    assert "Smart Conversation" in embed.title
    assert "@Helith" in embed.fields[0].value
