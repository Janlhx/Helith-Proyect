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


@bot.event
async def on_message(message):
    # Ignorar mensajes del propio bot
    if message.author == bot.user:
        return

    # Ignorar mensajes de otros bots
    if message.author.bot:
        return

    # Importaciones diferidas para evitar ciclos
    from domains.bot.router import intent_router
    from domains.conversation.service import conversation_service

    # Clasificar intención
    intent = intent_router.classify_intent(message)

    if intent == "conversation":
        # Respondemos si nos mencionan o es mensaje directo
        if bot.user.mentioned_in(message) or isinstance(
            message.channel, discord.DMChannel
        ):
            # Limpiar la mención del texto
            content = message.content.replace(f"<@{bot.user.id}>", "").strip()
            if not content:
                content = "hola"  # Si solo nos mencionaron, saludamos

            async with message.channel.typing():
                response = await conversation_service.process_message(
                    str(message.channel.id), str(message.author.id), content
                )
                await message.reply(response)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Flask en un thread separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Keep-alive server iniciado")

    # Bot en el thread principal
    bot.run(settings.DISCORD_TOKEN)