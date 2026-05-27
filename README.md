# Helith 🤖

> Discord Bot · Multi-LLM · ML Engineering

Helith is a Discord bot designed with a robust architecture focused on stability and Machine Learning. As the spiritual successor to Dalet, Helith is built from the ground up to provide predictive analytics, multi-model LLM integration, and flawless resource management.

## Key Features ✨

*   **Multi-LLM with Smart Fallback:** Uses Google Gemini as the primary conversational model, with automatic fallbacks to NVIDIA NIM (DeepSeek/Llama/Gemma) and Groq. If one provider goes down, Helith stays online.
*   **Token Monitoring & Prediction:** Real-time telemetry on token and model consumption. Predicts when free API quotas will be exhausted, featuring a private web dashboard.
*   **osu! Integration (Predictive ML):** Through the `/predict` command, Helith uses Machine Learning models trained on real data to estimate when a player will reach a specific global rank.
*   **Semantic Memory:** Uses `pgvector` in Supabase to search for relevant memories in conversations and pass them as context, drastically reducing unnecessary token usage.
*   **Real-Time Web Search:** Native integration with Tavily to answer questions about recent news, weather, or current events.
*   **Total Resilience:** Built on PostgreSQL (Supabase) with an automatic fallback to local SQLite if the external database connection drops.

## Commands 🎮

### Interaction
Helith responds naturally when mentioned (e.g., `@Helith how are you?`).
She also has specific utility commands:

*   `/help` — Displays the interactive help panel.
*   `/predict [username] [target_rank]` — Predicts how many days it will take a player to reach the given osu! rank.

### Administration (Text Commands)
The following commands can only be executed by the bot owner:

*   `h.metrics` — (Hidden) Generates a quick metrics report in Discord.
*   `h.tavily [query]` — (Hidden) Performs a direct test search using Tavily.
*   `h.sync [global|clear]` — Manages Discord's command tree synchronization (useful for solving duplicated slash commands).

## Telemetry Dashboard 📊

Helith exposes a port (8080 by default) for a private web dashboard. Here you can access detailed usage metrics, rate limits per server, active models, and quota exhaustion predictions. The dashboard is protected by the `DASHBOARD_PASSWORD` environment variable.

## Tech Stack 🛠️

*   **Python 3.11+**
*   [discord.py](https://discordpy.readthedocs.io/)
*   [Supabase](https://supabase.com/) (PostgreSQL + pgvector)
*   Scikit-Learn & XGBoost
*   Flask & Chart.js (Dashboard)

## Deployment 🚀

Helith is designed for easy deployment on **Render**.
It uses `uv` for lightning-fast dependency management. To run it locally:

```bash
# 1. Clone the repo and navigate to it
git clone https://github.com/your-username/Helith-Proyect.git
cd Helith-Proyect

# 2. Copy the environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Start the bot
uv run main.py
```

---
*Developed with ❤️ for the osu! community*
