# Migration Guide: Old Workflow Format to New Topology Format

## Overview

This guide helps you migrate from the old pattern-based workflow format to the new topology-based format. The new format provides greater flexibility, better performance through parallelization, and more explicit control over agent execution.

## What Changed?

### Old Format (Pattern-Based)

```json
{
  "id": "my_workflow",
  "pattern": "sequential",
  "entry_agent_id": "agent1",
  "recipient_agent_id": "agent2",
  "steps": [...]
}
```

### New Format (Topology-Based)

```json
{
  "id": "my_workflow",
  "topology": {
    "type": "sequential",
    "nodes": [...],
    "edges": [...],
    "entry_node": "node1"
  },
  "execution_strategy": "sequential"
}
```

### Key Differences

| Aspect | Old Format | New Format |
|--------|-----------|------------|
| Structure | Pattern-based | Graph-based (nodes + edges) |
| Flexibility | Limited patterns | Arbitrary topologies |
| Parallelization | Limited | Full support |
| Conditional routing | Not supported | Fully supported |
| Cycles | Not supported | Supported with termination |
| Configuration | Global only | Multi-layer hierarchy |
| Context passing | Implicit | Explicit strategies |

## Migration Steps

### Step 1: Identify Your Pattern

Determine which pattern your workflow uses:
- `two_agent` → Sequential topology (2 nodes)
- `sequential` → Sequential topology (N nodes)
- `group_chat` → Tree or graph topology
- `nested` → Graph topology with conditional routing

### Step 2: Convert to Topology Format

Follow the conversion guide for your pattern below.

### Step 3: Test the Migration

1. Deploy new topology configuration
2. Create test session
3. Verify execution flow
4. Compare results with old format

### Step 4: Update API Calls

No changes needed! The API remains backward compatible.

## Pattern-by-Pattern Migration

### 1. Two-Agent Pattern

**Old Format:**

```json
{
  "id": "simple_assistant",
  "pattern": "two_agent",
  "entry_agent_id": "user_proxy",
  "recipient_agent_id": "assistant",
  "max_turns": 10,
  "summary_method": "last_msg"
}
```

**New Format:**

```json
{
  "id": "simple_assistant",
  "version": "2.0",
  "topology": {
    "type": "sequential",
    "nodes": [
      {
        "id": "user_proxy_node",
        "agent_id": "user_proxy"
      },
      {
        "id": "assistant_node",
        "agent_id": "assistant"
      }
    ],
    "edges": [
      {
        "from_node": "user_proxy_node",
        "to_node": "assistant_node",
        "context_strategy": "full"
      }
    ],
    "entry_node": "user_proxy_node",
    "termination_conditions": [
      {
        "type": "max_iterations",
        "value": 10
      }
    ]
  },
  "execution_strategy": "sequential"
}
```

**Migration Notes:**
- `max_turns` → `termination_conditions.max_iterations`
- `summary_method` → `context_strategy` in edges
- Each agent becomes a node
- Add explicit edge between nodes

### 2. Sequential Pattern

**Old Format:**

```json
{
  "id": "sequential_research",
  "pattern": "sequential",
  "entry_agent_id": "reasoning_agent",
  "steps": [
    {
      "sender_id": "reasoning_agent",
      "recipient_id": "user_proxy",
      "max_turns": 3,
      "summary_method": "last_msg",
      "carryover": false
    },
    {
      "sender_id": "knowledge_agent",
      "recipient_id": "user_proxy",
      "max_turns": 5,
      "summary_method": "reflection_with_llm",
      "carryover": true
    },
    {
      "sender_id": "response_agent",
      "recipient_id": "user_proxy",
      "max_turns": 3,
      "summary_method": "last_msg",
      "carryover": true
    }
  ]
}
```

**New Format:**

```json
{
  "id": "sequential_research",
  "version": "2.0",
  "topology": {
    "type": "sequential",
    "nodes": [
      {
        "id": "reasoning_node",
        "agent_id": "reasoning_agent"
      },
      {
        "id": "knowledge_node",
        "agent_id": "knowledge_agent"
      },
      {
        "id": "response_node",
        "agent_id": "response_agent"
      }
    ],
    "edges": [
      {
        "from_node": "reasoning_node",
        "to_node": "knowledge_node",
        "context_strategy": "summary",
        "context_config": {
          "summary_method": "reflection_with_llm"
        }
      },
      {
        "from_node": "knowledge_node",
        "to_node": "response_node",
        "context_strategy": "full"
      }
    ],
    "entry_node": "reasoning_node"
  },
  "execution_strategy": "sequential"
}
```

