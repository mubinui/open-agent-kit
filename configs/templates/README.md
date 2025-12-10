# Configuration Templates and Examples

This directory contains comprehensive templates and examples for configuring the industry-grade orchestration service. These templates demonstrate the new topology-based workflow system, execution strategies, cache configuration, and agent behavior configuration.

## Directory Structure

```
templates/
├── README.md                           # This file
├── topologies/                         # Workflow topology examples
│   ├── sequential_workflow.json       # Simple sequential topology
│   ├── tree_topology.json             # Parallel tree topology
│   ├── graph_topology.json            # Complex graph with cycles
│   └── hybrid_topology.json           # Mixed sequential/parallel
├── execution/                          # Execution strategy examples
│   ├── sequential_strategy.json       # Sequential execution
│   ├── parallel_strategy.json         # Parallel execution
│   └── hybrid_strategy.json           # Hybrid execution
├── cache/                              # Cache configuration examples
│   ├── cache_full.json                # Full caching enabled
│   ├── cache_selective.json           # Selective caching
│   └── cache_disabled.json            # Caching disabled
├── agents/                             # Agent behavior examples
│   ├── agent_with_validation.json     # Agent with output validation
│   ├── agent_with_constraints.json    # Agent with constraints
│   └── agent_minimal.json             # Minimal agent config
└── complete_examples/                  # Full workflow examples
    ├── research_workflow.json          # Complete research workflow
    ├── code_review_workflow.json       # Code review workflow
    └── customer_support_workflow.json  # Customer support workflow
```

## Configuration Hierarchy

The orchestration service uses a multi-layer configuration hierarchy:

```
Global Config (system-wide defaults)
    ↓
Workflow Config (workflow-specific overrides)
    ↓
Agent Config (agent-specific overrides)
    ↓
Runtime Config (API-provided overrides)
```

### Override Rules

1. **Lower layers override higher layers**: Runtime > Agent > Workflow > Global
2. **Partial overrides**: Only specified fields are overridden, others inherit
3. **Validation**: All overrides must pass validation before being applied
4. **Isolation**: Configuration changes affect new sessions only, not active ones

### Example Override Flow

```json
// Global Config (configs/cache.json)
{
  "global_enabled": true,
  "layers": {
    "llm_response": {
      "enabled": true,
      "ttl": 3600
    }
  }
}

// Workflow Override (in workflow config)
{
  "cache_config": {
    "llm_response": {
      "ttl": 7200  // Override: 2 hours instead of 1 hour
    }
  }
}

// Agent Override (in agent config)
{
  "cache_override": {
    "llm_response": {
      "enabled": false  // Override: Disable cache for this agent
    }
  }
}

// Effective Config for this agent in this workflow:
// llm_response.enabled = false (from agent)
// llm_response.ttl = 7200 (from workflow, but irrelevant since disabled)
```

## Topology Types

### 1. Sequential Topology

Linear chain of agents executing in order.

**Use Cases:**
- Multi-step reasoning workflows
- Document processing pipelines
- Sequential analysis tasks

**Characteristics:**
- Strict ordering
- Each agent waits for previous to complete
- Full context passed between agents

**Example:** `topologies/sequential_workflow.json`

### 2. Tree Topology

One root agent spawning multiple parallel branches.

**Use Cases:**
- Parallel research tasks
- Multi-perspective analysis
- Distributed data gathering

**Characteristics:**
- Root agent coordinates
- Child branches execute in parallel
- Results aggregated at end

**Example:** `topologies/tree_topology.json`

### 3. Graph Topology

Arbitrary connections with conditional routing.

**Use Cases:**
- Complex decision workflows
- Iterative refinement processes
- Dynamic routing based on results

**Characteristics:**
- Flexible routing
- Conditional edges
- Cycle detection and termination

**Example:** `topologies/graph_topology.json`

### 4. Hybrid Topology

Mix of sequential and parallel execution.

**Use Cases:**
- Real-world complex workflows
- Optimized execution plans
- Balanced latency/throughput

**Characteristics:**
- Parallel where possible
- Sequential where required
- Dependency-aware execution

**Example:** `topologies/hybrid_topology.json`

## Execution Strategies

### Sequential Strategy

Execute agents one at a time in order.

**Configuration:**
```json
{
  "execution_strategy": "sequential",
  "strategy_config": {
    "wait_for_completion": true,
    "fail_fast": true
  }
}
```

**When to Use:**
- Strict ordering required
- Each step depends on previous
- Debugging and testing

### Parallel Strategy

Execute independent agents concurrently.

**Configuration:**
```json
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 5,
    "wait_for_all": true,
    "timeout_per_agent": 300
  }
}
```

**When to Use:**
- Independent tasks
- Minimize latency
- High throughput needed

### Hybrid Strategy

Automatically parallelize independent branches.

**Configuration:**
```json
{
  "execution_strategy": "hybrid",
  "strategy_config": {
    "max_concurrent": 10,
    "dependency_resolution": "automatic",
    "optimization_level": "balanced"
  }
}
```

**When to Use:**
- Complex workflows
- Optimize automatically
- Balance latency and resources

## Cache Configuration

### Global Cache Settings

Located in `configs/cache.json`:

```json
{
  "global_enabled": true,
  "layers": {
    "llm_response": { "enabled": true, "ttl": 3600 },
    "embedding": { "enabled": true, "ttl": 86400 },
    "session": { "enabled": true, "ttl": 1800 },
    "agent_result": { "enabled": false }
  }
}
```

