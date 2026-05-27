import logging
import os
import re
import threading

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from core.config import settings

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helith")

# ── Flask keep-alive (para Render + UptimeRobot) ──────────────────────────────
app = Flask(__name__)
app.secret_key = settings.DASHBOARD_PASSWORD or "helith_fallback_secret"


@app.route("/health")
def health():
    tavily_key = getattr(settings, "TAVILY_API_KEY", "")
    tavily_status = (
        "configured"
        if (tavily_key and tavily_key != "your_tavily_key")
        else "missing"
    )
    tavily_preview = tavily_key[:8] + "..." if tavily_key else "None"

    return jsonify(
        {
            "status": "ok",
            "bot": bot.is_ready() if bot else False,
            "version": settings.VERSION,
            "tavily": {
                "status": tavily_status,
                "preview": tavily_preview,
            },
        }
    )


@app.route("/")
def index():
    return jsonify({"name": "Helith", "status": "running"})


@app.route("/login", methods=["GET", "POST"])
def login():
    import secrets
    if request.method == "POST":
        password = request.form.get("password", "")
        if (
            password
            and settings.DASHBOARD_PASSWORD
            and secrets.compare_digest(password, settings.DASHBOARD_PASSWORD)
        ):
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Contraseña incorrecta")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/api/metrics")
def api_metrics():
    import secrets
    # Permite acceso vía sesión (navegador) o Authorization header (scripts)
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {settings.DISCORD_TOKEN[:20]}"
    if not session.get("authenticated") and not secrets.compare_digest(
        auth_header, expected
    ):
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
    # ── Generar Boot Report (RF-15) ──────────────────────────────────────────
    db_status = "🟢 Supabase" if settings.SUPABASE_KEY else "⚠️ SQLite (Fallback)"
    tavily_status = "🟢 Active" if settings.TAVILY_API_KEY else "⚪ Inactive"
    
    # Modelos LLM
    llms_active = []
    if settings.GEMINI_API_KEY:
        llms_active.append("Gemini")
    if settings.NVIDIA_API_KEY:
        llms_active.append("NVIDIA NIM")
    if settings.GROQ_API_KEY:
        llms_active.append("Groq")
    llms_str = ", ".join(llms_active) if llms_active else "None (CRITICAL)"

    # osu! API
    osu_status = "🟢 Active" if settings.OSU_CLIENT_ID else "⚪ Mock Mode"

    report = (
        f"\n{'='*50}\n"
        f"🤖 HELITH ONLINE — v{settings.VERSION}\n"
        f"👤 {bot.user} (ID: {bot.user.id})\n"
        f"🌍 Environment: {settings.ENVIRONMENT.upper()}\n"
        f"{'-'*50}\n"
        f"🗄️ Database: {db_status}\n"
        f"🧠 Active LLMs: {llms_str}\n"
        f"🔍 Web Search: {tavily_status}\n"
        f"🎮 osu! Integration: {osu_status}\n"
        f"🌐 Web Dashboard: 🟢 Port 8080\n"
        f"{'='*50}"
    )
    logger.info(report)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="out the window | v" + settings.VERSION,
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
            cmd_type = parts[1].lower() if len(parts) > 1 else ""

            if cmd_type == "global":
                synced = await bot.tree.sync()
                await message.reply(
                    f"Synced {len(synced)} slash commands globally."
                )
            elif cmd_type == "clear":
                if message.guild:
                    bot.tree.clear_commands(guild=message.guild)
                    await bot.tree.sync(guild=message.guild)
                    await message.reply(
                        f"Cleared and desynced all local commands for "
                        f"this server ({message.guild.name}). "
                        f"Only global commands will be shown now "
                        f"(may take up to 2 hours to appear)."
                    )
                else:
                    await message.reply(
                        "This command must be used inside a server "
                        "to clear local commands."
                    )
            else:
                if message.guild:
                    bot.tree.copy_global_to(guild=message.guild)
                    synced = await bot.tree.sync(guild=message.guild)
                    await message.reply(
                        f"Instantly synced {len(synced)} slash commands "
                        f"for this server ({message.guild.name})."
                    )
                else:
                    await message.reply(
                        "This command must be used inside a server "
                        "to sync locally, or use `h.sync global`."
                    )
        except Exception as e:
            await message.reply(f"Error syncing commands: {e}")
        return

    # Comando oculto para diagnosticar Tavily
    if content.startswith("h.tavily"):
        if not await bot.is_owner(message.author):
            return
        
        query = content[len("h.tavily"):].strip()
        if not query:
            await message.reply("Write something to search. Ex: `h.tavily weather london`")
            return
            
        await message.reply(f"🔍 Searching directly on Tavily: `{query}`...")
        from core.tools.search import tavily_search
        try:
            res = await tavily_search.search(query)
            if not res:
                await message.reply(
                    "❌ Tavily returned an empty result.\n"
                    "Possible causes: Invalid API Key, rate limit "
                    "exceeded, or 500 error."
                )
            else:
                await message.reply(f"✅ Successful result:\n{res}")
        except Exception as e:
            await message.reply(f"⚠️ Exception: {e}")
        return

    # Comando oculto para métricas
    if content.startswith("h.metrics"):
        if not await bot.is_owner(message.author):
            return
            
        from domains.monitoring.router import monitoring_router
        server_id_str = str(message.guild.id) if message.guild else "DM"
        await monitoring_router.handle_text_metrics(message, server_id_str)
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
            f"Hey, chill a bit. You're talking too fast. "
            f"Try again in {retry_user:.1f} seconds."
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
                f"This server is too noisy. I'm getting saturated. "
                f"Try again in {retry_guild:.1f} seconds."
            )
            return

    # Limpiar la mención del texto de manera robusta
    content = re.sub(rf"<@!?{bot.user.id}>", "", message.content).strip()
    if not content:
        content = "hello"  # Si solo nos mencionaron, saludamos

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
    logger.info("Keep-alive server started")

    # Bot en el thread principal
    bot.run(settings.DISCORD_TOKEN)
