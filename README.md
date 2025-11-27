<<<<<<< HEAD
# Orchestration Service

A production-grade, extensible multi-agent orchestration platform built on Microsoft Autogen 0.2. Transform any chatbot or conversational AI system with flexible agent workflows, dynamic configuration, and enterprise-ready infrastructure.

## Features

### Core Capabilities

- **🤖 Autogen-Powered Agents**: Built on Microsoft Autogen 0.2's ConversableAgent with full support for LLM interactions, tool use, code execution, and human-in-the-loop
- **🔄 Flexible Conversation Patterns**: Two-agent chat, sequential workflows, group chat orchestration, and nested conversations
- **⚙️ Dynamic Configuration**: JSON-based configuration for agents, tools, workflows, and providers with hot reload and API management
- **🔧 Tool Registry**: Dynamic tool registration using Autogen's `register_for_llm` and `register_for_execution` patterns
- **🧠 RAG Support**: Vector database integration with Autogen's RetrieveUserProxyAgent (ChromaDB, PGVector, Qdrant)

### Infrastructure

- **🌐 REST API**: FastAPI-based API with OpenAPI documentation for session management and message processing
- **📨 Async Processing**: RabbitMQ integration for scalable agent task distribution with dead letter queues
- **⚡ Redis Caching**: Multi-layer caching for sessions, embeddings, and LLM responses
- **💾 PostgreSQL Storage**: Persistent conversation history with Alembic migrations
- **📊 Observability**: Prometheus metrics, OpenTelemetry tracing, and structured logging
- **🔒 Security**: API key authentication, JWT tokens, RBAC, rate limiting, and credential encryption

### Admin Interface

- **🎨 Angular Admin UI**: Modern web interface for configuration management, testing, and monitoring
- **📈 Real-time Monitoring**: Live metrics, error tracking, and performance dashboards
- **🧪 Interactive Testing**: Chat interface for testing workflows and inspecting agent decisions

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  REST API    │  │  Admin UI    │  │  Python SDK          │  │
│  │  (FastAPI)   │  │  (Angular)   │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Conversation Pattern Engine                             │   │
│  │  • Two-Agent Chat (initiate_chat)                        │   │
│  │  • Sequential Chat (initiate_chats)                      │   │
│  │  • Group Chat (GroupChat + GroupChatManager)            │   │
│  │  • Nested Chat (register_nested_chats)                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent Factory & Configuration                           │   │
│  │  • Dynamic agent creation from JSON                      │   │
│  │  • Tool registry and registration                        │   │
│  │  • Workflow management                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ PostgreSQL   │  │ Redis Cache  │  │ RabbitMQ             │  │
│  │ (Sessions)   │  │ (Multi-layer)│  │ (Async Tasks)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Vector DBs   │  │ Prometheus   │  │ OpenTelemetry        │  │
│  │ (RAG)        │  │ (Metrics)    │  │ (Tracing)            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Conversation Flow

```
User Request → REST API → Session Manager → Conversation Pattern Engine
                                                      │
                    ┌─────────────────────────────────┴─────────────────────┐
                    │                                                       │
              Two-Agent Chat                                         Group Chat
                    │                                                       │
        ┌───────────┴───────────┐                          ┌────────────────┴────────────┐
        │                       │                          │                             │
   Reasoning Agent      Response Agent              GroupChatManager                     │
        │                       │                          │                             │
        └───────────┬───────────┘                    ┌─────┴─────┐                      │
                    │                                │           │                       │
              Shared Context                   Agent 1    Agent 2    Agent N             │
                    │                                │           │         │             │
                    └────────────────────────────────┴───────────┴─────────┴─────────────┘
                                                     │
                                          PostgreSQL + Redis Cache
```

## Quick Start

> **⚡ New to the project?** Follow our [Quick Setup Guide](docs/quick-setup-guide.md) for a streamlined 10-minute setup!

### Prerequisites

**Required:**
- Python 3.11 or later
- Docker and Docker Compose (for infrastructure services)
- At least one LLM provider API key (OpenRouter, OpenAI, or Anthropic)

