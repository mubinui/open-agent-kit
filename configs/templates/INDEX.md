# Configuration Templates Index

Complete index of all configuration templates and examples for the industry-grade orchestration service.

## Documentation Files

| File | Description | Use When |
|------|-------------|----------|
| [README.md](./README.md) | Comprehensive guide to all templates | Starting point, overview |
| [CONFIGURATION_HIERARCHY.md](./CONFIGURATION_HIERARCHY.md) | Detailed hierarchy and override rules | Understanding config layers |
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | Quick reference for common patterns | Need quick examples |
| [INDEX.md](./INDEX.md) | This file - complete index | Finding specific templates |

## Template Categories

### 1. Topology Templates (`topologies/`)

Workflow structure and agent relationships.

| Template | Type | Complexity | Use Case |
|----------|------|------------|----------|
| [sequential_workflow.json](./topologies/sequential_workflow.json) | Sequential | Simple | Linear agent chains |
| [tree_topology.json](./topologies/tree_topology.json) | Tree | Medium | Parallel research/analysis |
| [graph_topology.json](./topologies/graph_topology.json) | Graph | High | Conditional routing, cycles |
| [hybrid_topology.json](./topologies/hybrid_topology.json) | Hybrid | Medium | Mixed sequential/parallel |

**Key Features by Template:**

- **Sequential:** Strict ordering, simple debugging, predictable flow
- **Tree:** Parallel branches, result aggregation, high throughput
- **Graph:** Conditional routing, cycles with termination, dynamic decisions
- **Hybrid:** Automatic optimization, dependency resolution, balanced performance

### 2. Execution Strategy Templates (`execution/`)

How workflows execute agents.

| Template | Strategy | Optimization | Use Case |
|----------|----------|--------------|----------|
| [sequential_strategy.json](./execution/sequential_strategy.json) | Sequential | Latency | Strict ordering required |
| [parallel_strategy.json](./execution/parallel_strategy.json) | Parallel | Throughput | Independent tasks |
| [hybrid_strategy.json](./execution/hybrid_strategy.json) | Hybrid | Balanced | Complex workflows |

**Strategy Comparison:**

| Feature | Sequential | Parallel | Hybrid |
|---------|-----------|----------|--------|
| Execution Order | Strict | Concurrent | Automatic |
| Latency | High (sum) | Low (max) | Medium |
| Resource Usage | Low | High | Medium |
| Complexity | Simple | Medium | High |
| Best For | Dependencies | Independence | Mixed |

### 3. Cache Configuration Templates (`cache/`)

Caching strategies for performance and cost optimization.

| Template | Caching | TTL | Use Case |
|----------|---------|-----|----------|
| [cache_full.json](./cache/cache_full.json) | All layers | Long | Maximum performance |
| [cache_selective.json](./cache/cache_selective.json) | Strategic | Medium | Balanced approach |
| [cache_disabled.json](./cache/cache_disabled.json) | None | N/A | Real-time/testing |

**Cache Layers:**

- **llm_response:** LLM API responses (most expensive)
- **embedding:** Vector embeddings (for RAG)
- **session:** Session state
- **agent_result:** Complete agent outputs

### 4. Agent Behavior Templates (`agents/`)

Agent configuration with validation and constraints.

| Template | Features | Validation | Use Case |
|----------|----------|------------|----------|
| [agent_with_validation.json](./agents/agent_with_validation.json) | Output validation | Strict | Code generation, structured output |
| [agent_with_constraints.json](./agents/agent_with_constraints.json) | Resource limits | Medium | Controlled execution |
| [agent_minimal.json](./agents/agent_minimal.json) | Basic config | None | Simple assistants |

**Validation Types:**

- **Output Format:** JSON schema, code syntax, format templates
- **Constraints:** Length limits, forbidden patterns, timeouts
- **Security:** Pattern scanning, import restrictions, code analysis

### 5. Complete Workflow Examples (`complete_examples/`)

End-to-end workflow configurations.

| Template | Topology | Agents | Features | Duration |
|----------|----------|--------|----------|----------|
| [research_workflow.json](./complete_examples/research_workflow.json) | Tree | 6 | Parallel research, quality control | 2-3 min |
| [code_review_workflow.json](./complete_examples/code_review_workflow.json) | Sequential | 5 | Security, performance, style review | 1-2 min |
| [customer_support_workflow.json](./complete_examples/customer_support_workflow.json) | Graph | 7 | Routing, escalation, satisfaction check | 30-90 sec |

**Example Features:**

- **Research:** Multi-source parallel research with validation
- **Code Review:** Sequential specialized reviewers with comprehensive report
- **Customer Support:** Intelligent routing with escalation paths

## Quick Selection Guide

### By Use Case

| Use Case | Recommended Template |
|----------|---------------------|
| Multi-step analysis | `topologies/sequential_workflow.json` |
| Parallel research | `topologies/tree_topology.json` |
| Dynamic routing | `topologies/graph_topology.json` |
| Code generation | `agents/agent_with_validation.json` |
| Real-time chat | `cache/cache_disabled.json` |
| Batch processing | `cache/cache_full.json` |
| Complete research | `complete_examples/research_workflow.json` |
| Code review | `complete_examples/code_review_workflow.json` |
| Customer support | `complete_examples/customer_support_workflow.json` |

### By Complexity

