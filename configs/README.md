# Configuration Guide

This directory contains all JSON configuration files for the Autogen chatbot system. Configurations are loaded dynamically and can be modified via the Admin UI or directly through the REST API.

## Configuration Files

### 1. `agents.json` - Agent Definitions

Defines all conversable agents and their behaviors.

**Schema:**
```json
{
  "version": "1.0",
  "agents": [
    {
      "id": "unique_agent_id",
      "type": "conversable|retrieve_user_proxy",
      "name": "AgentName",
      "system_message": "System prompt for the agent",
      "llm_config": {
        "provider_id": "openrouter",
        "model": "openai/gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
        "cache_seed": 42,
        "timeout": 120
      },
      "human_input_mode": "NEVER|TERMINATE|ALWAYS",
      "code_execution_config": false,
      "tools": ["tool_id1", "tool_id2"],
      "max_consecutive_auto_reply": 10,
      "retrieve_config": null,
      "description": "Brief description",
      "version": 1,
      "last_updated": "2024-11-16T00:00:00Z"
    }
  ]
}
```

**Field Descriptions:**
- `id`: Unique identifier for the agent (required, string)
- `type`: Agent type - `conversable` for standard agents, `retrieve_user_proxy` for RAG agents (required)
- `name`: Display name for the agent (required, string)
- `system_message`: System prompt that defines agent behavior (string)
- `llm_config`: LLM configuration object:
  - `provider_id`: Reference to provider in `api_providers.json` (required)
  - `model`: Model name from the provider (required)
  - `temperature`: Sampling temperature 0.0-2.0 (default: 0.7)
  - `max_tokens`: Maximum response tokens (default: 1000)
  - `cache_seed`: Seed for response caching (optional)
  - `timeout`: Request timeout in seconds (default: 120)
- `human_input_mode`: When to request human input (default: NEVER)
- `code_execution_config`: Python code execution settings (false or object)
- `tools`: Array of tool IDs from `tools.json` (optional)
- `max_consecutive_auto_reply`: Max auto-replies before stopping (default: 10)
- `retrieve_config`: RAG configuration for retrieve agents (optional, object)

### 2. `tools.json` - Tool Registry

Defines callable tools that agents can use. Tools can be either **function-based** (Python functions) or **API-based** (external HTTP APIs).

**Schema:**
```json
{
  "version": "1.0",
  "tools": [
    {
      "id": "unique_tool_id",
      "name": "function_name",
      "description": "What this tool does",
      "type": "function",
      "entrypoint": "module.path:function_name",
      "enabled": true,
      "settings": {},
      "version": 1,
      "last_updated": "2024-11-16T00:00:00Z"
    }
  ]
}
```

**Field Descriptions:**
- `id`: Unique identifier for the tool (required, string)
- `name`: Function name exposed to agents (required, string)
- `description`: Clear description of tool purpose and usage (required, string)
- `type`: Tool type - `function` for Python functions, `api` for external APIs (default: function)
- `entrypoint`: Python import path in format `module.path:function` (required for function tools)
- `enabled`: Whether the tool is active (default: true, boolean)
- `settings`: Tool-specific configuration parameters (optional, object)

**Example Function Tool:**
```json
{
  "id": "calculator",
  "name": "calculate",
  "description": "Perform arithmetic calculations. Supports +, -, *, /, abs, round, etc.",
  "type": "function",
  "entrypoint": "src.tools.calculator:calculate",
  "enabled": true,
  "settings": {}
}
```

**Example API Tool:**
```json
{
  "id": "weather_api",
  "name": "get_weather",
  "description": "Get current weather information for a location",
  "type": "api",
  "enabled": true,
  "settings": {
    "type": "api",
    "api_url": "https://api.weatherapi.com/v1/current.json",
    "http_method": "GET",
    "auth_type": "api_key",
    "auth_header": "key",
    "auth_env_var": "WEATHER_API_KEY",
    "headers": {
      "Content-Type": "application/json"
    },
    "body_template": null,
    "response_path": "current.temp_c",
    "timeout": 30
  }
}
```

**API Tool Settings Fields:**
- `api_url`: Full URL to the API endpoint (required for API tools)
- `http_method`: HTTP method - `GET`, `POST`, `PUT`, `DELETE`, `PATCH` (default: POST)
- `auth_type`: Authentication type - `none`, `bearer`, `api_key`, `basic` (default: none)
- `auth_header`: Header name for API key authentication (e.g., `X-API-Key`)
- `auth_env_var`: Environment variable containing auth credentials
- `headers`: Additional HTTP headers as key-value pairs
- `body_template`: Request body template with `{variable}` placeholders for dynamic values
- `response_path`: JSON path to extract response data (e.g., `data.result`)
- `timeout`: Request timeout in seconds (default: 30)