**Optional:**
- Node.js 18+ and npm (for Admin UI)
- kubectl and Helm (for Kubernetes deployment)

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd orchestration-service

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install all dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**What gets installed:**
- **Core**: FastAPI, Uvicorn, Pydantic, SQLAlchemy
- **Autogen**: pyautogen 0.2.x with all dependencies
- **Infrastructure**: psycopg2, redis, pika (RabbitMQ)
- **Vector DBs**: chromadb, pgvector, qdrant-client
- **Observability**: prometheus-client, opentelemetry
- **Development**: pytest, ruff, mypy, pre-commit

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, and RabbitMQ with Docker Compose
docker-compose up -d postgres redis rabbitmq

# Verify services are running
docker-compose ps

# Check service logs if needed
docker-compose logs postgres
docker-compose logs redis
docker-compose logs rabbitmq
```

**Service URLs:**
- PostgreSQL: `localhost:5432` (user: postgres, password: postgres)
- Redis: `localhost:6379`
- RabbitMQ: `localhost:5672` (Management UI: http://localhost:15672)

### 3. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

**Required Configuration:**

```bash
# .env - Minimum required settings

# [REQUIRED] LLM Provider API Key (get from https://openrouter.ai/keys)
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here

# [REQUIRED] Database connection (use Docker defaults for local dev)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/orchestration

# [REQUIRED] Redis connection (use Docker defaults for local dev)
REDIS_URL=redis://localhost:6379/0
```

**Optional but Recommended:**

```bash
# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your-generated-secret-key-here

# Encryption (generate with: openssl rand -base64 32)
ENCRYPTION_KEY=your-generated-encryption-key-here

# RabbitMQ for async processing (use Docker defaults)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Logging
LOG_LEVEL=INFO

# Enable features
ENABLE_METRICS=true
ENABLE_AUDIT_LOGGING=true
```

**See `.env.example` for all available configuration options with detailed comments.**
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### 4. Initialize Database

```bash
# Run database migrations to create tables
alembic upgrade head

# Verify migration succeeded
alembic current
```

**What this does:**
- Creates all required database tables (sessions, messages, agents, etc.)
- Sets up indexes for performance
- Initializes audit logging tables

### 5. Verify Configuration Files

The service uses JSON configuration files in the `configs/` directory:

```bash
# Check that configuration files exist
ls -la configs/

# You should see:
# - agents.json          (agent definitions)
# - tools.json           (tool registrations)
# - workflows.json       (conversation patterns)
# - api_providers.json   (LLM provider configs)
# - prompt_templates.json (system prompts)
```

**These files are pre-configured with sensible defaults. You can customize them later.**

### 6. Start the API Server

```bash
# Start FastAPI server with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or use the convenience script
python -m src.main
```

**The API will be available at:** `http://localhost:8000`

