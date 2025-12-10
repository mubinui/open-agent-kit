# Configuration Quick Reference Guide

A quick reference for common configuration tasks and patterns.

## Quick Links

- [Topology Types](#topology-types)
- [Execution Strategies](#execution-strategies)
- [Cache Configurations](#cache-configurations)
- [Agent Behaviors](#agent-behaviors)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Topology Types

### Sequential Workflow
**Use when:** Steps must execute in order
```json
{
  "topology": {
    "type": "sequential",
    "nodes": [
      {"id": "step1", "agent_id": "agent_a"},
      {"id": "step2", "agent_id": "agent_b"},
      {"id": "step3", "agent_id": "agent_c"}
    ],
    "edges": [
      {"from_node": "step1", "to_node": "step2"},
      {"from_node": "step2", "to_node": "step3"}
    ],
    "entry_node": "step1"
  },
  "execution_strategy": "sequential"
}
```

### Tree Workflow (Parallel Branches)
**Use when:** Multiple independent tasks from one coordinator
```json
{
  "topology": {
    "type": "tree",
    "nodes": [
      {"id": "coordinator", "agent_id": "planner"},
      {"id": "worker1", "agent_id": "worker"},
      {"id": "worker2", "agent_id": "worker"},
      {"id": "worker3", "agent_id": "worker"},
      {"id": "aggregator", "agent_id": "synthesizer"}
    ],
    "edges": [
      {"from_node": "coordinator", "to_node": "worker1"},
      {"from_node": "coordinator", "to_node": "worker2"},
      {"from_node": "coordinator", "to_node": "worker3"},
      {"from_node": "worker1", "to_node": "aggregator"},
      {"from_node": "worker2", "to_node": "aggregator"},
      {"from_node": "worker3", "to_node": "aggregator"}
    ],
    "entry_node": "coordinator"
  },
  "execution_strategy": "parallel"
}
```

### Graph Workflow (Conditional Routing)
**Use when:** Dynamic routing based on results
```json
{
  "topology": {
    "type": "graph",
    "nodes": [
      {"id": "router", "agent_id": "classifier"},
      {"id": "path_a", "agent_id": "handler_a"},
      {"id": "path_b", "agent_id": "handler_b"},
      {"id": "finalizer", "agent_id": "responder"}
    ],
    "edges": [
      {
        "from_node": "router",
        "to_node": "path_a",
        "condition": ".classification == \"type_a\""
      },
      {
        "from_node": "router",
        "to_node": "path_b",
        "condition": ".classification == \"type_b\""
      },
      {"from_node": "path_a", "to_node": "finalizer"},
      {"from_node": "path_b", "to_node": "finalizer"}
    ],
    "entry_node": "router"
  },
  "execution_strategy": "hybrid"
}
```

## Execution Strategies

### Sequential
```json
{
  "execution_strategy": "sequential",
  "strategy_config": {
    "wait_for_completion": true,
    "fail_fast": true
  }
}
```

### Parallel
```json
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 5,
    "wait_for_all": true
  }
}
```

### Hybrid (Recommended)
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

## Cache Configurations

### Enable All Caching
```json
{
  "cache_config": {
    "llm_response": {"enabled": true, "ttl": 3600},
    "embedding": {"enabled": true, "ttl": 86400},
    "agent_result": {"enabled": true, "ttl": 1800}
  }
}
```

### Disable Caching (Real-time)
```json
{
  "cache_config": {
    "llm_response": {"enabled": false},
    "embedding": {"enabled": false},
    "agent_result": {"enabled": false}
  }
}
```

### Selective Caching
```json
{
  "cache_config": {
    "llm_response": {"enabled": true, "ttl": 1800},
    "embedding": {"enabled": true, "ttl": 43200},
    "agent_result": {"enabled": false}
  }
}
```

## Agent Behaviors

### JSON Output with Validation
```json
{
  "behavior": {
    "output_format": {
      "type": "json",
      "schema": {
        "type": "object",
        "required": ["result", "confidence"],
        "properties": {
          "result": {"type": "string"},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    }
  }
}
```

### Code Output with Security
```json
{
  "behavior": {
    "output_format": {
      "type": "code",
      "language": "python"
    },
    "constraints": {
      "forbidden_patterns": ["eval\\(", "exec\\(", "import os"]
    },
    "validation": {
      "syntax_check": true,
      "security_scan": true
    }
  }
}
```

### Output Length Constraints
```json
{
  "behavior": {
    "constraints": {
      "max_output_length": 5000,
      "min_output_length": 100,
      "timeout": 120
    }
  }
}
```

## Common Patterns

### Pattern 1: Research with Parallel Sources
```json
{
  "topology": {
    "type": "tree",
    "nodes": [
      {"id": "planner", "agent_id": "reasoning_agent"},
      {"id": "source1", "agent_id": "knowledge_agent"},
      {"id": "source2", "agent_id": "knowledge_agent"},
      {"id": "source3", "agent_id": "knowledge_agent"},
      {"id": "synthesizer", "agent_id": "response_agent"}
    ]
  },
  "execution_strategy": "parallel",
  "cache_config": {
    "llm_response": {"enabled": true, "ttl": 7200}
  }
}
```

### Pattern 2: Quality Control Loop
```json
{
  "topology": {
    "type": "graph",
    "nodes": [
      {"id": "generator", "agent_id": "creator"},
      {"id": "validator", "agent_id": "checker"},
      {"id": "refiner", "agent_id": "improver"},
      {"id": "finalizer", "agent_id": "publisher"}
    ],
    "edges": [
      {"from_node": "generator", "to_node": "validator"},
      {
        "from_node": "validator",
        "to_node": "finalizer",
        "condition": ".approved == true"
      },
      {
        "from_node": "validator",
        "to_node": "refiner",
        "condition": ".approved == false",
        "max_iterations": 3
      },
      {"from_node": "refiner", "to_node": "validator"}
    ]
  }
}
```

### Pattern 3: Intelligent Routing
```json
{
  "topology": {
    "type": "graph",
    "nodes": [
      {"id": "classifier", "agent_id": "router"},
      {"id": "simple_handler", "agent_id": "quick_responder"},
      {"id": "complex_handler", "agent_id": "deep_analyzer"},
      {"id": "finalizer", "agent_id": "formatter"}
    ],
    "edges": [
      {
        "from_node": "classifier",
        "to_node": "simple_handler",
        "condition": ".complexity == \"simple\""
      },
      {
        "from_node": "classifier",
        "to_node": "complex_handler",
        "condition": ".complexity == \"complex\""
      },
      {"from_node": "simple_handler", "to_node": "finalizer"},
      {"from_node": "complex_handler", "to_node": "finalizer"}
    ]
  }
}
```

## Resource Limits

### Conservative (Low Resource)
```json
{
  "resource_limits": {
    "max_concurrent_executions": 2,
    "max_execution_time": 180,
    "max_agent_calls": 10,
    "max_context_size": 50000
  }
}
```

### Balanced (Recommended)
```json
{
  "resource_limits": {
    "max_concurrent_executions": 5,
    "max_execution_time": 300,
    "max_agent_calls": 20,
    "max_context_size": 100000
  }
}
```

### Aggressive (High Performance)
```json
{
  "resource_limits": {
    "max_concurrent_executions": 10,
    "max_execution_time": 600,
    "max_agent_calls": 50,
    "max_context_size": 200000
  }
}
```

## Retry Strategies

### Exponential Backoff (Recommended)
```json
{
  "retry_strategy": {
    "max_retries": 3,
    "backoff_type": "exponential",
    "backoff_factor": 2.0,
    "initial_delay": 1.0,
    "retry_on": ["timeout", "rate_limit"]
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

### No Retry (Fail Fast)
```json
{
  "retry_strategy": {
    "max_retries": 0
  }
}
```

## Context Passing

### Full Context
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
```json
{
  "context_strategy": "selective",
  "context_config": {
    "fields": ["result", "metadata.confidence"]
  }
}
```

## Troubleshooting

### Workflow Times Out
**Solution:** Increase timeout or reduce complexity
```json
{
  "resource_limits": {
    "max_execution_time": 600  // Increase from 300
  }
}
```

### Cache Not Working
**Solution:** Check cache is enabled at all levels
```json
{
  "cache_config": {
    "llm_response": {
      "enabled": true,  // Ensure enabled
      "ttl": 3600       // Ensure reasonable TTL
    }
  }
}
```

### Too Many Concurrent Requests
**Solution:** Reduce max_concurrent or add queuing
```json
{
  "resource_limits": {
    "max_concurrent_executions": 3  // Reduce from 10
  }
}
```

### Agent Output Invalid
**Solution:** Add validation
```json
{
  "behavior": {
    "output_format": {
      "type": "json",
      "schema": { /* your schema */ }
    },
    "validation": {
      "on_validation_failure": "retry",
      "max_validation_retries": 2
    }
  }
}
```

### Cycle Not Terminating
**Solution:** Add max_iterations to cycle edge
```json
{
  "edges": [
    {
      "from_node": "refiner",
      "to_node": "validator",
      "max_iterations": 3  // Limit cycle iterations
    }
  ]
}
```

## API Examples

### Create Workflow
```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @my_workflow.json
```

### Start Session
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "my_workflow",
    "message": "Your query here"
  }'
```

### Get Effective Config
```bash
curl http://localhost:8000/api/v1/configs/effective?workflow_id=my_workflow&agent_id=my_agent
```

### Validate Config
```bash
curl -X POST http://localhost:8000/api/v1/configs/validate \
  -H "Content-Type: application/json" \
  -d @my_config.json
```

## Template Files

- **Topologies:** `templates/topologies/`
- **Execution:** `templates/execution/`
- **Cache:** `templates/cache/`
- **Agents:** `templates/agents/`
- **Complete Examples:** `templates/complete_examples/`

## Further Reading

- [Configuration Hierarchy](./CONFIGURATION_HIERARCHY.md)
- [Templates README](./README.md)
- [Main Config Guide](../README.md)
- [Design Document](../../.kiro/specs/industry-grade-orchestration/design.md)