| Complexity | Templates |
|------------|-----------|
| **Simple** | `sequential_workflow.json`, `agent_minimal.json`, `sequential_strategy.json` |
| **Medium** | `tree_topology.json`, `hybrid_topology.json`, `agent_with_constraints.json` |
| **High** | `graph_topology.json`, `agent_with_validation.json`, complete examples |

### By Performance Goal

| Goal | Templates |
|------|-----------|
| **Low Latency** | `parallel_strategy.json`, `cache_full.json`, tree topology |
| **Low Cost** | `cache_full.json`, `sequential_strategy.json` |
| **High Throughput** | `parallel_strategy.json`, `hybrid_strategy.json` |
| **Balanced** | `hybrid_strategy.json`, `cache_selective.json` |

## Configuration Checklist

When creating a new workflow, consider:

### 1. Topology Selection
- [ ] Determine agent relationships (sequential, tree, graph, hybrid)
- [ ] Define entry node
- [ ] Map agent connections (edges)
- [ ] Add termination conditions

### 2. Execution Strategy
- [ ] Choose strategy (sequential, parallel, hybrid)
- [ ] Set max_concurrent based on resources
- [ ] Configure timeout values
- [ ] Define failure handling

### 3. Cache Configuration
- [ ] Enable/disable per layer
- [ ] Set appropriate TTL values
- [ ] Configure eviction policies
- [ ] Add workflow/agent overrides

### 4. Agent Behavior
- [ ] Define output formats
- [ ] Add validation rules
- [ ] Set constraints
- [ ] Configure security checks

### 5. Resource Limits
- [ ] Set max_concurrent_executions
- [ ] Configure max_execution_time
- [ ] Define max_agent_calls
- [ ] Set max_context_size

### 6. Error Handling
- [ ] Configure retry strategy
- [ ] Set backoff parameters
- [ ] Define retry conditions
- [ ] Add error logging

### 7. Observability
- [ ] Enable tracing
- [ ] Configure logging level
- [ ] Set up metrics
- [ ] Add correlation IDs

## Template Customization Guide

### Step 1: Copy Template
```bash
cp configs/templates/topologies/sequential_workflow.json \
   configs/workflows/my_workflow.json
```

### Step 2: Update Agent IDs
Replace template agent IDs with your actual agents:
```json
{
  "nodes": [
    {"id": "step1", "agent_id": "my_agent_1"},  // Update this
    {"id": "step2", "agent_id": "my_agent_2"}   // Update this
  ]
}
```

### Step 3: Configure Execution
Adjust execution strategy and limits:
```json
{
  "execution_strategy": "hybrid",
  "resource_limits": {
    "max_execution_time": 300  // Adjust based on needs
  }
}
```

### Step 4: Set Cache Policy
Configure caching based on use case:
```json
{
  "cache_config": {
    "llm_response": {
      "enabled": true,
      "ttl": 3600  // Adjust TTL
    }
  }
}
```

### Step 5: Validate
```bash
curl -X POST http://localhost:8000/api/v1/configs/validate \
  -H "Content-Type: application/json" \
  -d @configs/workflows/my_workflow.json
```

### Step 6: Deploy
```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @configs/workflows/my_workflow.json
```

## Common Modifications

### Add Parallel Branch
```json
{
  "nodes": [
    {"id": "new_branch", "agent_id": "new_agent"}
  ],
  "edges": [
    {"from_node": "coordinator", "to_node": "new_branch"},
    {"from_node": "new_branch", "to_node": "aggregator"}
  ]
}
```

### Add Conditional Routing
```json
{
  "edges": [
    {
      "from_node": "router",
      "to_node": "handler",
      "condition": ".category == \"specific_type\""
    }
  ]
}
```

### Add Quality Control Loop
```json
{
  "edges": [
    {
      "from_node": "validator",
      "to_node": "refiner",
      "condition": ".approved == false",
      "max_iterations": 3
    },
    {"from_node": "refiner", "to_node": "validator"}
  ]
}
```

### Override Agent Config
```json
{
  "nodes": [
    {
      "id": "special_agent",
      "agent_id": "base_agent",
      "config_override": {
        "llm_config": {
          "temperature": 0.2,
          "max_tokens": 2000
        }
      }
    }
  ]
}
```

## Testing Templates

### Test Sequential Workflow
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "sequential_template",
    "message": "Test message"
  }'
```

### Test with Cache Disabled
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "my_workflow",
    "message": "Test message",
    "config_overrides": {
      "cache_config": {
        "llm_response": {"enabled": false}
      }
    }
  }'
```

### Get Execution Metrics
```bash
curl http://localhost:8000/api/v1/sessions/{session_id}/metrics
```

## Support and Resources

### Documentation
- [Main README](./README.md) - Comprehensive guide
- [Configuration Hierarchy](./CONFIGURATION_HIERARCHY.md) - Override rules
- [Quick Reference](./QUICK_REFERENCE.md) - Common patterns

### Design Documents
- [Requirements](../../.kiro/specs/industry-grade-orchestration/requirements.md)
- [Design](../../.kiro/specs/industry-grade-orchestration/design.md)
- [Tasks](../../.kiro/specs/industry-grade-orchestration/tasks.md)

### API Documentation
- Main Config Guide: `configs/README.md`
- API Reference: Check service documentation

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2024-12 | Initial topology-based configuration templates |

## Contributing

When adding new templates:

1. Follow existing naming conventions
2. Include comprehensive comments
3. Add validation examples
4. Document use cases
5. Update this index
6. Test thoroughly

## License

These templates are part of the orchestration service configuration system.
