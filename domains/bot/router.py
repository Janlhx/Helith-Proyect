import logging

import discord

from core.config import settings

logger = logging.getLogger("helith.router")


class IntentRouter:
    """Clasifica los mensajes entrantes para decidir qué dominio debe manejarlos.

    Según HELITH_DOCS, no usamos un LLM para esto para ahorrar tokens.
    En esta fase inicial usamos reglas deterministas.
    """

    def classify_intent(self, message: discord.Message) -> str:
        """Clasifica el contenido del mensaje en una intención."""
        content = message.content.strip().lower()

        # 1. Comandos administrativos (Empiezan con el prefijo, ej: h.setup)
        if content.startswith(settings.PREFIX):
            return "admin"

        # 2. Intención: Predicción de osu!
        # Buscamos palabras clave para derivar al dominio de osu
        if "osu" in content and (
            "predict" in content
            or "rank" in content
            or "tiempo" in content
            or "llegar" in content
        ):
            logger.info(f"Intención detectada: osu! para el mensaje: '{content}'")
            return "osu"

        # 3. Intención: Monitoreo/Métricas
        if (
            "métricas" in content
            or "tokens" in content
            or "consumo" in content
        ):
            logger.info(
                f"Intención detectada: monitoreo para el mensaje: '{content}'"
            )
            return "monitoring"

        # 4. Por defecto: Conversación
        # Si el bot fue mencionado o es un mensaje directo, asumimos conversación
        return "conversation"


intent_router = IntentRouter()