**Migration Notes:**
- Each step becomes a node
- Steps define edges between nodes
- `carryover: true` → `context_strategy: "full"`
- `carryover: false` → `context_strategy: "selective"` or `"summary"`
- `summary_method` → `context_config.summary_method`

### 3. Group Chat Pattern

**Old Format:**

```json
{
  "id": "group_brainstorm",
  "pattern": "group_chat",
  "entry_agent_id": "facilitator",
  "group_chat": {
    "agents": ["facilitator", "creative_agent", "analytical_agent", "critic_agent"],
    "max_round": 15,
    "speaker_selection_method": "auto"
  }
}
```

**New Format (Tree Topology):**

```json
{
  "id": "group_brainstorm",
  "version": "2.0",
  "topology": {
    "type": "tree",
    "nodes": [
      {
        "id": "facilitator_node",
        "agent_id": "facilitator"
      },
      {
        "id": "creative_node",
        "agent_id": "creative_agent"
      },
      {
        "id": "analytical_node",
        "agent_id": "analytical_agent"
      },
      {
        "id": "critic_node",
        "agent_id": "critic_agent"
      },
      {
        "id": "synthesizer_node",
        "agent_id": "response_agent"
      }
    ],
    "edges": [
      {"from_node": "facilitator_node", "to_node": "creative_node"},
      {"from_node": "facilitator_node", "to_node": "analytical_node"},
      {"from_node": "facilitator_node", "to_node": "critic_node"},
      {"from_node": "creative_node", "to_node": "synthesizer_node"},
      {"from_node": "analytical_node", "to_node": "synthesizer_node"},
      {"from_node": "critic_node", "to_node": "synthesizer_node"}
    ],
    "entry_node": "facilitator_node",
    "termination_conditions": [
      {
        "type": "max_iterations",
        "value": 15
      }
    ]
  },
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 3,
    "parallel_branches": ["creative_node", "analytical_node", "critic_node"]
  }
}
```

**Migration Notes:**
- Group chat agents become parallel branches
- Add facilitator as root node
- Add synthesizer to aggregate results
- `max_round` → `termination_conditions.max_iterations`
- `speaker_selection_method: "auto"` → parallel execution
- Consider adding explicit routing for `round_robin` or constrained transitions

### 4. Nested Pattern

**Old Format:**

```json
{
  "id": "nested_research_assistant",
  "pattern": "nested",
  "entry_agent_id": "research_assistant",
  "nested_chats": [
    {
      "trigger_agent_id": "research_assistant",
      "nested_chats": [
        {
          "recipient": "fact_checker",
          "message": "Verify the accuracy",
          "max_turns": 3
        },
        {
          "recipient": "source_validator",
          "message": "Validate sources",
          "max_turns": 2
        }
      ],
      "trigger_condition": "fact check"
    }
  ]
}
```

**New Format (Graph Topology):**

```json
{
  "id": "nested_research_assistant",
  "version": "2.0",
  "topology": {
    "type": "graph",
    "nodes": [
      {
        "id": "research_node",
        "agent_id": "research_assistant"
      },
      {
        "id": "fact_checker_node",
        "agent_id": "fact_checker"
      },
      {
        "id": "source_validator_node",
        "agent_id": "source_validator"
      },
      {
        "id": "finalizer_node",
        "agent_id": "response_agent"
      }
    ],
    "edges": [
      {
        "from_node": "research_node",
        "to_node": "fact_checker_node",
        "condition": ".output | contains(\"fact check\")"
      },
      {
        "from_node": "research_node",
        "to_node": "finalizer_node",
        "condition": ".output | contains(\"fact check\") | not"
      },
      {
        "from_node": "fact_checker_node",
        "to_node": "source_validator_node"
      },
      {
        "from_node": "source_validator_node",
        "to_node": "finalizer_node"
      }
    ],
    "entry_node": "research_node",
    "termination_conditions": [
      {
        "type": "agent_completion",
        "agent_id": "finalizer_node"
      }
    ]
  },
  "execution_strategy": "hybrid"
}
```

**Migration Notes:**
- Nested chats become conditional edges
- `trigger_condition` → `condition` in edge
- Each nested recipient becomes a node
- Add explicit routing logic
- Consider using graph topology for complex nesting

## Configuration Migration

### Cache Configuration

**Old:** Global only in `configs/cache.json`

**New:** Multi-layer hierarchy

```json
{
  "cache_config": {
    "llm_response": {
      "enabled": true,
      "ttl": 7200
    }
  }
}
```

Add to workflow configuration to override global settings.

