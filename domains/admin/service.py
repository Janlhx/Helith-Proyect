import discord

HELITH_COLOR = 0x00F0FF
DARK_COLOR = 0x1F232A


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Home",
                description="Basic interaction guide",
                emoji="🏠",
                value="home",
            ),
            discord.SelectOption(
                label="osu! Prediction",
                description="Mathematical regression model",
                emoji="🎯",
                value="osu",
            ),
            discord.SelectOption(
                label="Metrics & Monitoring",
                description="Server consumption and quotas",
                emoji="📊",
                value="monitoring",
            ),
            discord.SelectOption(
                label="AI Conversation",
                description="Helith's identity and limits",
                emoji="💬",
                value="chat",
            ),
        ]
        super().__init__(
            placeholder="Select a module...",
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
                title="HELITH // USER MANUAL v1.0.0",
                description=(
                    "I am an analytical artificial intelligence designed for "
                    "game progress predictive modeling and network metrics "
                    "diagnostics."
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="🏠 Home",
                value=(
                    "Welcome to the interactive panel. Use the dropdown menu "
                    "below to navigate through my operational modules."
                ),
                inline=False,
            )
            embed.set_footer(text="Helith Core System")
            return embed

        elif section == "osu":
            embed = discord.Embed(
                title="🎯 osu! Predictions (ML)",
                description=(
                    "My predictive engine uses an adaptive OLS linear regression "
                    "to estimate how much time it will take a player to reach a "
                    "specific global rank."
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="Mechanism (Improvement Indicator)",
                value=(
                    "I calculate an $ii$ by comparing actual vs expected play time. "
                    "This accelerates or dampens the prediction slope."
                ),
                inline=False,
            )
            embed.add_field(
                name="Usage (Slash Command)",
                value=(
                    "Use the native discord command:\n"
                    "`/predict username:mrekk target_rank:1`"
                ),
                inline=False,
            )
            return embed

        elif section == "monitoring":
            embed = discord.Embed(
                title="📊 Monitoring & Telemetry",
                description=(
                    "I keep a constant log of network usage, rate limits, "
                    "and multi-LLM token consumption across all providers."
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="Web Dashboard",
                value=(
                    "I expose a private web dashboard for administrators "
                    "to monitor real-time consumption and quota exhaustion."
                ),
                inline=False,
            )
            embed.add_field(
                name="Commands",
                value=(
                    "Hidden command `h.metrics` provides a quick summary "
                    "directly in chat (Admin only)."
                ),
                inline=False,
            )
            return embed

        elif section == "chat":
            embed = discord.Embed(
                title="💬 Smart Conversation",
                description=(
                    "I am capable of holding natural conversations, adapting "
                    "to the language you speak to me, and searching the web in real-time."
                ),
                color=HELITH_COLOR,
            )
            embed.add_field(
                name="How to interact?",
                value=(
                    "Mention me (`@Helith`) or send me a Direct Message.\n\n"
                    "**Example:**\n"
                    "`@Helith what's your opinion on human inefficiency?`"
                ),
                inline=False,
            )
            embed.add_field(
                name="Capabilities",
                value=(
                    "• **Multi-LLM Fallback:** I stay online even if a provider fails.\n"
                    "• **Real-Time Search:** I can look up current news and facts.\n"
                    "• **Semantic Memory:** I remember important context."
                ),
                inline=False,
            )
            return embed

        return self.get_help_embed("home")


admin_service = AdminService()
