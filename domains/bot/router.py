import logging

import discord

from domains.bot.search_intent import build_search_query, needs_web_search

logger = logging.getLogger("helith.router")


class IntentRouter:
    """Classifies incoming messages to determine which domain should handle them."""

    def classify_intent(self, message: discord.Message) -> str:
        """Classify the message content into an intent."""
        # In Phase 6, the osu and monitoring domains moved to Slash Commands.
        # Only natural conversation remains.
        return "conversation"

    def needs_web_search(self, content: str) -> bool:
        """Determina si una consulta requiere búsqueda web (señales generalizadas)."""
        return needs_web_search(content)

    def build_search_query(self, content: str) -> str:
        """Normalize the user message for sending to Tavily."""
        return build_search_query(content)


intent_router = IntentRouter()