### Agent Configuration

**Old:** Static in `configs/agents.json`

**New:** Can override per-node

```json
{
  "nodes": [
    {
      "id": "my_node",
      "agent_id": "reasoning_agent",
      "config_override": {
        "llm_config": {
          "temperature": 0.3
        },
        "tools": ["calculator"]
      }
    }
  ]
}
```

### Execution Configuration

**New:** Add execution strategy

```json
{
  "execution_strategy": "hybrid",
  "strategy_config": {
    "max_concurrent": 5,
    "dependency_resolution": "automatic"
  }
}
```

## Backward Compatibility

### API Compatibility

The API remains backward compatible. Old workflow configurations continue to work:

```bash
# Old format still works
POST /api/v1/sessions
{
  "workflow_id": "simple_assistant"  # Old pattern-based workflow
}

# New format also works
POST /api/v1/sessions
{
  "workflow_id": "new_topology_workflow"  # New topology-based workflow
}
```

### Configuration Files

Both formats can coexist:

```
configs/
├── workflows.json          # Can contain both old and new formats
├── workflows_v2/           # Optional: separate directory for new format
│   ├── research.json
│   └── support.json
```

### Gradual Migration

Migrate workflows incrementally:

1. Keep old workflows running
2. Create new topology versions
3. Test new versions
4. Switch traffic gradually
5. Deprecate old versions

## Migration Checklist

### Pre-Migration

- [ ] Review current workflow configurations
- [ ] Identify patterns used
- [ ] Document expected behavior
- [ ] Set up test environment
- [ ] Back up current configurations

### During Migration

- [ ] Convert workflow to topology format
- [ ] Add execution strategy
- [ ] Configure context passing
- [ ] Set resource limits
- [ ] Add termination conditions
- [ ] Test with sample data
- [ ] Verify execution flow
- [ ] Check performance metrics

### Post-Migration

- [ ] Monitor execution in production
- [ ] Compare metrics with old format
- [ ] Gather user feedback
- [ ] Optimize configuration
- [ ] Document changes
- [ ] Update team documentation

## Common Migration Issues

### Issue 1: Context Not Passed Correctly

**Problem:** Downstream agents don't receive expected context.

**Old behavior:** Implicit context passing with `carryover`

**Solution:** Explicitly configure context strategy:

```json
{
  "context_strategy": "full",  // or "summary" or "selective"
  "context_config": {
    "fields": ["result", "metadata"]
  }
}
```

### Issue 2: Execution Order Changed

**Problem:** Agents execute in unexpected order.

**Old behavior:** Implicit ordering from steps array

**Solution:** Verify edge connections and use sequential strategy:

```json
{
  "execution_strategy": "sequential",
  "strategy_config": {
    "wait_for_completion": true
  }
}
```

### Issue 3: Performance Degradation

**Problem:** Workflow slower than before.

**Old behavior:** Some implicit parallelization

**Solution:** Use parallel or hybrid strategy:

```json
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 5
  }
}
```

### Issue 4: Validation Errors

**Problem:** Topology validation fails.

**Common causes:**
- Unreachable nodes
- Missing entry node
- Invalid agent references
- Cycles without termination

**Solution:** Use validation tool:

```bash
# Validate topology before deployment
curl -X POST http://localhost:8000/api/v1/workflows/validate \
  -H "Content-Type: application/json" \
  -d @my_workflow.json
```

## Migration Tools

### Automated Conversion Script

```python
# scripts/migrate_workflow.py
import json
import sys

def migrate_two_agent(old_config):
    """Convert two-agent pattern to topology format."""
    return {
        "id": old_config["id"],
        "version": "2.0",
        "topology": {
            "type": "sequential",
            "nodes": [
                {"id": f"{old_config['entry_agent_id']}_node", 
                 "agent_id": old_config["entry_agent_id"]},
                {"id": f"{old_config['recipient_agent_id']}_node",
                 "agent_id": old_config["recipient_agent_id"]}
            ],
            "edges": [
                {
                    "from_node": f"{old_config['entry_agent_id']}_node",
                    "to_node": f"{old_config['recipient_agent_id']}_node",
                    "context_strategy": "full"
                }
            ],
            "entry_node": f"{old_config['entry_agent_id']}_node"
        },
        "execution_strategy": "sequential"
    }

def migrate_sequential(old_config):
    """Convert sequential pattern to topology format."""
    nodes = []
    edges = []
    
    for i, step in enumerate(old_config["steps"]):
        node_id = f"{step['sender_id']}_node_{i}"
        nodes.append({
            "id": node_id,
            "agent_id": step["sender_id"]
        })
        
        if i > 0:
            prev_node = f"{old_config['steps'][i-1]['sender_id']}_node_{i-1}"
            context_strategy = "full" if step.get("carryover") else "summary"
            edges.append({
                "from_node": prev_node,
                "to_node": node_id,
                "context_strategy": context_strategy
            })
    
    return {
        "id": old_config["id"],
        "version": "2.0",
        "topology": {
            "type": "sequential",
            "nodes": nodes,
            "edges": edges,
            "entry_node": nodes[0]["id"]
        },
        "execution_strategy": "sequential"
    }

# Usage
if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        old_config = json.load(f)
    
    pattern = old_config.get("pattern")
    if pattern == "two_agent":
        new_config = migrate_two_agent(old_config)
    elif pattern == "sequential":
        new_config = migrate_sequential(old_config)
    else:
        print(f"Pattern {pattern} not supported yet")
        sys.exit(1)
    
    print(json.dumps(new_config, indent=2))
```

