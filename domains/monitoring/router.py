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
        """Extrae el reporte del servidor y genera un Embed rico en Discord
        para el comando oculto h.metrics.
        """
        try:
            logger.info(
                f"MonitoringRouter procesando métricas texto para servidor {server_id}"
            )
            report = monitoring_service.get_full_report()
            server_usage = report.get("server_usage_analysis", {}).get(server_id)

            if not server_usage:
                await message.reply(
                    "Aún no hay métricas registradas para este servidor."
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
                title=f"📊 Análisis de Red | Servidor: `{server_id}`",
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="Estado de Salud",
                value=f"{status_emoji} **{status}**",
                inline=False,
            )
            embed.add_field(
                name="Tráfico (7 Días)",
                value=(
                    f"Mensajes: `{server_usage.get('messages_sent', 0)}`\n"
                    f"Tokens: `{server_usage.get('total_tokens', 0):,}`\n"
                    f"Promedio/Día: `{server_usage.get('avg_tokens_per_day', 0):,}`"
                ),
                inline=False,
            )
            embed.add_field(
                name="Protección Rate Limit",
                value=(
                    f"Impactos Bloqueados: `{server_usage.get('rate_limit_hits', 0)}`"
                ),
                inline=False,
            )
            embed.add_field(
                name="Recomendación Dinámica",
                value=f"*{server_usage.get('recommended_cooldown', '')}*",
                inline=False,
            )
            embed.set_footer(
                text="Vista rápida. Consulta el dashboard web para gráficos detallados."
            )

            await message.reply(embed=embed)

        except Exception as e:
            logger.error(f"Error en MonitoringRouter: {e}")
            await message.reply(
                "No pude extraer las métricas de red en este momento."
            )


monitoring_router = MonitoringRouter()