**You should see:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 7. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "checks": {
#     "database": "healthy",
#     "redis": "healthy",
#     "rabbitmq": "healthy"
#   }
# }

# Check metrics endpoint
curl http://localhost:8000/metrics
```

### 8. Test Your First Conversation

```bash
# Create a session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "simple_assistant"}')

# Extract session ID
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

# Send a message
curl -X POST http://localhost:8000/api/v1/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Can you explain what you can do?"}' | jq

# Get conversation history
curl http://localhost:8000/api/v1/sessions/$SESSION_ID/history | jq
```

### 9. Access Interactive API Documentation

Open your browser to explore and test the API:

- **Swagger UI**: http://localhost:8000/docs (interactive API testing)
- **ReDoc**: http://localhost:8000/redoc (beautiful API documentation)
- **OpenAPI JSON**: http://localhost:8000/openapi.json (machine-readable spec)

### 10. (Optional) Start the Admin UI

```bash
# In a new terminal, navigate to admin UI directory
cd admin-ui

# Install dependencies (first time only)
npm install

# Start development server
npm start
```

**The Admin UI will be available at:** `http://localhost:4200`

**Features:**
- Visual workflow designer
- Agent configuration editor
- Real-time conversation testing
- Metrics and monitoring dashboards
- Configuration management

## Configuration Guide

### Configuration Files

All configurations are stored as JSON files in the `configs/` directory and can be managed through the REST API or Admin UI:

- **`agents.json`**: Agent definitions (system prompts, LLM configs, tools)
- **`tools.json`**: Tool registry (functions that agents can call)
- **`workflows.json`**: Conversation workflows (two-agent, sequential, group chat)
- **`api_providers.json`**: LLM providers and external APIs
- **`prompt_templates.json`**: Reusable prompt templates
- **`vector_databases.json`**: Vector DB configurations for RAG

📖 **See [`configs/README.md`](configs/README.md) for complete schema documentation, examples, and best practices.**

### Dynamic Configuration Management

#### Via REST API

```bash
# List all agents
curl http://localhost:8000/api/v1/agents

# Create new agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my_agent",
    "name": "MyAgent",
    "type": "conversable",
    "system_message": "You are a helpful assistant",
    "llm_config": {
      "provider_id": "openrouter",
      "model": "openai/gpt-4",
      "temperature": 0.7
    }
  }'

# Update agent
curl -X PUT http://localhost:8000/api/v1/agents/my_agent \
  -H "Content-Type: application/json" \
  -d '{"system_message": "Updated prompt"}'

# Delete agent
curl -X DELETE http://localhost:8000/api/v1/agents/my_agent

# Reload all configurations
curl -X POST http://localhost:8000/api/v1/configs/reload

# Get configuration status
curl http://localhost:8000/api/v1/configs/status
```

#### Via Admin UI

1. Navigate to http://localhost:4200
2. Go to **Configuration** → **Agents/Tools/Workflows**
3. Use the visual editor to create/update configurations
4. Changes are validated and saved automatically

#### Hot Reload

Configuration hot-reload is enabled in development mode. When you edit JSON files in `configs/`, they are automatically reloaded:

```bash
# Edit configuration file
nano configs/agents.json

# Changes are detected and applied automatically (no restart needed)
```

### Environment Variables

Infrastructure services (databases, caches, message brokers) are configured via environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Cache
REDIS_URL=redis://host:6379/0

# Message Broker
RABBITMQ_URL=amqp://user:pass@host:5672/

# Vector Databases
CHROMADB_PATH=./data/chromadb
QDRANT_URL=http://host:6333
PGVECTOR_URL=postgresql://user:pass@host:5432/vectordb

# LLM Providers
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-...

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development|production
ENABLE_METRICS=true
```

📖 **See [`.env.example`](.env.example) for all available environment variables with descriptions.**

### Configuration Best Practices

1. **Agents**: Use clear system messages, set appropriate temperatures, limit max_tokens
2. **Tools**: Provide detailed descriptions, test independently before assigning to agents
3. **Workflows**: Start simple (two-agent), then add complexity (sequential, group chat)
4. **Security**: Never commit API keys, use environment variables, rotate credentials regularly
5. **Testing**: Test configurations via API before deploying to production

## Running the Project

### Development Mode

```bash
# Start infrastructure
docker-compose up -d

# Activate virtual environment
source .venv/bin/activate

# Start API server with auto-reload (enables config hot-reload)
uvicorn src.api.main:app --reload --port 8000

# In another terminal, start Admin UI (optional)
cd admin-ui && npm start
```

### Production Mode

```bash
# Start all services with docker-compose
docker-compose up -d

# Or use production deployment (see docs/deployment-guide.md)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py

# Run integration tests only
pytest tests/integration/
```

### Code Quality Checks

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/

# Run all checks
ruff check src/ tests/ && mypy src/ && pytest
```

## Integrating Libraries and Modules

### Using Autogen Agents

```python
from autogen import ConversableAgent
from src.factory.agent_factory import AgentFactory
from src.config.loader import ConfigLoader

# Load configuration
config_loader = ConfigLoader()
agent_configs = config_loader.load_agents()

# Create agent factory
factory = AgentFactory(
    provider_registry=config_loader.provider_registry,
    tool_registry=config_loader.tool_registry
)

# Create an agent from configuration
agent = factory.create_agent(agent_configs["reasoning_agent"])

# Use the agent
response = agent.generate_reply(
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Registering Custom Tools

```python
from typing import Annotated
from src.config.tool_registry import ToolRegistry

# Define your tool function
def my_custom_tool(
    query: Annotated[str, "Search query"],
    max_results: Annotated[int, "Maximum results"] = 5
) -> Annotated[str, "Search results"]:
    """
    Custom tool that performs a specific task.
    """
    # Your implementation here
    return f"Results for: {query}"

# Register the tool
tool_registry = ToolRegistry()
tool_registry.register_tool(
    tool_id="my_custom_tool",
    tool_function=my_custom_tool,
    description="Custom tool for specific tasks"
)

# Use in agent configuration (configs/agents.json)
# "tools": ["my_custom_tool"]
```

### Creating Custom Conversation Patterns

```python
from src.patterns.conversation_engine import ConversationEngine
from autogen import ConversableAgent

# Initialize conversation engine
engine = ConversationEngine()

# Execute two-agent pattern
result = engine.execute_two_agent(
    initiator=agent1,
    recipient=agent2,
    message="Start conversation",
    max_turns=10
)

# Execute sequential pattern
result = engine.execute_sequential(
    agents=[agent1, agent2, agent3],
    message="Start workflow",
    steps=[
        {"sender": agent1, "recipient": agent2, "max_turns": 5},
        {"sender": agent2, "recipient": agent3, "max_turns": 3}
    ]
)

# Execute group chat pattern
result = engine.execute_group_chat(
    agents=[agent1, agent2, agent3],
    message="Start discussion",
    max_rounds=10,
    speaker_selection_method="auto"
)
```

### Using Vector Databases for RAG

```python
from src.infrastructure.vector_db.chromadb_client import ChromaDBClient
from src.agents.knowledge import KnowledgeAgent

# Initialize vector database
vector_db = ChromaDBClient(persist_directory="./data/chromadb")

# Create collection and add documents
collection = vector_db.create_collection("knowledge_base")
vector_db.add_documents(
    collection_name="knowledge_base",
    documents=["Document 1 content", "Document 2 content"],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}]
)

