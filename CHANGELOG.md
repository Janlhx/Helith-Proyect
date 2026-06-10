# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-09

### Added
- **Smart Conversation Domain:** Core conversational AI capabilities powered by a Multi-LLM strategy.
- **LLM Fallback System:** Automatic failover between Gemini, NVIDIA NIM, and Groq providers to ensure high availability.
- **Semantic Memory System:** Vector-based memory using text embeddings and cosine similarity to maintain conversation context. Includes a fallback from Supabase to a local SQLite database.
- **Real-Time Web Search:** Integration with the Tavily API to fetch real-time news and facts when required by user intent.
- **osu! Predictions Domain:** A custom Machine Learning model utilizing adaptive log-linear regression to predict the days required for a player to reach a target rank, based on an individualized "Improvement Indicator" (ii).
- **Web Dashboard & Telemetry:** A built-in Flask server providing real-time telemetry, API usage, active LLM status, and basic health checks (`/health`, `/ping`).
- **Rate Limiting:** Advanced bucket-based rate limiting per user and per guild to prevent spam and API quota exhaustion.
- **Admin Utilities:** Interactive UI Help panel with module selections (Home, osu! Prediction, AI Conversation) and hidden commands for debugging metrics and search capabilities.
- **Robust CI/CD Pipeline:** Test coverage across endpoints and core logic, automated linting via `ruff`, and testing via `pytest`.

### Changed
- Refactored architecture into a clean Domain-Driven Design (DDD) to support future scalability and maintainability.
- Streamlined the Help Panel to hide technical terminology (like "Multi-LLM Fallback" or "Monitoring & Telemetry") from standard users.

### Fixed
- Addressed multiple linting and line-length (E501) formatting errors to strictly comply with `ruff` standards.
- Fixed an authentication mismatch bug during automated Web Server tests where the mocked authorization token mismatched against an empty environmental variable.
