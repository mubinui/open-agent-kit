# Configuration Hierarchy and Override Rules

This document provides a comprehensive guide to understanding and using the multi-layer configuration hierarchy in the orchestration service.

## Table of Contents

1. [Overview](#overview)
2. [Configuration Layers](#configuration-layers)
3. [Override Rules](#override-rules)
4. [Merge Behavior](#merge-behavior)
5. [Examples](#examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Overview

The orchestration service uses a four-layer configuration hierarchy that allows fine-grained control over system behavior while maintaining sensible defaults.

### Hierarchy Diagram

```
┌─────────────────────────────────────────┐
│         Global Configuration            │  ← System-wide defaults
│  (configs/cache.json, configs/*.json)   │
└─────────────────────────────────────────┘
                  ↓ (overrides)
┌─────────────────────────────────────────┐
│       Workflow Configuration            │  ← Workflow-specific settings
│    (workflow.cache_config, etc.)        │
└─────────────────────────────────────────┘
                  ↓ (overrides)
┌─────────────────────────────────────────┐
│         Agent Configuration             │  ← Agent-specific settings
│     (agent.cache_override, etc.)        │
└─────────────────────────────────────────┘
                  ↓ (overrides)
┌─────────────────────────────────────────┐
│        Runtime Configuration            │  ← API request parameters
│      (API request body overrides)       │
└─────────────────────────────────────────┘
```

### Key Principles

1. **Lower layers override higher layers**: Runtime > Agent > Workflow > Global
2. **Partial overrides**: Only specified fields are overridden
3. **Inheritance**: Unspecified fields inherit from higher layers
4. **Validation**: All overrides must pass validation
5. **Isolation**: Changes affect new sessions only

## Configuration Layers

### Layer 1: Global Configuration

**Location:** `configs/*.json` files

**Scope:** System-wide defaults for all workflows and agents

**Files:**
- `cache.json` - Global cache settings
- `agents.json` - Agent definitions
- `workflows.json` - Workflow definitions
- `api_providers.json` - LLM provider settings
- `tools.json` - Tool definitions

**Example (cache.json):**
```json
{
  "global_enabled": true,
  "layers": {
    "llm_response": {
      "enabled": true,
      "ttl": 3600,
      "max_size": 10000,
      "eviction_policy": "LRU"
    }
  }
}
```

**When to use:**
- Setting system-wide defaults
- Configuring infrastructure (Redis, MongoDB)
- Defining available agents and tools
- Establishing baseline policies

### Layer 2: Workflow Configuration

**Location:** Workflow definition JSON

**Scope:** Specific to one workflow

**Override Fields:**
- `cache_config` - Cache settings for this workflow
- `resource_limits` - Resource limits for this workflow
- `retry_strategy` - Retry behavior for this workflow
- `execution_strategy` - How to execute this workflow

**Example:**
```json
{
  "id": "research_workflow",
  "topology": { ... },
  "cache_config": {
    "llm_response": {
      "ttl": 7200  // Override: 2 hours instead of global 1 hour
    }
  },
  "resource_limits": {
    "max_concurrent_executions": 5,
    "max_execution_time": 600
  }
}
```

**When to use:**
- Workflow-specific optimizations
- Different cache strategies per workflow
- Workflow-specific resource limits
- Custom retry strategies

### Layer 3: Agent Configuration

**Location:** Agent definition JSON or workflow node config

**Scope:** Specific to one agent

**Override Fields:**
- `cache_override` - Cache settings for this agent
- `config_override` - Agent-specific configuration
- `resource_limits` - Agent-specific limits
- `behavior` - Output validation and constraints

**Example:**
```json
{
  "id": "expensive_agent",
  "cache_override": {
    "llm_response": {
      "enabled": true,
      "ttl": 14400  // 4 hours for expensive operations
    }
  },
  "resource_limits": {
    "timeout": 180,
    "max_retries": 5
  }
}
```

**When to use:**
- Agent-specific optimizations
- Different cache TTL for expensive agents
- Agent-specific timeouts
- Output validation rules

### Layer 4: Runtime Configuration

**Location:** API request body

**Scope:** Single execution

**Override Fields:**
- Any configuration field can be overridden at runtime
- Typically used for testing or special cases

**Example:**
```json
POST /api/v1/sessions
{
  "workflow_id": "research_workflow",
  "message": "Research AI in healthcare",
  "config_overrides": {
    "cache_config": {
      "llm_response": {
        "enabled": false  // Disable cache for this request
      }
    },
    "resource_limits": {
      "max_execution_time": 300  // Shorter timeout for this request
    }
  }
}
```

**When to use:**
- Testing without cache
- One-off special requirements
- Debugging specific issues
- User-specific overrides

## Override Rules

### Rule 1: Lower Layers Win

When the same field is specified at multiple layers, the lowest (most specific) layer takes precedence.

**Example:**
```
Global:   llm_response.ttl = 3600
Workflow: llm_response.ttl = 7200
Agent:    llm_response.ttl = 14400
Runtime:  llm_response.ttl = 1800

Effective: llm_response.ttl = 1800 (Runtime wins)
```

### Rule 2: Partial Overrides

Only specified fields are overridden. Unspecified fields inherit from higher layers.

**Example:**
```json
// Global
{
  "llm_response": {
    "enabled": true,
    "ttl": 3600,
    "max_size": 10000,
    "eviction_policy": "LRU"
  }
}

// Workflow Override
{
  "llm_response": {
    "ttl": 7200  // Only override TTL
  }
}

// Effective Configuration
{
  "llm_response": {
    "enabled": true,        // Inherited from global
    "ttl": 7200,           // Overridden by workflow
    "max_size": 10000,     // Inherited from global
    "eviction_policy": "LRU"  // Inherited from global
  }
}
```

### Rule 3: Null Values

Setting a field to `null` explicitly removes it (does not inherit).

**Example:**
```json
// Global
{
  "max_size": 10000
}

// Override
{
  "max_size": null  // Explicitly remove limit
}

// Effective
{
  "max_size": null  // No size limit
}
```

### Rule 4: Array Replacement

Arrays are replaced entirely, not merged.

**Example:**
```json
// Global
{
  "tools": ["tool_a", "tool_b", "tool_c"]
}

// Override
{
  "tools": ["tool_d"]  // Replaces entire array
}

// Effective
{
  "tools": ["tool_d"]  // Only tool_d, not merged
}
```

### Rule 5: Object Merging

Objects are merged recursively.

**Example:**
```json
// Global
{
  "llm_config": {
    "temperature": 0.7,
    "max_tokens": 1000,
    "timeout": 120
  }
}

// Override
{
  "llm_config": {
    "temperature": 0.3,
    "max_tokens": 2000
  }
}

// Effective
{
  "llm_config": {
    "temperature": 0.3,   // Overridden
    "max_tokens": 2000,   // Overridden
    "timeout": 120        // Inherited
  }
}
```

## Merge Behavior

### Deep Merge Algorithm

The system uses a deep merge algorithm that:

1. Starts with global configuration
2. Recursively merges workflow overrides
3. Recursively merges agent overrides
4. Recursively merges runtime overrides

**Pseudocode:**
```python
def merge_config(base, override):
    result = copy(base)
    for key, value in override.items():
        if value is None:
            result[key] = None
        elif isinstance(value, dict) and key in result:
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result

effective_config = merge_config(
    merge_config(
        merge_config(global_config, workflow_config),
        agent_config
    ),
    runtime_config
)
```

### Special Cases

#### Cache Configuration

Cache configuration supports three levels of override:
- Global: `configs/cache.json`
- Workflow: `workflow.cache_config`
- Agent: `agent.cache_override`

**Example:**
```json
// Global (cache.json)
{
  "global_enabled": true,
  "layers": {
    "llm_response": {"enabled": true, "ttl": 3600}
  }
}

// Workflow
{
  "cache_config": {
    "llm_response": {"ttl": 7200}
  }
}

// Agent
{
  "cache_override": {
    "llm_response": {"enabled": false}
  }
}

// Effective for this agent in this workflow
{
  "llm_response": {
    "enabled": false,  // Agent override
    "ttl": 7200        // Workflow override (irrelevant since disabled)
  }
}
```

#### Resource Limits

Resource limits can be set at workflow and agent levels:

**Example:**
```json
// Workflow
{
  "resource_limits": {
    "max_concurrent_executions": 5,
    "max_execution_time": 600,
    "max_agent_calls": 20
  }
}

// Agent
{
  "resource_limits": {
    "timeout": 120,
    "max_retries": 3
  }
}

// Effective
{
  "max_concurrent_executions": 5,  // From workflow
  "max_execution_time": 600,       // From workflow
  "max_agent_calls": 20,           // From workflow
  "timeout": 120,                  // From agent
  "max_retries": 3                 // From agent
}
```

## Examples

### Example 1: Cache Configuration Hierarchy

**Scenario:** Different cache strategies for different workflows and agents

```json
// Global (cache.json)
{
  "global_enabled": true,
  "layers": {
    "llm_response": {
      "enabled": true,
      "ttl": 3600,
      "eviction_policy": "LRU"
    }
  }
}

// Workflow: Real-time Chat
{
  "id": "realtime_chat",
  "cache_config": {
    "llm_response": {
      "enabled": false  // No cache for real-time
    }
  }
}

// Workflow: Batch Processing
{
  "id": "batch_processing",
  "cache_config": {
    "llm_response": {
      "ttl": 14400  // 4-hour cache for batch
    }
  }
}

// Agent: Expensive Analyzer (in batch workflow)
{
  "id": "expensive_analyzer",
  "cache_override": {
    "llm_response": {
      "ttl": 86400  // 24-hour cache for expensive operations
    }
  }
}

// Effective Configurations:
// 1. realtime_chat workflow, any agent:
//    llm_response.enabled = false

// 2. batch_processing workflow, normal agent:
//    llm_response.enabled = true, ttl = 14400

// 3. batch_processing workflow, expensive_analyzer:
//    llm_response.enabled = true, ttl = 86400
```

### Example 2: Resource Limits Hierarchy

**Scenario:** Different resource limits for different workflow types

```json
// Workflow: Quick Response
{
  "id": "quick_response",
  "resource_limits": {
    "max_execution_time": 60,
    "max_agent_calls": 5
  }
}

// Workflow: Deep Analysis
{
  "id": "deep_analysis",
  "resource_limits": {
    "max_execution_time": 600,
    "max_agent_calls": 30
  }
}

// Agent: Fast Responder (in quick_response)
{
  "id": "fast_responder",
  "resource_limits": {
    "timeout": 15,
    "max_retries": 1
  }
}

// Agent: Thorough Analyzer (in deep_analysis)
{
  "id": "thorough_analyzer",
  "resource_limits": {
    "timeout": 180,
    "max_retries": 5
  }
}

// Effective Configurations:
// 1. quick_response workflow, fast_responder:
//    max_execution_time = 60, max_agent_calls = 5,
//    timeout = 15, max_retries = 1

// 2. deep_analysis workflow, thorough_analyzer:
//    max_execution_time = 600, max_agent_calls = 30,
//    timeout = 180, max_retries = 5
```

### Example 3: Runtime Override

**Scenario:** Testing without cache

```json
// Normal Request
POST /api/v1/sessions
{
  "workflow_id": "research_workflow",
  "message": "Research AI"
}
// Uses workflow and agent cache settings

// Testing Request (disable cache)
POST /api/v1/sessions
{
  "workflow_id": "research_workflow",
  "message": "Research AI",
  "config_overrides": {
    "cache_config": {
      "llm_response": {"enabled": false},
      "agent_result": {"enabled": false}
    }
  }
}
// Disables all caching for this request only
```

## Best Practices

### 1. Start with Sensible Globals

Set reasonable defaults in global configuration:

```json
{
  "cache": {
    "global_enabled": true,
    "layers": {
      "llm_response": {"enabled": true, "ttl": 3600}
    }
  }
}
```

### 2. Override at the Right Level

- **Global:** System-wide policies
- **Workflow:** Workflow-specific optimizations
- **Agent:** Agent-specific tuning
- **Runtime:** Testing and debugging only

### 3. Document Overrides

Add comments explaining why overrides are needed:

```json
{
  "cache_config": {
    "llm_response": {
      "ttl": 14400,
      "_comment": "4-hour cache because this workflow processes static data"
    }
  }
}
```

### 4. Use Workflow Overrides for Patterns

Group similar workflows and use consistent overrides:

```json
// All real-time workflows
{
  "cache_config": {
    "llm_response": {"enabled": false}
  }
}

// All batch workflows
{
  "cache_config": {
    "llm_response": {"ttl": 14400}
  }
}
```

### 5. Minimize Runtime Overrides

Runtime overrides should be rare:
- Use for testing
- Use for debugging
- Avoid for normal operations

### 6. Monitor Effective Configuration

Log the effective configuration for debugging:

```python
logger.info(f"Effective config for {workflow_id}/{agent_id}: {effective_config}")
```

## Troubleshooting

### Issue: Override Not Taking Effect

**Symptoms:** Configuration change doesn't affect behavior

**Possible Causes:**
1. Override at wrong level
2. Typo in field name
3. Active session using old config
4. Validation failure (check logs)

**Solutions:**
1. Verify override is at correct level
2. Check field names match exactly
3. Start new session to test
4. Check logs for validation errors

### Issue: Unexpected Configuration Value

**Symptoms:** Configuration value different than expected

**Possible Causes:**
1. Higher priority override exists
2. Partial override not merging correctly
3. Array replacement instead of merge

**Solutions:**
1. Check all layers for overrides
2. Log effective configuration
3. Verify merge behavior for arrays vs objects

### Issue: Cache Not Working

**Symptoms:** Cache always misses

**Possible Causes:**
1. Cache disabled at some layer
2. TTL too short
3. Cache key generation issue

**Solutions:**
1. Check all layers: global, workflow, agent
2. Increase TTL
3. Check cache key includes correct fields

### Issue: Resource Limits Too Restrictive

**Symptoms:** Workflows timing out or failing

**Possible Causes:**
1. Limits set too low at workflow level
2. Agent-specific limits too restrictive
3. Cumulative effect of multiple limits

**Solutions:**
1. Review workflow resource_limits
2. Check agent-specific limits
3. Increase limits incrementally
4. Monitor actual resource usage

## Configuration Validation

The system validates all configuration at load time:

### Validation Rules

1. **Required Fields:** All required fields must be present
2. **Type Checking:** Fields must match expected types
3. **Range Validation:** Numeric values within valid ranges
4. **Reference Integrity:** Agent/tool IDs must exist
5. **Schema Validation:** JSON schemas must be valid

### Validation Errors

```json
{
  "error": "Configuration validation failed",
  "details": [
    {
      "layer": "workflow",
      "field": "cache_config.llm_response.ttl",
      "error": "Value must be positive integer"
    }
  ]
}
```

### Testing Configuration

Test configuration before deploying:

```bash
# Validate configuration
curl -X POST http://localhost:8000/api/v1/configs/validate \
  -H "Content-Type: application/json" \
  -d @my_config.json

# Get effective configuration
curl http://localhost:8000/api/v1/configs/effective?workflow_id=my_workflow&agent_id=my_agent
```

## Summary

The configuration hierarchy provides:

1. **Flexibility:** Override at any level
2. **Maintainability:** Sensible defaults with specific overrides
3. **Testability:** Runtime overrides for testing
4. **Isolation:** Changes don't affect active sessions
5. **Validation:** All changes validated before application

**Key Takeaways:**
- Lower layers override higher layers
- Partial overrides inherit unspecified fields
- Objects merge, arrays replace
- Document your overrides
- Test configuration changes