# Create RAG agent
knowledge_agent = KnowledgeAgent(
    config=knowledge_agent_config,
    vector_db=vector_db
)

# Query with retrieval
response = knowledge_agent.query(
    "What information do you have about X?",
    n_results=5
)
```

### Accessing Redis Cache

```python
from src.infrastructure.cache import RedisCache

# Initialize cache
cache = RedisCache(redis_url="redis://localhost:6379/0")

# Store data
cache.set("session:123", {"user_id": "user1", "state": "active"}, ttl=3600)

# Retrieve data
session_data = cache.get("session:123")

# Delete data
cache.delete("session:123")

# Use cache decorator
from src.infrastructure.cache_manager import cache_result

@cache_result(ttl=3600, key_prefix="llm_response")
def get_llm_response(prompt: str) -> str:
    # Expensive LLM call
    return llm.generate(prompt)
```

### Using PostgreSQL Store

```python
from src.infrastructure.database.postgres_store import PostgreSQLStore
from uuid import uuid4

# Initialize store
store = PostgreSQLStore(database_url="postgresql://...")

# Save conversation message
store.save_message(
    session_id=uuid4(),
    role="user",
    content="Hello!",
    metadata={"timestamp": "2025-11-16T10:00:00Z"}
)

# Get conversation history
history = store.get_history(session_id=session_id, limit=50)

# Search conversations
results = store.search_conversations(
    query="machine learning",
    limit=10
)
```

### Implementing Custom Middleware

```python
from fastapi import Request, Response
from src.api.main import app

@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    # Pre-processing
    request.state.custom_data = "value"
    
    # Process request
    response = await call_next(request)
    
    # Post-processing
    response.headers["X-Custom-Header"] = "value"
    
    return response
```

### Adding Prometheus Metrics

```python
from src.observability.metrics import MetricsCollector

# Initialize metrics
metrics = MetricsCollector()

# Track custom metrics
metrics.increment_counter("custom_events", labels={"type": "important"})
metrics.observe_histogram("custom_duration", 0.5, labels={"operation": "process"})
metrics.set_gauge("custom_value", 42, labels={"metric": "active_users"})

# Use decorators
from src.observability.metrics import track_time, count_calls

@track_time("function_duration")
@count_calls("function_calls")
def my_function():
    # Your code here
    pass
```

## Troubleshooting

### Common Issues

**1. Database connection errors:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
psql postgresql://postgres:postgres@localhost:5432/orchestration -c "SELECT 1"
```

**2. Redis connection errors:**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

**3. Import errors:**
```bash
# Reinstall dependencies
uv sync --reinstall

# Verify installation
python -c "import autogen; print(autogen.__version__)"
```