### 3. `api_providers.json` - API Provider Configuration

Defines LLM providers, search APIs, and external services.

**Schema:**
```json
{
  "version": "1.0",
  "last_updated": "2025-11-04T00:00:00Z",
  "providers": [
    {
      "id": "unique_provider_id",
      "name": "Provider Name",
      "type": "llm|tool|api",
      "description": "Provider description",
      "base_url": "https://api.example.com/v1",
      "auth": {
        "scheme": "bearer|api_key|none",
        "env_var": "ENV_VAR_NAME"
      },
      "models": [],
      "request_defaults": {
        "timeout_seconds": 120,
        "max_retries": 2,
        "headers": {}
      },
      "enabled": true,
      "settings": {}
    }
  ]
}
```

**Field Descriptions:**
- `id`: Unique identifier for the provider (required, string)
- `name`: Display name (required, string)
- `type`: Provider category - `llm`, `tool`, or `api` (required)
- `base_url`: API base URL (required for llm/api types)
- `auth.scheme`: Authentication method (required)
- `auth.env_var`: Environment variable containing credentials (required for bearer/api_key)
- `models`: Array of available models (for LLM providers)
- `request_defaults`: Default request configuration
- `enabled`: Whether provider is active (default: true)

### 4. `workflows.json` - Workflow Orchestration

Defines agent conversation workflows and patterns.

**Schema:**
```json
{
  "version": "1.0.0",
  "workflows": [
    {
      "id": "unique_workflow_id",
      "name": "Workflow Name",
      "description": "Workflow description",
      "pattern": "two_agent|sequential|group_chat|nested",
      "entry_agent_id": "agent_id",
      "recipient_agent_id": "agent_id",
      "enabled": true,
      "max_turns": 10,
      "summary_method": "last_msg|reflection_with_llm",
      "metadata": {},
      "workflow_type": "sequential|tree|chatbot|custom",
      "persistence": "postgres|mongo_only",
      "version": 1,
      "last_updated": "2024-11-16T00:00:00Z"
    }
  ]
}
```

**Pattern Types:**

#### Two-Agent Pattern
Simple conversation between two agents.
```json
{
  "pattern": "two_agent",
  "entry_agent_id": "user_proxy",
  "recipient_agent_id": "assistant",
  "max_turns": 10
}
```

#### Sequential Pattern
Multi-step workflow with ordered agent interactions.
```json
{
  "pattern": "sequential",
  "entry_agent_id": "reasoning_agent",
  "steps": [
    {
      "sender_id": "reasoning_agent",
      "recipient_id": "user_proxy",
      "max_turns": 3,
      "carryover": false
    },
    {
      "sender_id": "knowledge_agent",
      "recipient_id": "user_proxy",
      "max_turns": 5,
      "carryover": true
    }
  ]
}
```

#### Group Chat Pattern
Multiple agents collaborating with a manager.
```json
{
  "pattern": "group_chat",
  "entry_agent_id": "moderator",
  "group_chat": {
    "agents": ["agent1", "agent2", "agent3"],
    "max_round": 15,
    "speaker_selection_method": "auto|round_robin|manual",
    "allowed_transitions": {
      "agent1": ["agent2", "agent3"],
      "agent2": ["agent1"]
    }
  }
}
```

### 5. `prompt_templates.json` - Prompt Management

Centralized prompt templates and system messages.

**Schema:**
```json
{
  "version": "1.0",
  "contexts": [
    {
      "id": "unique_prompt_id",
      "target": "agent_id",
      "description": "Purpose of this prompt",
      "prompt": "The actual prompt text"
    }
  ],
  "fallbacks": {
    "missing_provider": "Error message template",
    "missing_prompt": "Error message template"
  }
}
```

**Field Descriptions:**
- `id`: Unique identifier (required, string)
- `target`: Agent ID this prompt applies to (optional, string)
- `description`: What this prompt accomplishes (required, string)
- `prompt`: The actual prompt text with optional variables (required, string)

## Environment Variables

All sensitive credentials and infrastructure endpoints are configured via environment variables:

### Required Variables
```bash
# LLM Providers
OPENROUTER_API_KEY=your_api_key_here

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Cache
REDIS_URL=redis://host:6379/0

# Message Queue
RABBITMQ_URL=amqp://user:pass@host:5672/

# Vector Databases (optional)
CHROMADB_PATH=/path/to/chromadb
QDRANT_URL=http://host:6333
PGVECTOR_URL=postgresql://user:pass@host:5432/vectordb
```

