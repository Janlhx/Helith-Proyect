import logging

import discord

from domains.admin.service import HelpMenuView, admin_service

logger = logging.getLogger("helith.admin.router")


class AdminRouter:
    """Enruta comandos administrativos mediante Slash Commands."""

    async def handle_slash_help(self, interaction: discord.Interaction):
        """Procesa el comando /help y retorna el menú interactivo."""
        try:
            logger.info("AdminRouter procesando slash command /help")
            embed = admin_service.get_help_embed("home")
            view = HelpMenuView()
            await interaction.response.send_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error en AdminRouter: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred loading the help panel.", ephemeral=True
                )


admin_router = AdminRouter()