**4. Migration errors:**
```bash
# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

**5. Port already in use:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn src.api.main:app --port 8001
```

For more troubleshooting, see [docs/troubleshooting.md](docs/troubleshooting.md)

## Workflow Configuration

The orchestration service supports multiple conversation patterns through workflow configurations:

### Available Patterns

1. **Two-Agent**: Simple conversation between two agents
2. **Sequential**: Chain of conversations with context carryover
3. **Group Chat**: Multi-agent collaboration with dynamic speaker selection
4. **Nested**: Complex workflows with conditional sub-conversations

### Example Workflows

See `configs/workflows.json` for example configurations:

- `simple_assistant`: Basic two-agent Q&A
- `sequential_research`: Multi-step research pipeline (reasoning → knowledge → response)
- `group_brainstorm`: Collaborative brainstorming with multiple agents
- `constrained_group_chat`: Structured discussion with controlled transitions
- `round_robin_review`: Sequential code review by multiple reviewers

### Configuration

Workflows are defined in `configs/workflows.json`:

```json
{
  "id": "simple_assistant",
  "name": "Simple Assistant",
  "pattern": "two_agent",
  "entry_agent_id": "user_proxy",
  "recipient_agent_id": "assistant",
  "max_turns": 10,
  "enabled": true
}
```

For detailed workflow configuration documentation, see [docs/workflow-configuration.md](docs/workflow-configuration.md).

## Project Structure

```
orchestration-service/
├── src/                          # Source code
│   ├── agents/                   # Agent implementations
│   │   ├── base.py              # Base agent (ConversableAgent)
│   │   ├── reasoning.py         # Intent analysis agent
│   │   ├── knowledge.py         # RAG agent (RetrieveUserProxyAgent)
│   │   ├── response.py          # Response generation agent
│   │   └── orchestrator.py      # Agent orchestration
│   ├── api/                      # REST API layer
│   │   ├── main.py              # FastAPI application
│   │   ├── auth.py              # Authentication & authorization
│   │   ├── models.py            # API request/response models
│   │   ├── rate_limiting.py     # Rate limiting middleware
│   │   ├── session_manager.py   # Session management
│   │   └── routers/             # API route handlers
│   ├── config/                   # Configuration management
│   │   ├── settings.py          # Application settings
│   │   ├── loader.py            # Config file loader
│   │   ├── agent_models.py      # Agent config models
│   │   ├── tool_models.py       # Tool config models
│   │   ├── workflow_models.py   # Workflow config models
│   │   ├── registries.py        # Provider/prompt registries
│   │   ├── tool_registry.py     # Tool registration
│   │   └── workflow_registry.py # Workflow management
│   ├── factory/                  # Agent creation
│   │   └── agent_factory.py     # Dynamic agent factory
│   ├── infrastructure/           # Infrastructure services
│   │   ├── cache.py             # Redis cache client
│   │   ├── cache_manager.py     # Cache coordination
│   │   ├── message_broker.py    # RabbitMQ integration
│   │   ├── async_processor.py   # Async task processing
│   │   ├── database/            # Database layer
│   │   │   ├── connection.py    # DB connection pool
│   │   │   ├── postgres_store.py # PostgreSQL store
│   │   │   └── schema.py        # SQLAlchemy models
│   │   └── vector_db/           # Vector database clients
│   │       ├── base.py          # Base interface
│   │       ├── chromadb_client.py
│   │       ├── pgvector_client.py
│   │       └── qdrant_client.py
│   ├── memory/                   # Conversation memory
│   │   ├── store.py             # Memory store interface
│   │   ├── inmemory.py          # In-memory implementation
│   │   └── models.py            # Memory data models
│   ├── observability/            # Monitoring & tracing
│   │   ├── metrics.py           # Prometheus metrics
│   │   └── tracing.py           # OpenTelemetry tracing
│   ├── patterns/                 # Conversation patterns
│   │   └── conversation_engine.py # Pattern execution engine
│   ├── tools/                    # Tool implementations
│   │   ├── calculator.py        # Math operations
│   │   └── web_search.py        # DuckDuckGo search
│   └── audit_logging/            # Audit logging
│       ├── audit.py             # Audit trail
│       └── logger.py            # Structured logging
├── admin-ui/                     # Angular Admin UI
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/           # UI pages
│   │   │   │   ├── dashboard/
│   │   │   │   ├── agents/
│   │   │   │   ├── tools/
│   │   │   │   ├── workflows/
│   │   │   │   ├── testing/
│   │   │   │   └── monitoring/
│   │   │   ├── services/        # API services
│   │   │   └── models/          # TypeScript models
│   │   └── environments/        # Environment configs
│   └── package.json
├── configs/                      # Configuration files
│   ├── agents.json              # Agent definitions
│   ├── tools.json               # Tool definitions
│   ├── workflows.json           # Workflow definitions
│   ├── api_providers.json       # LLM provider configs
│   ├── prompt_templates.json    # Prompt templates
│   └── vector_databases.json    # Vector DB configs
├── tests/                        # Test suite
│   ├── unit/                    # Unit tests
│   │   ├── test_agents.py
│   │   ├── test_agent_factory.py
│   │   ├── test_conversation_engine.py
│   │   └── ...
│   └── integration/             # Integration tests
│       └── test_orchestrator.py
├── alembic/                      # Database migrations
│   ├── versions/                # Migration scripts
│   └── env.py                   # Alembic config
├── docs/                         # Documentation
│   ├── api-quickstart.md        # API quick start
│   ├── getting-started.md       # Getting started guide
│   ├── deployment-guide.md      # Deployment instructions
│   ├── workflow-configuration.md # Workflow config guide
│   └── ...
├── k8s/                          # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── ...
├── helm/                         # Helm charts
│   └── orchestration-service/
├── dashboards/                   # Grafana dashboards
│   └── orchestration-service.json
├── docker-compose.yml            # Local development stack
├── Dockerfile                    # Container image
├── pyproject.toml               # Python dependencies
└── README.md                    # This file
```