### Workflow-Level Overrides

In workflow configuration:

```json
{
  "cache_config": {
    "llm_response": {
      "enabled": false  // Disable for real-time workflows
    }
  }
}
```

### Agent-Level Overrides

In agent configuration:

```json
{
  "cache_override": {
    "llm_response": {
      "ttl": 7200  // Longer cache for expensive agents
    }
  }
}
```

## Agent Behavior Configuration

### Output Format Validation

```json
{
  "behavior": {
    "output_format": {
      "type": "json",
      "schema": {
        "type": "object",
        "required": ["result", "confidence"],
        "properties": {
          "result": { "type": "string" },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    }
  }
}
```

### Constraints

```json
{
  "behavior": {
    "constraints": {
      "max_output_length": 5000,
      "forbidden_patterns": ["eval(", "exec(", "import os"],
      "required_patterns": ["^```python"],
      "timeout": 120
    }
  }
}
```

### Validation Rules

```json
{
  "behavior": {
    "validation": {
      "syntax_check": true,
      "security_scan": true,
      "custom_validators": ["check_code_quality", "verify_imports"]
    }
  }
}
```

## Context Passing Strategies

### Full Context

Pass complete conversation history.

```json
{
  "context_strategy": "full",
  "context_config": {
    "include_system_messages": true,
    "include_tool_calls": true
  }
}
```

### Summary Context

Summarize before passing.

```json
{
  "context_strategy": "summary",
  "context_config": {
    "summary_method": "reflection_with_llm",
    "max_summary_length": 500
  }
}
```

### Selective Context

Pass only specific fields.

```json
{
  "context_strategy": "selective",
  "context_config": {
    "fields": ["result", "metadata.confidence"],
    "transform": ".result | select(.confidence > 0.8)"
  }
}
```

## Resource Limits

### Workflow-Level Limits

```json
{
  "resource_limits": {
    "max_concurrent_executions": 5,
    "max_execution_time": 600,
    "max_agent_calls": 20,
    "max_context_size": 100000
  }
}
```

### Agent-Level Limits

```json
{
  "resource_limits": {
    "timeout": 120,
    "max_retries": 3,
    "max_tokens": 2000
  }
}
```

## Retry Strategies

### Exponential Backoff

```json
{
  "retry_strategy": {
    "max_retries": 3,
    "backoff_type": "exponential",
    "backoff_factor": 2.0,
    "initial_delay": 1.0,
    "max_delay": 60.0,
    "retry_on": ["timeout", "rate_limit", "temporary_failure"]
  }
}
```

### Fixed Delay

```json
{
  "retry_strategy": {
    "max_retries": 5,
    "backoff_type": "fixed",
    "delay": 5.0,
    "retry_on": ["network_error"]
  }
}
```

## Quick Start Examples

### 1. Simple Sequential Workflow

```bash
# Copy template
cp configs/templates/topologies/sequential_workflow.json configs/workflows/my_workflow.json

# Edit agent IDs and configuration
# Deploy via API
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @configs/workflows/my_workflow.json
```

### 2. Parallel Research Workflow

```bash
# Use tree topology template
cp configs/templates/topologies/tree_topology.json configs/workflows/research.json

# Configure parallel branches
# Deploy
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @configs/workflows/research.json
```

### 3. Custom Agent with Validation

```bash
# Copy agent template
cp configs/templates/agents/agent_with_validation.json configs/agents/my_agent.json

# Configure validation rules
# Deploy
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d @configs/agents/my_agent.json
```

## Best Practices

### 1. Start Simple

- Begin with sequential topologies
- Add parallelism incrementally
- Test each agent independently

### 2. Configure Caching Wisely

- Enable for expensive operations
- Disable for real-time data
- Use appropriate TTL values

### 3. Set Resource Limits

- Prevent runaway executions
- Set reasonable timeouts
- Monitor resource usage

### 4. Validate Agent Output

- Define clear output formats
- Use JSON schemas
- Implement security checks

### 5. Handle Errors Gracefully

- Configure retry strategies
- Set appropriate error handlers
- Log detailed error context

## Troubleshooting

### Topology Validation Errors

**Problem:** "Unreachable nodes detected"
**Solution:** Ensure all nodes have path from entry node

**Problem:** "Cycle detected without termination"
**Solution:** Add max_iterations to cycle edges

### Execution Failures

**Problem:** "Timeout exceeded"
**Solution:** Increase timeout or optimize agent

**Problem:** "Resource limit reached"
**Solution:** Increase limits or reduce concurrency

### Cache Issues

**Problem:** "Stale cached responses"
**Solution:** Reduce TTL or disable cache for agent

**Problem:** "Cache misses"
**Solution:** Check cache key generation

## Migration Guide

### From Old Workflow Format

Old format (pattern-based):
```json
{
  "pattern": "sequential",
  "steps": [...]
}
```

New format (topology-based):
```json
{
  "topology": {
    "type": "sequential",
    "nodes": [...],
    "edges": [...]
  }
}
```

See `complete_examples/` for full migration examples.

## Additional Resources

- [Design Document](../../.kiro/specs/industry-grade-orchestration/design.md)
- [Requirements Document](../../.kiro/specs/industry-grade-orchestration/requirements.md)
- [API Documentation](../../docs/API.md)
- [Configuration Reference](../README.md)