**Usage:**

```bash
python scripts/migrate_workflow.py configs/old_workflow.json > configs/new_workflow.json
```

### Validation Tool

```bash
# Validate migrated workflow
uv run python -c "
from src.patterns.topology_engine import WorkflowGraph
import json
import sys

with open(sys.argv[1]) as f:
    config = json.load(f)

graph = WorkflowGraph.from_config(config['topology'])
result = graph.validate()

if result.is_valid:
    print('✓ Topology is valid')
else:
    print('✗ Validation errors:')
    for error in result.errors:
        print(f'  - {error}')
    sys.exit(1)
" configs/new_workflow.json
```

## Testing Migrated Workflows

### 1. Unit Testing

Test individual nodes:

```bash
# Test single agent
curl -X POST http://localhost:8000/api/v1/agents/test \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "reasoning_agent",
    "message": "Test message"
  }'
```

### 2. Integration Testing

Test complete workflow:

```bash
# Create session with new workflow
SESSION_ID=$(curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "new_topology_workflow"}' \
  | jq -r '.session_id')

# Send test message
curl -X POST http://localhost:8000/api/v1/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "Test query"}'
```

### 3. Performance Testing

Compare execution times:

```bash
# Old workflow
time curl -X POST http://localhost:8000/api/v1/sessions \
  -d '{"workflow_id": "old_workflow", "message": "test"}'

# New workflow
time curl -X POST http://localhost:8000/api/v1/sessions \
  -d '{"workflow_id": "new_workflow", "message": "test"}'
```

### 4. Load Testing

Test under load:

```bash
# Using Apache Bench
ab -n 100 -c 10 -p request.json -T application/json \
  http://localhost:8000/api/v1/sessions
```

## Best Practices

### 1. Migrate Incrementally

Start with simple workflows, then move to complex ones:

1. Two-agent patterns
2. Sequential patterns
3. Group chat patterns
4. Nested patterns

### 2. Test Thoroughly

- Test each migrated workflow independently
- Compare results with old format
- Verify performance metrics
- Check error handling

### 3. Document Changes

Document what changed and why:

```json
{
  "_migration_notes": {
    "migrated_from": "sequential pattern",
    "migration_date": "2024-12-10",
    "changes": [
      "Converted steps to nodes/edges",
      "Added explicit context passing",
      "Enabled parallel execution for independent branches"
    ]
  }
}
```

### 4. Monitor in Production

- Track execution metrics
- Monitor error rates
- Compare with baseline
- Gather user feedback

### 5. Keep Old Configs

Don't delete old configurations immediately:

```
configs/
├── workflows.json              # Current (mixed)
├── workflows_old_backup.json   # Backup of old format
└── workflows_v2/               # New topology format
```

## Getting Help

### Resources

- [Topology Configuration Guide](TOPOLOGY_CONFIGURATION.md)
- [Execution Strategies Guide](EXECUTION_STRATEGIES.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Configuration Templates](../configs/templates/)

### Support

- GitHub Issues: Report migration problems
- Documentation: Check latest docs
- Examples: Review complete examples in `configs/templates/complete_examples/`

## Next Steps

1. Review [Topology Configuration Guide](TOPOLOGY_CONFIGURATION.md)
2. Explore [Execution Strategies](EXECUTION_STRATEGIES.md)
3. Configure [Cache Settings](CACHE_CONFIGURATION.md)
4. Set up [Agent Behaviors](AGENT_BEHAVIOR.md)
5. Read [Troubleshooting Guide](TROUBLESHOOTING.md)