## Database Migrations

The project uses Alembic for database schema migrations.

### Initial Setup

```bash
# Set your database URL
export DATABASE_URL="postgresql://user:password@localhost:5432/orchestration"

# Run migrations to create tables
alembic upgrade head
```

### Common Migration Commands

```bash
# Create a new migration after schema changes
alembic revision --autogenerate -m "Description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Show current migration version
alembic current

# Show migration history
alembic history
```

### Environment Variables

The database connection can be configured via environment variable:

```bash
# PostgreSQL connection string
DATABASE_URL=postgresql://user:password@localhost:5432/orchestration
```

If `DATABASE_URL` is not set, Alembic will use the default from `alembic.ini`.

## Development

### Code Quality

```bash
# Run linter
ruff check src/ tests/

# Run type checker
mypy src/

# Format code
ruff format src/ tests/
```

### Testing Strategy

- **Unit Tests**: Individual agent logic and memory operations
- **Integration Tests**: Agent coordination and OpenRouter interactions
- **System Tests**: End-to-end conversation flows
- **Safety Tests**: Safeguard validation and policy enforcement

## Dynamic Configuration

The chatbot supports runtime configuration of API providers and prompt templates through JSON files.

### Managing API Providers

Edit `configs/api_providers.json` to add, modify, or remove API providers:

```json
{
  "version": "1.0",
  "last_updated": "2025-11-04T00:00:00Z",
  "providers": [
    {
      "id": "your_api",
      "name": "Your Custom API",
      "type": "api",
      "description": "Your API description",
      "base_url": "https://api.example.com/v1",
      "auth": {
        "scheme": "bearer",
        "env_var": "YOUR_API_KEY"
      },
      "enabled": true
    }
  ]
}
```

**Provider Types**: `llm`, `tool`, `search`, `database`, `api`

**Auth Schemes**: `bearer`, `api_key`, `basic`, `oauth2`, `none`

### Managing Prompt Templates

Edit `configs/prompt_templates.json` to customize system prompts:

```json
{
  "version": "1.0",
  "contexts": [
    {
      "id": "custom_prompt",
      "target": "response_agent",
      "description": "Custom system prompt",
      "prompt": "You are a specialized assistant that..."
    }
  ]
}
```

### Managing Agent Configurations

Edit `configs/agents.json` to define agent configurations:

```json
{
  "version": "1.0",
  "agents": [
    {
      "id": "reasoning_agent",
      "type": "conversable",
      "name": "ReasoningAgent",
      "system_message": "You are a reasoning agent...",
      "llm_config": {
        "provider_id": "openrouter",
        "model": "openai/gpt-4",
        "temperature": 0.7,
        "max_tokens": 500,
        "cache_seed": 42,
        "timeout": 120
      },
      "human_input_mode": "NEVER",
      "code_execution_config": false,
      "tools": [],
      "max_consecutive_auto_reply": 10,
      "description": "Analyzes user intent and creates execution plans"
    }
  ]
}
```

**Agent Types**:
- `conversable` - Standard LLM-powered agent using Autogen's ConversableAgent
- `retrieve_user_proxy` - RAG agent using RetrieveUserProxyAgent for vector database retrieval
- `group_chat_manager` - Manager for multi-agent group conversations

**Human Input Modes**: `ALWAYS`, `NEVER`, `TERMINATE`

**LLM Config Fields**:
- `provider_id` - ID of LLM provider from `api_providers.json`
- `model` - Model name (e.g., "openai/gpt-4")
- `temperature` - Sampling temperature (0.0-2.0)
- `max_tokens` - Maximum tokens in response (optional)
- `cache_seed` - Seed for caching, set to null to disable (optional)
- `timeout` - Request timeout in seconds

**Retrieve Config** (for `retrieve_user_proxy` agents):
```json
{
  "retrieve_config": {
    "task": "qa",
    "docs_path": ["./docs"],
    "chunk_token_size": 2000,
    "vector_db": "chromadb",
    "collection_name": "knowledge_base",
    "embedding_model": "all-mpnet-base-v2",
    "get_or_create": true
  }
}
```

Supported vector databases: `chromadb`, `pgvector`, `qdrant`

### CLI Commands

While running the chatbot, use these commands:

- `reload` - Reload configuration files without restarting
- `providers` - List all available API providers
- `prompts` - List all prompt templates
- `status` - Show system status and statistics
- `history` - View conversation history
- `new` - Start a new session
- `quit` / `exit` - End the conversation

### Hot Reload

The system watches the `configs/` directory for changes. When you save modifications to JSON files, the configuration automatically reloads (requires `watchdog` package).

### Adding a New API Provider

1. Add provider configuration to `configs/api_providers.json`
2. Set required environment variables in `.env`
3. Use `reload` command in the CLI to apply changes
4. The provider is immediately available to agents

**Example: Adding a mock API for testing**

The project includes a disabled mock API provider as a template. To enable it:

1. Open `configs/api_providers.json`
2. Find the `mock_api` provider
3. Set `"enabled": true`
4. Add `MOCK_API_KEY=your_key` to `.env`
5. Reload configuration in the CLI

## Key Features Explained

### Conversation Patterns

The orchestration service supports four Autogen conversation patterns:

1. **Two-Agent Chat**: Simple back-and-forth between two agents using `initiate_chat()`
2. **Sequential Chat**: Chain multiple conversations with context carryover using `initiate_chats()`
3. **Group Chat**: Multi-agent collaboration with dynamic speaker selection using `GroupChat` + `GroupChatManager`
4. **Nested Chat**: Complex workflows with conditional sub-conversations using `register_nested_chats()`

See [docs/workflow-configuration.md](docs/workflow-configuration.md) for detailed examples.

### Dynamic Configuration

All system components can be configured via JSON files or REST API:

- **Agents**: Define ConversableAgent instances with LLM configs, tools, and behaviors
- **Tools**: Register Python functions as tools using Autogen's registration pattern
- **Workflows**: Configure conversation patterns and agent sequences
- **Providers**: Add LLM providers, databases, and external services

Configuration changes are hot-reloaded without service restart.

### Vector Database RAG

Integrate semantic search using Autogen's `RetrieveUserProxyAgent`:

- **ChromaDB**: Embedded vector database (default)
- **PGVector**: PostgreSQL extension for vectors
- **Qdrant**: Standalone vector search engine

Configure document paths, chunk sizes, and embedding models via JSON.

### Observability

Built-in monitoring and tracing:

- **Prometheus Metrics**: Request rates, latencies, error rates, LLM costs
- **OpenTelemetry Tracing**: Distributed traces across agents and services
- **Structured Logging**: JSON logs with correlation IDs
- **Grafana Dashboards**: Pre-built dashboards in `dashboards/`

Access metrics at `http://localhost:8000/metrics`

