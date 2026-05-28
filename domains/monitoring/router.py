import logging

import discord

from domains.monitoring.service import monitoring_service

logger = logging.getLogger("helith.monitoring.router")
HELITH_COLOR = 0x00F0FF


class MonitoringRouter:
    """Enruta interacciones de monitoreo (métricas) vía Slash Commands."""

    async def handle_text_metrics(
        self, message: discord.Message, server_id: str
    ):
        """Extract the server report and generate a rich Discord Embed
        for the hidden h.metrics command.
        """
        try:
            logger.info(
                f"MonitoringRouter processing text metrics for server {server_id}"
            )
            report = monitoring_service.get_full_report()
            server_usage = report.get("server_usage_analysis", {}).get(server_id)

            if not server_usage:
                await message.reply(
                    "No metrics registered for this server yet."
                )
                return

            status = server_usage.get("status", "NORMAL")
            if status == "NORMAL":
                status_emoji = "🟢"
            elif status == "ADVERTENCIA":
                status_emoji = "🟡"
            else:
                status_emoji = "🔴"

            embed = discord.Embed(
                title=f"📊 Network Analysis | Server: `{server_id}`",
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="Health Status",
                value=f"{status_emoji} **{status}**",
                inline=False,
            )
            embed.add_field(
                name="Traffic (7 Days)",
                value=(
                    f"Messages: `{server_usage.get('messages_sent', 0)}`\n"
                    f"Tokens: `{server_usage.get('total_tokens', 0):,}`\n"
                    f"Avg/Day: `{server_usage.get('avg_tokens_per_day', 0):,}`"
                ),
                inline=False,
            )
            embed.add_field(
                name="Rate Limit Protection",
                value=(
                    f"Blocked Hits: `{server_usage.get('rate_limit_hits', 0)}`"
                ),
                inline=False,
            )
            embed.add_field(
                name="Dynamic Recommendation",
                value=f"*{server_usage.get('recommended_cooldown', '')}*",
                inline=False,
            )
            embed.set_footer(
                text="Quick view. Check the web dashboard for detailed charts."
            )

            await message.reply(embed=embed)

        except Exception as e:
            logger.error(f"Error en MonitoringRouter: {e}")
            await message.reply(
                "I couldn't extract network metrics at this time."
            )


monitoring_router = MonitoringRouter()
