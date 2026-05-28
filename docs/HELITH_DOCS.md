# Helith — Planning & Architecture Documentation

> Discord Bot · Multi-LLM · ML Engineering  
> Author: Juan (Litxe) · UPB Medellín · 2026

---

## Index

1. [Overview](#1-overview)
2. [Context and Lessons from Dalet](#2-context-and-lessons-from-dalet)
3. [Project Identity](#3-project-identity)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Architecture](#6-architecture)
7. [Tech Stack](#7-tech-stack)
8. [Project Structure](#8-project-structure)
9. [DevOps and CI/CD](#9-devops-and-cicd)
10. [Development Phases](#10-development-phases)
11. [Success Metrics](#11-success-metrics)
12. [Registered Technical Decisions](#12-registered-technical-decisions)

---

## 1. Overview

Helith is a second-generation Discord bot, developed as a spiritual successor to Dalet. Unlike Dalet, which was built incrementally without formal planning (vibe coding), Helith was born with an applied software engineering process: defined requirements, architecture designed before coding, and deliberate, documented technical decisions.

**Helith does not replace Dalet.** They coexist covering different spaces:

- **Dalet** → Conversational, osu! integration, sarcastic and laid-back personality.
- **Helith** → Predictive analysis with ML, intelligent LLM resource management, reliability as a core value, reserved and direct personality.

**Guiding Principle:** Helith does fewer things than Dalet, but does them flawlessly. No broken command reaches production.

---

## 2. Context and Lessons from Dalet

Dalet accumulated structural problems over time that directly inform Helith's design:

| Problem in Dalet | Impact | Solution in Helith |
| --- | --- | --- |
| Fallback to Llama (lower quality) | Incoherent responses with the personality when Gemini ran out of quota. | A pool of comparable quality models; never degrade to an incapable model. |
| No token monitoring | Silent exhaustion without warning, impossible to act preventively. | Predictive monitoring with a dashboard and pre-exhaustion alerts. |
| Broken commands in production | Degrades the experience and user interest. | No feature reaches production if it doesn't pass automated tests. |
| Exposed technical data | Inappropriate in servers with many users. | Admin commands (metrics, sync) are hidden and only accessible by the bot owner. |
| No engineering process | Hard to maintain and evolve the project. | Domain-Driven Design (DDD) + documentation + CI/CD from day one. |

---

## 3. Project Identity

### 3.1 Helith's Personality

The counterpoint to Dalet. Where Dalet is sarcastic, acidic, and detached, Helith is reserved and deliberate — she speaks less, but when she does, it has weight. She listens before she speaks.

| Attribute | Description |
| --- | --- |
| Tone | Reserved, direct, with depth. Less acidic than Dalet. |
| Emojis | Rarely. Not performative. |
| Roleplay | No. Just direct text. |
| Relationship with Dalet | They are acquaintances. Helith can make subtle references to Dalet without being her shadow. |
| Creator | Litxe. She does not mention him unless it is relevant. |

### 3.2 Value Proposition

- Multi-server by design, not as an afterthought.
- Machine Learning as a real feature, not just a disguised API call.
- Reliability: if a feature exists, it works.
- Intelligent token management — the bot never silently collapses.

---

## 4. Functional Requirements

### FR-01 to FR-03 — Conversation with Resource Management
- **FR-01:** The bot responds when mentioned directly (reactive mode).
  - Conversation context is kept per channel, not globally.
  - Context is smartly truncated preserving the most relevant messages.
- **FR-02:** Semantic memory system per server.
  - Embeddings stored in Supabase (pgvector) for relevant context search.
  - Memory is used as additional context, not a substitute for recent history.

### FR-04 to FR-05 — Intent Router
- **FR-04:** The router classifies each message into an intent category before invoking any LLM.
  - Categories: general conversation, osu! predictive analysis, web search.
  - The classification uses deterministic logic or a lightweight local model — never an expensive API LLM.
- **FR-05:** Each intent category is assigned to a responsible domain.

### FR-06 to FR-08 — ML: osu! Predictive Analysis
- **FR-06:** The user can query a predicted time to reach a target rank using `/predict`.
  - Input: osu! username, target rank.
  - Output: estimation with confidence intervals and improvement indicators.
- **FR-07:** The model is trained with real data from the osu! API and Dalet's existing database.

### FR-09 to FR-12 — ML: Token Predictive Monitoring
- **FR-09:** The system logs every LLM call with metadata: model, tokens, server, user, timestamp.
- **FR-10:** A module predicts future consumption by model and by server, triggering preventive alerts.
- **FR-11:** Web metrics dashboard accessible only with a password.
- **FR-12:** The system deduplicates server IDs and tracks messages per day natively.

### FR-13 to FR-15 — Administration
- **FR-13:** Technical state commands (`h.sync`, `h.metrics`, `h.tavily`) are hidden and only accessible by the bot owner.
- **FR-14:** The bot reports its state upon booting (version, available models, DB status) to the logs.

### FR-16 — Real-time Web Search (Tavily)
- **FR-16:** The bot can perform real-time web searches using the Tavily API to answer questions about recent events, news, or dynamic information.

#### Design decisions for web search
| Decision | Definition |
| --- | --- |
| When it searches | Only when the question requires current info. General knowledge does not trigger a search. |
| Where it lives | `core/tools/search.py` — shared tool, any domain can invoke it. |
| Token Optimization | Tavily results are summarized into 2-3 key points before being injected into the prompt. |
| Response format | Max 3 lines. Concise, direct, with Helith's natural tone. |

---

## 5. Non-Functional Requirements

| ID | Requirement | Description |
| --- | --- | --- |
| NFR-01 | Reliability | No feature exists in production if it doesn't work. Zero broken commands. |
| NFR-02 | DB Resilience | If Supabase is unavailable, the bot operates in a degraded mode with local SQLite. |
| NFR-03 | Gradual LLM Degradation | The fallback never descends to a model incapable of sustaining the persona. |
| NFR-04 | Error Transparency | Errors are logged with sufficient context. |
| NFR-05 | Latency | Maximum conversational response time of 5 seconds under normal conditions. |

---

## 6. Architecture

### 6.1 Central Design Decision

> The orchestrator DOES NOT use an LLM to decide which domain to invoke. Classification is deterministic. This eliminates the double token cost of a pure agentic system.

### 6.2 General Flow

```
Discord Event
     │
     ▼
Discord Gateway (domains/bot)
     │
     ▼
Intent Router ──── deterministic classification
     │
     ├──► domains/conversation   (general conversation)
     ├──► domains/osu            (progress prediction)
     ├──► domains/admin          (administrative commands)
     └──► core/tools/search      (real-time web queries)
              │
              ▼
         core/llm/pool           (if domain needs LLM)
              │
              ├── Gemini 2.5 Flash (Primary)
              ├── NVIDIA NIM (DeepSeek / Llama 3) (Fallback 1)
              └── Groq Llama 3 (Fallback 2)
```

### 6.3 Multi-LLM Strategy

| Tier | Model | Use Case |
| --- | --- | --- |
| Primary | Gemini Flash / Pro | General conversation, context analysis. |
| Fallback 1 | NVIDIA NIM (DeepSeek V4, Llama) | Comparable quality, different provider. |
| Fallback 2 | Groq (Llama 3.3 70B, DeepSeek R1) | Extremely fast secondary fallback. |
| Local classification | sentence-transformers | Intent router, memory embeddings. Zero API cost. |

---

## 7. Tech Stack

| Component | Technology | Justification |
| --- | --- | --- |
| Main Language | Python 3.11+ | Unmatched ML ecosystem. |
| Discord Framework | discord.py | Stable, well documented. |
| Database | Supabase (PostgreSQL) | Generous free tier + native pgvector for embeddings. |
| Fallback DB | SQLite | Resilience without external dependencies. |
| Embeddings / Memory | pgvector in Supabase | Eliminates need for separate vector DB infrastructure. |
| Predictive ML | scikit-learn / XGBoost | osu! progress prediction. |
| Token Monitoring | Custom algorithm | Calculates burnout dates based on usage. |
| LLMs | Gemini, NVIDIA NIM, Groq | Multi-provider pool. |
| Web Server (Dashboard) | Flask | Necessary to serve the telemetry dashboard and keep Render awake. |
| Package Management | uv | Faster than pip, modern. |

---

## 8. Project Structure

Architecture based on **Domain-Driven Design (DDD)** — each domain is autonomous and contains everything it needs.

```
helith/
├── .github/
│   └── workflows/
│       ├── ci.yml              # tests + lint on push/PR
│       └── cd.yml              # deploy to Render on merge to main
├── core/                       # shared infrastructure
│   ├── db/
│   ├── llm/
│   ├── tools/
│   ├── config.py
│   └── exceptions.py
├── domains/
│   ├── bot/                    # Discord gateway + router
│   ├── conversation/           # chat history, semantic memory, LLM
│   ├── osu/                    # progress prediction + osu! API
│   ├── monitoring/             # telemetry and prediction dashboard
│   └── admin/                  # admin commands
├── tests/
│   ├── unit/
│   └── integration/
├── templates/
│   └── dashboard.html          # Web UI for telemetry
├── docs/
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 9. DevOps and CI/CD

### Branches

| Branch | Purpose |
| --- | --- |
| `development` | Daily work, features in progress. |
| `staging` | Validation before production. |
| `main` | Production, only merges what is verified. |

### CI Pipeline (GitHub Actions — ci.yml)
Runs on every push and PR:
- Linting with `ruff`
- Unit and integration tests with `pytest`
- No PR can be merged if the pipeline fails.

### CD Pipeline (GitHub Actions — cd.yml)
- Merge to `main` or `staging` triggers automatic deployment to Render.

---

## 10. Development Phases

### Phase 1 — Foundations (Completed)
- Repository structure and DDD architecture.
- Connection to Discord.
- Multi-LLM system with fallback and logging.
- Supabase connection with SQLite fallback.
- CI/CD Pipelines.

### Phase 2 — Conversation and Identity (Completed)
- Conversation history per channel with window management.
- Semantic memory with pgvector.
- Deterministic intent router.

### Phase 3 — Token Monitoring (Completed)
- LLM call logging with full metadata.
- Consumption prediction model.
- Flask-based metrics dashboard (password protected).

### Phase 4 — osu! Predictive ML (Completed)
- Data collection pipeline.
- Progress prediction model.
- Discord integration (`/predict` command).

### Phase 5 — Polish and Stabilization (Completed)
- Real-time Web Search (Tavily).
- Hidden administration commands.
- Full translation to English (v1.0).

---

## 11. Success Metrics

- Zero broken commands in production at the end of each phase.
- The bot never silently collapses — there is always a fallback response.
- The monitoring model accurately predicts token exhaustion.
- The osu! progress predictions have an acceptable mean error.
- Minimum 70% test coverage in core modules before going to production.

---

## 12. Registered Technical Decisions

| Decision | Considered Alternatives | Reason for Choice |
| --- | --- | --- |
| Python as main language | TypeScript, Mixed | Irreplaceable ML ecosystem. |
| Render over Railway | Railway, Fly.io | Render availability and ease of use with UptimeRobot. |
| Supabase over Neon | Neon, ElephantSQL | Native pgvector eliminates separate infrastructure. |
| DDD over Layered Arch | Layered, Monorepo | Well-defined domains from the start. More intuitive. |
| Deterministic router | LLM agent orchestrator | An LLM orchestrator doubles token usage. Deterministic is cheaper and faster. |
| Pool of comparable LLMs | Single provider with weak fallback | The main issue with Dalet was the fallback to a weak Llama model. Fallbacks must be transparent. |
| English as Core Language | Bilingual (ES/EN) Module | Maintaining two system prompts and dual translations is a maintenance nightmare. English provides better LLM reasoning and global reach. |
| uv over pip/poetry | pip, poetry | Faster, modern, better dependency management. |

---

*Living document — updated as the project evolves.*
