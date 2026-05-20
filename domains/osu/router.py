import logging

import discord

from domains.osu.service import osu_service

logger = logging.getLogger("helith.osu.router")


class OsuRouter:
    """Enruta las consultas del dominio de osu! vía Slash Commands."""

    async def handle_slash_predict(
        self,
        interaction: discord.Interaction,
        username: str,
        target_rank: int,
        server_id: str,
        user_id: str,
    ):
        """Enruta y maneja la consulta predictiva de osu!."""
        try:
            logger.info(
                f"OsuRouter procesando /predict para username={username}, "
                f"target={target_rank}"
            )

            # Avisamos a Discord que estamos procesando la respuesta
            await interaction.response.defer()

            response = await osu_service.process_slash_predict(
                username, target_rank, server_id, user_id
            )

            await interaction.followup.send(response)

        except Exception as e:
            logger.error(f"Error en OsuRouter: {e}")
            error_msg = (
                "Lo siento, ha ocurrido un error al procesar tu estimación "
                "de rango en osu!."
            )
            if interaction.response.is_done():
                await interaction.followup.send(error_msg)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)


osu_router = OsuRouter()
