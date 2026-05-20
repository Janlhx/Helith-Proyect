import logging
import os
import re
import threading

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, jsonify

from core.config import settings

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helith")

# ── Flask keep-alive (para Render + UptimeRobot) ──────────────────────────────
app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "bot": bot.is_ready() if bot else False,
            "version": settings.VERSION,
        }
    )


@app.route("/")
def index():
    return jsonify({"name": "Helith", "status": "running"})


@app.route("/dashboard")
def dashboard():
    import secrets

    from flask import request

    # Protección básica: solo el admin con el token correcto puede ver el dashboard
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {settings.DISCORD_TOKEN[:20]}"
    if not secrets.compare_digest(auth, expected):
        return jsonify({"error": "Unauthorized"}), 401

    from domains.monitoring.service import monitoring_service

    report = monitoring_service.get_full_report()
    return jsonify(report)


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


# ── Bot ───────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=settings.PREFIX,
    intents=intents,
    help_command=None,
)


# ── Slash Commands ────────────────────────────────────────────────────────────
@bot.tree.command(name="help", description="Displays the interactive help panel.")
async def slash_help(interaction: discord.Interaction):
    from domains.admin.router import admin_router

    await admin_router.handle_slash_help(interaction)


@bot.tree.command(name="metrics", description="Displays server consumption metrics.")
@app_commands.default_permissions(administrator=True)
async def slash_metrics(interaction: discord.Interaction):
    from domains.monitoring.router import monitoring_router

    server_id_str = str(interaction.guild_id) if interaction.guild_id else "DM"
    user_id_str = str(interaction.user.id)
    await monitoring_router.handle_slash_metrics(
        interaction, server_id_str, user_id_str
    )


@bot.tree.command(
    name="predict",
    description="Predicts when a player will reach a target rank in osu!.",
)
@app_commands.describe(
    username="The osu! username", target_rank="The global rank to reach (e.g. 5000)"
)
async def slash_predict(
    interaction: discord.Interaction, username: str, target_rank: int = 5000
):
    from domains.osu.router import osu_router

    server_id_str = str(interaction.guild_id) if interaction.guild_id else "DM"
    user_id_str = str(interaction.user.id)
    await osu_router.handle_slash_predict(
        interaction, username, target_rank, server_id_str, user_id_str
    )


@bot.event
async def on_ready():
    logger.info(f"Helith online — {bot.user} ({bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="por la ventana",
        )
    )


@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception(f"Error en evento {event}")


# Mapeo de cooldowns por usuario: 5 mensajes por minuto
user_cooldown = commands.CooldownMapping.from_cooldown(
    5, 60.0, commands.BucketType.user
)
# Mapeo de cooldowns por servidor: 20 mensajes por minuto
guild_cooldown = commands.CooldownMapping.from_cooldown(
    20, 60.0, commands.BucketType.guild
)


@bot.event
async def on_message(message):
    # Ignorar mensajes del propio bot
    if message.author == bot.user:
        return

    # Ignorar mensajes de otros bots
    if message.author.bot:
        return

    content = message.content.strip()

    # Comando oculto para sincronizar comandos slash
    if content.startswith("h.sync"):
        # Protección de seguridad: solo el dueño del bot puede sincronizar
        if not await bot.is_owner(message.author):
            await message.reply(
                "No tienes permisos suficientes para sincronizar el árbol de comandos."
            )
            return
        try:
            parts = content.split()
            is_global = len(parts) > 1 and parts[1].lower() == "global"

            if is_global:
                synced = await bot.tree.sync()
                await message.reply(
                    f"Sincronizados {len(synced)} comandos slash globalmente."
                )
            else:
                if message.guild:
                    bot.tree.copy_global_to(guild=message.guild)
                    synced = await bot.tree.sync(guild=message.guild)
                    await message.reply(
                        f"Sincronizados {len(synced)} comandos slash de "
                        f"manera instantánea para este servidor "
                        f"({message.guild.name})."
                    )
                else:
                    await message.reply(
                        "Este comando debe ser usado dentro de un servidor "
                        "para sincronizar localmente, o usa `h.sync global`."
                    )
        except Exception as e:
            await message.reply(f"Error sincronizando comandos: {e}")
        return

    from domains.bot.router import intent_router

    intent = intent_router.classify_intent(message)

    is_mentioned = bot.user.mentioned_in(message)
    is_dm = isinstance(message.channel, discord.DMChannel)

    # Si la intención es meramente conversacional, exigimos mención o DM
    if intent == "conversation" and not (is_mentioned or is_dm):
        return

    # 1. Aplicar cooldown por usuario
    bucket_user = user_cooldown.get_bucket(message)
    retry_user = bucket_user.update_rate_limit()
    if retry_user:
        from domains.monitoring.service import monitoring_service

        monitoring_service.record_rate_limit(
            str(message.guild.id) if message.guild else "DM", str(message.author.id)
        )
        await message.reply(
            f"Oye, relájate un poco. Estás hablando demasiado rápido. "
            f"Inténtalo de nuevo en {retry_user:.1f} segundos."
        )
        return

    # 2. Aplicar cooldown por servidor (solo si no es DM)
    if not is_dm:
        bucket_guild = guild_cooldown.get_bucket(message)
        retry_guild = bucket_guild.update_rate_limit()
        if retry_guild:
            from domains.monitoring.service import monitoring_service

            monitoring_service.record_rate_limit(
                str(message.guild.id), str(message.author.id)
            )
            await message.reply(
                f"Este servidor está muy ruidoso. Me están saturando. "
                f"Inténtalo de nuevo en {retry_guild:.1f} segundos."
            )
            return

    # Limpiar la mención del texto de manera robusta
    content = re.sub(rf"<@!?{bot.user.id}>", "", message.content).strip()
    if not content:
        content = "hola"  # Si solo nos mencionaron, saludamos

    # Derivar según la intención clasificada
    response = None
    server_id_str = str(message.guild.id) if message.guild else "DM"

    async with message.channel.typing():
        if intent == "conversation":
            # Por defecto: Conversación
            from domains.conversation.service import conversation_service

            response = await conversation_service.process_message(
                str(message.channel.id),
                server_id_str,
                str(message.author.id),
                content,
            )

    if response:
        if isinstance(response, dict):
            await message.reply(**response)
        else:
            await message.reply(response)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Flask en un thread separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Keep-alive server iniciado")

    # Bot en el thread principal
    bot.run(settings.DISCORD_TOKEN)