## Documentation

### Getting Started
- [Getting Started Guide](docs/getting-started.md) - Detailed setup instructions
- [API Quick Start](docs/api-quickstart.md) - API usage examples
- [Environment Variables](docs/environment-variables.md) - Configuration reference

### Configuration
- [Workflow Configuration](docs/workflow-configuration.md) - Define conversation patterns
- [Agent Configuration](docs/conversation-patterns-usage.md) - Configure agents
- [Vector Database Integration](docs/vector-database-integration.md) - Setup RAG

### Infrastructure
- [Deployment Guide](docs/deployment-guide.md) - Docker, Kubernetes, cloud deployment
- [PostgreSQL Conversation Store](docs/postgresql-conversation-store.md) - Database setup
- [Redis Caching](docs/redis-caching.md) - Cache configuration
- [RabbitMQ Integration](docs/rabbitmq-integration.md) - Async processing

### Operations
- [Observability](docs/observability.md) - Monitoring and tracing
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## API Reference

### REST API Endpoints

**Session Management**
```bash
POST   /api/v1/sessions                    # Create new session
GET    /api/v1/sessions/{session_id}       # Get session details
DELETE /api/v1/sessions/{session_id}       # End session
POST   /api/v1/sessions/{session_id}/messages  # Send message
GET    /api/v1/sessions/{session_id}/history   # Get chat history
```

**Agent Management**
```bash
POST   /api/v1/agents                      # Create agent config
GET    /api/v1/agents                      # List all agents
GET    /api/v1/agents/{agent_id}           # Get agent details
PUT    /api/v1/agents/{agent_id}           # Update agent config
DELETE /api/v1/agents/{agent_id}           # Delete agent
```

**Tool Management**
```bash
POST   /api/v1/tools                       # Register tool
GET    /api/v1/tools                       # List all tools
GET    /api/v1/tools/{tool_id}             # Get tool details
PUT    /api/v1/tools/{tool_id}             # Update tool
DELETE /api/v1/tools/{tool_id}             # Delete tool
```

**Workflow Management**
```bash
POST   /api/v1/workflows                   # Create workflow
GET    /api/v1/workflows                   # List all workflows
GET    /api/v1/workflows/{workflow_id}     # Get workflow details
PUT    /api/v1/workflows/{workflow_id}     # Update workflow
DELETE /api/v1/workflows/{workflow_id}     # Delete workflow
```

**System**
```bash
GET    /health                             # Health check
GET    /metrics                            # Prometheus metrics
GET    /docs                               # Swagger UI
GET    /redoc                              # ReDoc documentation
```

Full API documentation available at `http://localhost:8000/docs`

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py

# Run integration tests only
pytest tests/integration/
```

### Code Quality

```bash
# Lint code
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current
```

### Hot Reload Development

The system watches configuration files for changes:

```bash
# Edit any config file
vim configs/agents.json

# Changes are automatically reloaded
# Check logs for reload confirmation
```

## Deployment

### Docker

```bash
# Build image
docker build -t orchestration-service:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f orchestration-service
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/

# Or use Helm
helm install orchestration-service ./helm/orchestration-service

# Check status
kubectl get pods -l app=orchestration-service
```

### Cloud Deployment

See [docs/deployment-guide.md](docs/deployment-guide.md) for:
- AWS ECS/EKS deployment
- Azure Container Apps/AKS deployment
- GCP Cloud Run/GKE deployment
- Scaling recommendations
- Production best practices

## Contributing

We welcome contributions! Please see our [Developer Guide](docs/developer-guide.md) for:
- Project structure and architecture
- Coding standards and style guide
- Testing requirements
- Pull request process

## License

[Your License Here]

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/orchestration-service/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/orchestration-service/discussions)
- **Documentation**: [docs/](docs/)

## Acknowledgments

Built with:
- [Microsoft Autogen 0.2](https://microsoft.github.io/autogen/0.2/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Angular](https://angular.io/)
- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)
- [RabbitMQ](https://www.rabbitmq.com/)
=======
# orchestration-service



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.bracits.com/rnd/ai-hub/orchestration-service.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab.bracits.com/rnd/ai-hub/orchestration-service/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
>>>>>>> bd2bb613a360e37ba96bf558efc1799defe72e76
