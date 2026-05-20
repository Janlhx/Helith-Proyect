import logging
import os
import threading

import discord
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
    return jsonify({
        "status": "ok",
        "bot": bot.is_ready() if bot else False,
        "version": settings.VERSION,
    })


@app.route("/")
def index():
    return jsonify({"name": "Helith", "status": "running"})


@app.route("/dashboard")
def dashboard():
    from flask import request

    # Protección básica: solo el admin con el token correcto puede ver el dashboard
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {settings.DISCORD_TOKEN[:20]}"
    if auth != expected:
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
            str(message.guild.id) if message.guild else "DM",
            str(message.author.id)
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
                str(message.guild.id),
                str(message.author.id)
            )
            await message.reply(
                f"Este servidor está muy ruidoso. Me están saturando. "
                f"Inténtalo de nuevo en {retry_guild:.1f} segundos."
            )
            return

    # Limpiar la mención del texto
    content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not content:
        content = "hola"  # Si solo nos mencionaron, saludamos

    # Derivar según la intención clasificada
    response = None
    server_id_str = str(message.guild.id) if message.guild else "DM"

    async with message.channel.typing():
        if intent == "osu":
            from domains.osu.router import osu_router
            response = await osu_router.handle_message(
                str(message.channel.id), str(message.author.id), content
            )
        elif intent == "monitoring":
            from domains.monitoring.router import monitoring_router
            response = await monitoring_router.handle_message(
                server_id_str, str(message.author.id), content
            )
        elif intent == "admin":
            from domains.admin.router import admin_router
            response = await admin_router.handle_message(message, content)
        else:
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