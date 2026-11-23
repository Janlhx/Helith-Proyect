# Helith

> Discord Bot | Multi-LLM Routing | Predictive ML Engineering

**Status: On Hold / Archived.** Development was paused in favor of continuing and expanding [Dalet-Proyect](https://github.com/Janlhx/Dalet-Proyect). Kept public as a reference for its predictive ML pipeline, `pgvector` semantic memory, and multi-provider LLM fallback architecture.

Helith is a Discord bot designed around stability, token telemetry, and Machine Learning. Built from the ground up to provide predictive analytics, multi-model LLM integration, and resilient resource management.

## Key Features

* **Multi-LLM with Smart Fallback:** Uses Google Gemini as the primary conversational model, with automatic fallbacks to NVIDIA NIM (DeepSeek/Llama/Gemma) and Groq. If one provider hits rate limits or goes down, Helith stays online.
* **Token Monitoring & Quota Prediction:** Real-time telemetry on token and model consumption. Estimates when free API quotas will be exhausted, exposed via a private web dashboard.
* **osu! Rank Progression Prediction (`/predict`):** Uses a predictive pipeline (`domains/osu/ml_model.py`) combining empirical playtime curves, improvement indicators, and trend estimation to forecast how many days it will take a player to reach a target global rank.
* **Semantic Memory (`pgvector`):** Uses `pgvector` in Supabase (PostgreSQL) to retrieve relevant conversational memories by semantic similarity, reducing unnecessary prompt token usage.
* **Real-Time Web Search:** Native integration with Tavily for up-to-date news, weather, and current events.
* **Database Resilience:** Built on PostgreSQL (Supabase) with automatic fallback to local SQLite if the external database connection drops.

## Commands

### Interaction
Helith responds naturally when mentioned (e.g., `@Helith how are you?`).
Utility slash commands:

* `/help` — Displays the interactive help panel.
* `/predict [username] [target_rank]` — Predicts how many days it will take a player to reach the given osu! rank.

### Administration (Text Commands)
Owner-only commands:

* `h.metrics` — Generates a quick metrics report in Discord.
* `h.tavily [query]` — Performs a direct test search using Tavily.
* `h.sync [global|clear]` — Manages Discord's command tree synchronization.

## Telemetry Dashboard

Helith exposes a port (`8080` by default) for a private web dashboard displaying usage metrics, rate limits per server, active models, and quota exhaustion predictions (protected by `DASHBOARD_PASSWORD`).

## Tech Stack

* Python 3.11+
* `discord.py`
* Supabase (PostgreSQL + `pgvector`) & SQLite fallback
* Scikit-Learn & XGBoost
* Flask & Chart.js (Dashboard)

## Local Setup

Helith is configured for deployment on Render and uses `uv` for dependency management:

```bash
# 1. Clone the repo and navigate to it
git clone https://github.com/Janlhx/Helith-Proyect.git
cd Helith-Proyect

# 2. Copy the environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Start the bot
uv run main.py
```
