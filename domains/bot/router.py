import logging

import discord

logger = logging.getLogger("helith.router")


class IntentRouter:
    """Clasifica los mensajes entrantes para decidir qué dominio debe manejarlos."""

    def classify_intent(self, message: discord.Message) -> str:
        """Clasifica el contenido del mensaje en una intención."""
        # En la Fase 6, los dominios osu y monitoreo se movieron a Slash Commands.
        # Solo sobrevive la conversación natural.
        return "conversation"

    def needs_web_search(self, content: str) -> bool:
        """Determina de forma heurística si una consulta requiere búsqueda web."""
        text = content.lower().strip()

        # Prefijos de búsqueda explícitos para forzar trigger
        explicit_triggers = ["busca ", "buscar ", "search ", "google "]
        if any(text.startswith(trigger) for trigger in explicit_triggers):
            return True

        # Palabras clave heurísticas en español e inglés
        keywords = [
            "noticias",
            "news",
            "clima",
            "weather",
            "precio",
            "dólar",
            "dolar",
            "euro",
            "bitcoin",
            "crypto",
            "partido",
            "futbol",
            "fútbol",
            "resultado",
            "ganador",
            "campeón",
            "campeon",
            "hoy",
            "today",
            "actual",
            "actualidad",
            "reciente",
            "recientes",
            "último",
            "ultimo",
            "este año",
            "this year",
            "quien gano",
            "quién ganó",
            "quien es el actual",
            "quién es el actual",
            "qué pasó con",
            "que paso con",
            "quien es hoy",
            "quién es hoy",
            "está pasando",
            "esta pasando",
        ]

        import re

        for keyword in keywords:
            # Búsqueda por palabra completa para evitar falsos positivos
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text):
                return True

        return False


intent_router = IntentRouter()
