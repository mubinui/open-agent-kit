<div align="center">

# 🌳 Open Agent Kit (OAK)

**An open-source multi-agent development kit — design, test, and deploy AI agent workflows from one place.**

[![CI](https://img.shields.io/github/actions/workflow/status/mubinui/open-agent-kit/ci.yml?label=CI)](../../actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![CrewAI](https://img.shields.io/badge/runtime-CrewAI-orange.svg)](https://crewai.com)

</div>

---

Open Agent Kit is a self-hosted platform for building multi-agent AI applications:

- 🎨 **Visual Studio** — a React Flow canvas for composing agent workflows (selector, sequential, parallel topologies) with drag-and-drop agents, tools, and triggers
- 🤖 **CrewAI runtime** — workflows execute on [CrewAI](https://crewai.com), with any LLM via LiteLLM (OpenRouter, OpenAI, Gemini, self-hosted vLLM, local Ollama)
- 🛠️ **Tools out of the box** — web search, RAG, a calculator, and any REST API via Swagger/OpenAPI import
- ⚡ **Live LLM tester** — validate keys, models, latency, and cost before wiring them into agents
- 🚀 **Flash deployments** — publish any workflow as a standalone chat page served at `/d/<name>/`, embeddable anywhere with an iframe
- 🔐 **Optional auth** — local users + API keys (SQL-backed), or Keycloak SSO
- 📦 **One container** — API, Studio UI, and SQLite persistence in a single Docker image

## Installation

### Prerequisites

| Method | Requirements |
|---|---|
| Docker (recommended) | Docker 24+ (or Docker Desktop) |
| Local development | Python 3.10+, [uv](https://docs.astral.sh/uv/), Node.js 22+ |

You'll also want an LLM API key — an [OpenRouter](https://openrouter.ai/keys) key works out of the box, and any LiteLLM-supported provider (OpenAI, Gemini, self-hosted vLLM, local Ollama) can be configured.

### Option 1 — Docker (recommended)

Build the image and run it:

```bash
git clone https://github.com/mubinui/open-agent-kit.git
cd open-agent-kit
docker build -t open-agent-kit .

docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY=sk-or-... \
  -v oak_data:/app/data \
  open-agent-kit
```

Open **http://localhost:8000** — the Studio UI, API (`/docs`), and deployed chatbots are all served from this one container. On first boot the database schema is created automatically on the `oak_data` volume; no other services are required.

### Option 2 — Docker Compose

```bash
git clone https://github.com/mubinui/open-agent-kit.git
cd open-agent-kit
cp .env.example .env        # add your OPENROUTER_API_KEY
docker compose up
```

Optional production services are behind profiles:

```bash
docker compose --profile postgres up     # PostgreSQL instead of SQLite
docker compose --profile qdrant up       # Qdrant vector store
docker compose --profile redis up        # Redis cache
```

With the `postgres` profile, set `DATABASE_URL=postgresql://oak:oak_pass@postgres:5432/oak` in `.env`.

### Local development

Backend (Python 3.10+, [uv](https://docs.astral.sh/uv/)):

```bash
uv sync --extra dev
uv run uvicorn src.api.main:app --reload      # API on :8000
```

Studio (Node 22+):

```bash
cd workflow-editor
npm ci
npm run dev                                    # Vite dev server on :5173, proxies /api to :8000
```

CLI chat:

```bash
uv run oak --workflow demo_multi_agent --message "What is 2 + 2 * 5?"
```

## How it works

```
┌─────────────────────────────────────────────────────┐
│                   Open Agent Kit                    │
│                                                     │
│  Studio SPA (React 19 + React Flow)   ← served at / │
│  FastAPI backend                      ← /api/v1/*   │
│  Deployed chat pages                  ← /d/<name>/  │
│                                                     │
│  CrewAI runtime ──→ LiteLLM ──→ any LLM provider    │
│                                                     │
│  configs/*.json   agents · workflows · tools        │
│  data/            SQLite DB · sessions · deployments│
└─────────────────────────────────────────────────────┘
```

Everything is configuration-driven. Agents, workflows, tools, prompts, and providers live in `configs/*.json` and are editable via the Studio UI, the REST API, or a text editor (hot-reload in development).

The bundled **demo_multi_agent** workflow routes user questions between three specialists — web search, knowledge base (RAG), and calculator — and is a good starting template.

## Configuration

All settings come from environment variables (see [.env.example](.env.example)):

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | — | LLM API key (OpenRouter default provider) |
| `LLM_MODEL` | `openai/gpt-oss-20b` | Default model id |
| `DATABASE_URL` | `sqlite:///./data/oak.db` | SQLite by default; any PostgreSQL URL works |
| `APP_PORT` | `8000` | API + Studio port |
| `OAK_ADMIN_USERNAME` / `OAK_ADMIN_PASSWORD` | — | Create the first admin account on boot |
| `OAK_AUTO_MIGRATE` | `true` | Run DB migrations on startup |
| `KEYCLOAK_ENABLED` | `false` | Optional Keycloak SSO |
| `RAG_PIPELINE_BASE_URL` | — | Optional external RAG service for the `rag_*` tools |

Authentication is **off by default** in development mode: every endpoint works unauthenticated so you can start building immediately. For production, set `ENVIRONMENT=production` and either create local users/API keys or enable Keycloak.

## API

The full interactive reference lives at `/docs`. The essentials:

```bash
# Create a session for a workflow
curl -X POST localhost:8000/api/v1/sessions \
  -H 'Content-Type: application/json' \
  -d '{"workflow_id": "demo_multi_agent"}'

# Chat
curl -X POST localhost:8000/api/v1/sessions/<session_id>/messages \
  -H 'Content-Type: application/json' \
  -d '{"message": "What is the weather in Berlin?"}'
```

Plus full CRUD for agents, workflows, tools (with Swagger import), prompts, providers, triggers/webhooks, deployments, and workflow test cases.

## Project layout

```
src/                  FastAPI backend
  api/                routers, session manager, auth
  crewai_runtime/     workflow → CrewAI translation & execution
  config/             pydantic config models, registries, validation
  tools/              built-in tools (web search, RAG, calculator, API executor)
workflow-editor/      Studio SPA (React 19 + TypeScript + Vite + React Flow)
configs/              agent/workflow/tool/provider definitions (JSON)
alembic/              database migrations
helm/  k8s/           Kubernetes deployment manifests
```

## Development

```bash
uv run pytest tests/unit -q          # backend tests
cd workflow-editor && npm run lint   # frontend lint
docker build -t open-agent-kit .     # full image build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
