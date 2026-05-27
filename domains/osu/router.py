import logging

import discord

from domains.osu.service import osu_service

logger = logging.getLogger("helith.osu.router")


class OsuRouter:
    """Route osu! domain queries via Slash Commands."""

    async def handle_slash_predict(
        self,
        interaction: discord.Interaction,
        username: str,
        target_rank: int,
        server_id: str,
        user_id: str,
    ):
        """Route and handle the osu! predictive query."""
        try:
            logger.info(
                f"OsuRouter processing /predict for username={username}, "
                f"target={target_rank}"
            )

            # Notify Discord that we are processing the response
            await interaction.response.defer()

            response = await osu_service.process_slash_predict(
                username, target_rank, server_id, user_id
            )

            await interaction.followup.send(response)

        except Exception as e:
            logger.error(f"Error in OsuRouter: {e}")
            error_msg = (
                "Sorry, an error occurred while processing your osu! "
                "rank estimation."
            )
            if interaction.response.is_done():
                await interaction.followup.send(error_msg)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)


osu_router = OsuRouter()
