import logging

from domains.osu.service import osu_service

logger = logging.getLogger("helith.osu.router")


class OsuRouter:
    """Enruta las consultas del dominio de osu!."""

    async def handle_message(
        self, channel_id: str, user_id: str, content: str
    ) -> str:
        """Enruta y maneja la consulta asíncrona del usuario."""
        try:
            logger.info(
                f"OsuRouter procesando mensaje para canal={channel_id}, "
                f"usuario={user_id}"
            )
            response = await osu_service.process_query(
                channel_id, user_id, content
            )
            return response
        except Exception as e:
            logger.error(f"Error en OsuRouter: {e}")
            return (
                "Lo siento, ha ocurrido un error al procesar tu estimación de "
                "rango en osu!."
            )


osu_router = OsuRouter()

