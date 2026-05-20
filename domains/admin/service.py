import discord

HELITH_COLOR = 0x00F0FF
DARK_COLOR = 0x1F232A


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Inicio",
                description="Guía de interacción básica",
                emoji="🏠",
                value="home",
            ),
            discord.SelectOption(
                label="Predicción osu!",
                description="Modelo de regresión matemática",
                emoji="🎯",
                value="osu",
            ),
            discord.SelectOption(
                label="Métricas y Monitoreo",
                description="Consumo y cuotas de servidor",
                emoji="📊",
                value="monitoring",
            ),
            discord.SelectOption(
                label="Conversación IA",
                description="Personalidad y límites de Helith",
                emoji="💬",
                value="chat",
            ),
        ]
        super().__init__(
            placeholder="Selecciona una sección...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_dropdown",
        )

    async def callback(self, interaction: discord.Interaction):
        from domains.admin.service import admin_service

        embed = admin_service.get_help_embed(self.values[0])
        await interaction.response.edit_message(embed=embed)


class HelpMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.add_item(HelpDropdown())


class AdminService:
    def get_help_embed(self, section: str = "home") -> discord.Embed:
        if section == "home":
            embed = discord.Embed(
                title="HELITH // MANUAL DE USUARIO v0.1.0",
                description=(
                    "Soy una inteligencia artificial analítica orientada a "
                    "modelado predictivo de progreso de juego y diagnóstico "
                    "de métricas de red.\n\n"
                    "**Estatus:** ACTIVO\n"
                    "**Prefijo Administrativo:** `h.`"
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="🏠 Inicio",
                value=(
                    "Bienvenido al panel interactivo. Utiliza el menú "
                    "desplegable a continuación para navegar por mis "
                    "módulos operativos."
                ),
                inline=False,
            )
            embed.set_footer(text="Helith Core System")
            return embed

        elif section == "osu":
            embed = discord.Embed(
                title="🎯 Predicciones de osu! (ML)",
                description=(
                    "Mi motor predictivo utiliza una regresión lineal OLS "
                    "adaptativa para estimar cuánto tiempo le tomará a un "
                    "jugador alcanzar un rango global específico."
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="Mecanismo (Improvement Indicator)",
                value=(
                    "Calculo un $ii$ comparando el tiempo de juego real "
                    "vs estadístico. Esto acelera o desacelera la "
                    "pendiente de predicción."
                ),
                inline=False,
            )
            embed.add_field(
                name="Uso (Lenguaje Natural)",
                value=(
                    'Envíame un mensaje que contenga la palabra "osu" y una '
                    "intención predictiva.\n\n**Ejemplo:**\n"
                    "`Helith, ¿cuánto tardará mrekk en llegar al rank 1 en osu?`"
                ),
                inline=False,
            )
            return embed

        elif section == "monitoring":
            embed = discord.Embed(
                title="📊 Monitoreo y Métricas",
                description=(
                    "Llevo un registro constante del uso de red, impactos "
                    "al Rate Limit (Cooldowns) y consumo de tokens de "
                    "los modelos LLM."
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="Comandos Integrados",
                value=(
                    "No requieres acceder al dashboard web. Puedes "
                    "preguntarme en el chat:\n\n"
                    "`Helith, ¿cuáles son las métricas del servidor?`\n"
                    "`h.help métricas`"
                ),
                inline=False,
            )
            embed.add_field(
                name="Estados",
                value=(
                    "🟢 NORMAL\n"
                    "🟡 ADVERTENCIA (Cooldown sugerido: 120s)\n"
                    "🔴 CRÍTICO (Cooldown sugerido: 180s)"
                ),
                inline=False,
            )
            return embed

        elif section == "chat":
            embed = discord.Embed(
                title="💬 Conversación Inteligente",
                description=(
                    "Mi personalidad es estricta, seca y matemática. No "
                    "utilizo emojis alegremente ni relleno innecesario."
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="¿Cómo interactuar?",
                value=(
                    "Mencióname (`@Helith`) o envíame un Mensaje Directo.\n\n"
                    "**Ejemplo:**\n"
                    "`@Helith dime tu opinión sobre la ineficiencia humana.`"
                ),
                inline=False,
            )
            embed.add_field(
                name="Límites",
                value=(
                    "Tengo un límite estricto de **5 mensajes por minuto** "
                    "por usuario, y **20 mensajes por minuto** por servidor."
                ),
                inline=False,
            )
            return embed

        return self.get_help_embed("home")

    def get_specific_help(self, command: str) -> discord.Embed:
        cmd = command.lower().strip()
        if cmd in ["osu", "predict", "rango", "prediccion"]:
            return self.get_help_embed("osu")
        elif cmd in ["metricas", "monitoring", "tokens", "status", "consumo"]:
            return self.get_help_embed("monitoring")
        elif cmd in ["chat", "hablar", "conversacion", "ia"]:
            return self.get_help_embed("chat")

        embed = discord.Embed(
            title="⚠️ Comando Desconocido",
            description=f"No se encontró información para: `{command}`.",
            color=0xFF0000,
        )
        return embed


admin_service = AdminService()