### Optional Variables
```bash
# Application
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
MAX_CONVERSATION_TURNS=20
ENVIRONMENT=development|production

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317
PROMETHEUS_PORT=9090
```

## Configuration Best Practices

### 1. Agent Configuration
- Use descriptive `system_message` prompts that clearly define agent roles
- Set appropriate `temperature` values (0.0-0.3 for factual, 0.7-1.0 for creative)
- Limit `max_tokens` to prevent excessive costs
- Use `cache_seed` for deterministic testing

### 2. Tool Configuration
- Provide clear, detailed tool descriptions for LLM understanding
- Use descriptive `name` values that indicate tool purpose
- Test tools independently before assigning to agents
- Disable unused tools with `"enabled": false`

### 3. Workflow Configuration
- Start with simple `two_agent` patterns before complex workflows
- Use `sequential` patterns for multi-step reasoning tasks
- Set reasonable `max_turns` to prevent infinite loops
- Use `carryover: true` in sequential steps to maintain context

### 4. Security
- Never commit API keys to version control
- Store all credentials in environment variables
- Use `.env` files locally (add to `.gitignore`)
- Rotate API keys regularly in production

## API Endpoints for Configuration Management

All configurations can be managed via REST API:

### Agents
- `POST /api/v1/agents` - Create new agent
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{agent_id}` - Get specific agent
- `PUT /api/v1/agents/{agent_id}` - Update agent
- `DELETE /api/v1/agents/{agent_id}` - Delete agent

### Tools
- `POST /api/v1/tools` - Register new tool
- `GET /api/v1/tools` - List all tools
- `GET /api/v1/tools/{tool_id}` - Get specific tool
- `PUT /api/v1/tools/{tool_id}` - Update tool
- `DELETE /api/v1/tools/{tool_id}` - Delete tool

### Workflows
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows` - List workflows
- `GET /api/v1/workflows/{workflow_id}` - Get workflow
- `PUT /api/v1/workflows/{workflow_id}` - Update workflow
- `DELETE /api/v1/workflows/{workflow_id}` - Delete workflow

### Prompts
- `POST /api/v1/prompts` - Create prompt template
- `GET /api/v1/prompts` - List prompts
- `GET /api/v1/prompts/{prompt_id}` - Get prompt
- `PUT /api/v1/prompts/{prompt_id}` - Update prompt
- `DELETE /api/v1/prompts/{prompt_id}` - Delete prompt

### API Providers
- `POST /api/v1/api-providers` - Register provider
- `GET /api/v1/api-providers` - List providers
- `GET /api/v1/api-providers/{provider_id}` - Get provider
- `PUT /api/v1/api-providers/{provider_id}` - Update provider
- `DELETE /api/v1/api-providers/{provider_id}` - Delete provider

## Configuration Validation

The system validates configurations against JSON schemas:

### Common Validation Errors
1. **Missing Required Fields**: Ensure all required fields are present
2. **Invalid References**: Tool/agent IDs must exist before referencing
3. **Type Mismatches**: Check field types (string, number, boolean, object)
4. **Circular Dependencies**: Workflows cannot reference themselves

### Dependency Validation
- Agents cannot reference non-existent tools
- Workflows cannot reference non-existent agents
- Deleting agents/tools checks for dependencies first

## Hot Reload

Configuration changes are loaded dynamically:
- **Agents/Tools/Workflows**: Changes take effect immediately for new sessions
- **API Providers**: Existing sessions use cached providers until reload
- **Prompts**: Updated prompts apply to new conversations

To force reload all configurations:
```bash
POST /api/v1/configs/reload
```

## Troubleshooting

### Configuration Not Loading
1. Check JSON syntax with a validator
2. Verify file permissions are readable
3. Check logs for validation errors
4. Ensure `configs/` directory is mounted in Docker

### Agent Not Responding
1. Verify `llm_config.provider_id` exists in `api_providers.json`
2. Check API key environment variable is set
3. Verify model name is correct for provider
4. Check agent has appropriate `max_consecutive_auto_reply` value

### Tool Not Working
1. Verify tool is `"enabled": true`
2. Check `entrypoint` path is correct
3. Ensure tool module is installed
4. Verify tool function signature matches Autogen requirements

### Workflow Errors
1. Verify all agent IDs exist in `agents.json`
2. Check `pattern` matches workflow structure
3. Ensure `max_turns` is reasonable (not 0 or negative)
4. Validate `group_chat.agents` list is not empty

## Examples

See individual JSON files in this directory for complete examples of each configuration type.
