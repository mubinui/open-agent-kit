<div align="center">

# 🤖 Orchestration Service

**A production-grade, extensible multi-agent orchestration platform built on Microsoft Autogen 0.2**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com/)
[![Angular](https://img.shields.io/badge/Angular-17+-dd0031.svg)](https://angular.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

*Transform any chatbot or conversational AI system with flexible agent workflows, dynamic configuration, and enterprise-ready infrastructure.*

[Getting Started](#-quick-start) •
[Documentation](#-documentation) •
[API Reference](#-api-reference) •
[Contributing](#-contributing)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🤖 Core Capabilities

- **Autogen-Powered Agents** — Built on Microsoft Autogen 0.2's ConversableAgent
- **Flexible Conversation Patterns** — Two-agent, sequential, group chat, nested
- **Dynamic Configuration** — JSON-based config with hot reload
- **Tool Registry** — Dynamic tool registration with Autogen patterns
- **RAG Support** — Vector database integration (ChromaDB, PGVector, Qdrant)

</td>
<td width="50%">

### 🏗️ Infrastructure

- **REST API** — FastAPI with OpenAPI documentation
- **Async Processing** — RabbitMQ for scalable task distribution
- **Caching** — Redis multi-layer caching
- **Storage** — PostgreSQL with Alembic migrations
- **Observability** — Prometheus, OpenTelemetry, structured logging
- **Security** — API keys, JWT, RBAC, rate limiting

</td>
</tr>
</table>

### 🎨 Admin Interface

Modern Angular web interface featuring:
- Visual workflow designer
- Agent configuration editor
- Real-time conversation testing
- Metrics and monitoring dashboards

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Presentation Layer                          │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│    │   REST API   │  │   Admin UI   │  │    Python SDK    │    │
│    │   (FastAPI)  │  │   (Angular)  │  │                  │    │
│    └──────────────┘  └──────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Conversation Pattern Engine                    │ │
│  │  • Two-Agent Chat    • Sequential Chat    • Group Chat     │ │
│  │  • Nested Chat       • Agent Factory      • Tool Registry  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                     Infrastructure Layer                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ PostgreSQL │  │   Redis    │  │  RabbitMQ  │  │ Vector DB │ │
│  │ (Sessions) │  │  (Cache)   │  │  (Async)   │  │   (RAG)   │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Required | Optional |
|----------|----------|
| Python 3.11+ | Node.js 18+ (Admin UI) |
| Docker & Docker Compose | kubectl & Helm (K8s) |
| LLM API Key (OpenRouter/OpenAI) | |

### Installation

```bash
# 1. Clone the repository
git clone git@gitlab.bracits.com:rnd/ai-hub/orchestration-service.git
cd orchestration-service

# 2. Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Create virtual environment and install dependencies
uv sync
source .venv/bin/activate

# 4. Start infrastructure services
docker-compose up -d postgres redis rabbitmq

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 6. Initialize database
alembic upgrade head

# 7. Start the API server
uvicorn src.api.main:app --reload --port 8000
```

### Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Create a session and send a message
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "simple_assistant"}'
```

### Start Admin UI (Optional)

```bash
cd admin-ui
npm install
npm start
# Open http://localhost:4200
```

---

## 📁 Project Structure

```
orchestration-service/
├── src/                    # Python source code
│   ├── agents/             # Agent implementations
│   ├── api/                # FastAPI REST API
│   ├── config/             # Configuration management
│   ├── factory/            # Agent factory
│   ├── infrastructure/     # Database, cache, message broker
│   ├── memory/             # Conversation memory
│   ├── observability/      # Metrics & tracing
│   ├── patterns/           # Conversation patterns
│   └── tools/              # Tool implementations
├── admin-ui/               # Angular Admin UI
├── configs/                # JSON configuration files
│   ├── agents.json         # Agent definitions
│   ├── tools.json          # Tool definitions
│   ├── workflows.json      # Workflow patterns
│   └── api_providers.json  # LLM provider configs
├── tests/                  # Test suite
├── alembic/                # Database migrations
├── k8s/                    # Kubernetes manifests
├── helm/                   # Helm charts
└── docs/                   # Documentation
```

---

## ⚙️ Configuration

### Agent Configuration

```json
{
  "id": "reasoning_agent",
  "type": "conversable",
  "name": "ReasoningAgent",
  "system_message": "You are a reasoning agent...",
  "llm_config": {
    "provider_id": "openrouter",
    "model": "openai/gpt-4",
    "temperature": 0.7
  },
  "tools": ["calculator", "web_search"]
}
```

### Workflow Patterns

| Pattern | Description |
|---------|-------------|
| `two_agent` | Simple back-and-forth between two agents |
| `sequential` | Chain of conversations with context carryover |
| `group_chat` | Multi-agent collaboration with speaker selection |
| `nested` | Complex workflows with conditional sub-conversations |

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/orchestration
REDIS_URL=redis://localhost:6379/0

# Optional
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

---

## 📚 API Reference

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/sessions` | Create new session |
| `GET` | `/api/v1/sessions/{id}` | Get session details |
| `DELETE` | `/api/v1/sessions/{id}` | End session |
| `POST` | `/api/v1/sessions/{id}/messages` | Send message |
| `GET` | `/api/v1/sessions/{id}/history` | Get chat history |

### Agent Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents` | List all agents |
| `POST` | `/api/v1/agents` | Create agent |
| `PUT` | `/api/v1/agents/{id}` | Update agent |
| `DELETE` | `/api/v1/agents/{id}` | Delete agent |

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific tests
pytest tests/unit/test_agents.py
```

### Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 🚢 Deployment

### Docker

```bash
docker build -t orchestration-service:latest .
docker-compose up -d
```

### Kubernetes

```bash
# Using manifests
kubectl apply -f k8s/

# Using Helm
helm install orchestration-service ./helm/orchestration-service
```

---

## 📖 Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Detailed setup instructions |
| [API Quick Start](docs/api-quickstart.md) | API usage examples |
| [Workflow Configuration](docs/workflow-configuration.md) | Configure conversation patterns |
| [Deployment Guide](docs/deployment-guide.md) | Production deployment |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and solutions |

---

## 🤝 Contributing

We welcome contributions! Please see our [Developer Guide](docs/developer-guide.md) for:

- Project structure and architecture
- Coding standards and style guide
- Testing requirements
- Pull request process

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:

<p>
<a href="https://microsoft.github.io/autogen/0.2/"><img src="https://img.shields.io/badge/Microsoft_Autogen-0.2-blue?style=for-the-badge" alt="Autogen"></a>
<a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
<a href="https://angular.io/"><img src="https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white" alt="Angular"></a>
<a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
<a href="https://redis.io/"><img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"></a>
</p>

---

<div align="center">

**[⬆ Back to Top](#-orchestration-service)**

Made with ❤️ by the AI Hub Team

</div>
