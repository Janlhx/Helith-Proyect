import logging

import discord

from domains.bot.search_intent import build_search_query, needs_web_search

logger = logging.getLogger("helith.router")


class IntentRouter:
    """Clasifica los mensajes entrantes para decidir qué dominio debe manejarlos."""

    def classify_intent(self, message: discord.Message) -> str:
        """Clasifica el contenido del mensaje en una intención."""
        # En la Fase 6, los dominios osu y monitoreo se movieron a Slash Commands.
        # Solo sobrevive la conversación natural.
        return "conversation"

    def needs_web_search(self, content: str) -> bool:
        """Determina si una consulta requiere búsqueda web (señales generalizadas)."""
        return needs_web_search(content)

    def build_search_query(self, content: str) -> str:
        """Normaliza el mensaje del usuario para enviarlo a Tavily."""
        return build_search_query(content)


intent_router = IntentRouter()
