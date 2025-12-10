# Topology Configuration Guide

## Overview

The orchestration service now supports flexible workflow topologies beyond simple sequential patterns. This guide explains how to configure different topology types, understand their execution characteristics, and choose the right topology for your use case.

## What is a Topology?

A **topology** defines the structure and relationships between agents in a workflow. Instead of hardcoded patterns, you now define workflows as directed graphs where:

- **Nodes** represent agents
- **Edges** represent message flow and dependencies
- **Execution strategies** determine how the graph is traversed

## Topology Types

### 1. Sequential Topology

**Description:** Linear chain of agents executing in strict order.

**Use Cases:**
- Multi-step reasoning workflows
- Document processing pipelines
- Sequential analysis tasks
- Workflows where each step depends on the previous

**Characteristics:**
- ✅ Strict ordering guaranteed
- ✅ Simple to understand and debug
- ✅ Predictable execution flow
- ❌ No parallelization
- ❌ Higher latency for independent tasks

**Configuration Example:**

```json
{
  "topology": {
    "type": "sequential",
    "nodes": [
      {
        "id": "analyzer",
        "agent_id": "reasoning_agent"
      },
      {
        "id": "researcher",
        "agent_id": "knowledge_agent"
      },
      {
        "id": "responder",
        "agent_id": "response_agent"
      }
    ],
    "edges": [
      {
        "from_node": "analyzer",
        "to_node": "researcher",
        "context_strategy": "full"
      },
      {
        "from_node": "researcher",
        "to_node": "responder",
        "context_strategy": "full"
      }
    ],
    "entry_node": "analyzer"
  }
}
```

**Execution Flow:**
```
User Query → Analyzer → Researcher → Responder → Final Response
```

### 2. Tree Topology

**Description:** One root agent spawning multiple parallel branches that execute concurrently.

**Use Cases:**
- Parallel research tasks
- Multi-perspective analysis
- Distributed data gathering
- Independent subtask execution

**Characteristics:**
- ✅ High parallelization
- ✅ Reduced latency
- ✅ Efficient resource utilization
- ✅ Scales well with concurrent tasks
- ❌ More complex to debug
- ❌ Requires careful result aggregation

**Configuration Example:**

```json
{
  "topology": {
    "type": "tree",
    "nodes": [
      {
        "id": "coordinator",
        "agent_id": "reasoning_agent",
        "output_transform": ".research_plan"
      },
      {
        "id": "researcher_1",
        "agent_id": "knowledge_agent",
        "input_transform": ".research_plan.topics[0]"
      },
      {
        "id": "researcher_2",
        "agent_id": "knowledge_agent",
        "input_transform": ".research_plan.topics[1]"
      },
      {
        "id": "researcher_3",
        "agent_id": "knowledge_agent",
        "input_transform": ".research_plan.topics[2]"
      },
      {
        "id": "aggregator",
        "agent_id": "response_agent"
      }
    ],
    "edges": [
      {"from_node": "coordinator", "to_node": "researcher_1"},
      {"from_node": "coordinator", "to_node": "researcher_2"},
      {"from_node": "coordinator", "to_node": "researcher_3"},
      {"from_node": "researcher_1", "to_node": "aggregator"},
      {"from_node": "researcher_2", "to_node": "aggregator"},
      {"from_node": "researcher_3", "to_node": "aggregator"}
    ],
    "entry_node": "coordinator"
  },
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 3,
    "parallel_branches": ["researcher_1", "researcher_2", "researcher_3"]
  }
}
```

**Execution Flow:**
```
                    ┌─→ Researcher 1 ─┐
User Query → Coordinator ─→ Researcher 2 ─→ Aggregator → Response
                    └─→ Researcher 3 ─┘
        (parallel execution)
```

### 3. Graph Topology

**Description:** Arbitrary connections with conditional routing and cycles.

**Use Cases:**
- Complex decision workflows
- Iterative refinement processes
- Dynamic routing based on results
- Quality control loops
- Adaptive workflows

**Characteristics:**
- ✅ Maximum flexibility
- ✅ Conditional routing
- ✅ Iterative refinement
- ✅ Dynamic decision-making
- ❌ Most complex to design
- ❌ Requires cycle termination conditions
- ❌ Harder to predict execution time

**Configuration Example:**

```json
{
  "topology": {
    "type": "graph",
    "nodes": [
      {"id": "intake", "agent_id": "reasoning_agent"},
      {"id": "simple_handler", "agent_id": "response_agent"},
      {"id": "complex_handler", "agent_id": "reasoning_agent"},
      {"id": "quality_checker", "agent_id": "reasoning_agent"},
      {"id": "refiner", "agent_id": "response_agent"}
    ],
    "edges": [
      {
        "from_node": "intake",
        "to_node": "simple_handler",
        "condition": ".decision.route == \"simple\""
      },
      {
        "from_node": "intake",
        "to_node": "complex_handler",
        "condition": ".decision.route == \"complex\""
      },
      {
        "from_node": "simple_handler",
        "to_node": "quality_checker"
      },
      {
        "from_node": "quality_checker",
        "to_node": "refiner",
        "condition": ".quality_assessment.approved == false"
      },
      {
        "from_node": "refiner",
        "to_node": "quality_checker",
        "max_iterations": 3
      }
    ],
    "entry_node": "intake",
    "termination_conditions": [
      {"type": "max_iterations", "value": 10},
      {"type": "timeout", "value": 600}
    ]
  }
}
```

**Execution Flow:**
```
                    ┌─→ Simple Handler ─┐
User Query → Intake ─┤                   ├─→ Quality Checker ⇄ Refiner
                    └─→ Complex Handler ─┘         (cycle)
```

### 4. Hybrid Topology

**Description:** Mix of sequential and parallel execution with automatic optimization.

**Use Cases:**
- Real-world complex workflows
- Balanced latency/throughput
- Workflows with mixed dependencies
- Production systems

**Characteristics:**
- ✅ Automatic parallelization
- ✅ Respects dependencies
- ✅ Optimized execution
- ✅ Best of both worlds
- ⚠️ Requires dependency analysis

**Configuration Example:**

```json
{
  "topology": {
    "type": "hybrid",
    "nodes": [
      {"id": "analyzer", "agent_id": "reasoning_agent"},
      {"id": "researcher_a", "agent_id": "knowledge_agent"},
      {"id": "researcher_b", "agent_id": "knowledge_agent"},
      {"id": "validator", "agent_id": "reasoning_agent"},
      {"id": "responder", "agent_id": "response_agent"}
    ],
    "edges": [
      {"from_node": "analyzer", "to_node": "researcher_a"},
      {"from_node": "analyzer", "to_node": "researcher_b"},
      {"from_node": "researcher_a", "to_node": "validator"},
      {"from_node": "researcher_b", "to_node": "validator"},
      {"from_node": "validator", "to_node": "responder"}
    ],
    "entry_node": "analyzer"
  },
  "execution_strategy": "hybrid",
  "strategy_config": {
    "dependency_resolution": "automatic",
    "optimization_level": "balanced"
  }
}
```

**Execution Flow:**
```
                    ┌─→ Researcher A ─┐
User Query → Analyzer ─┤                ├─→ Validator → Responder
                    └─→ Researcher B ─┘
        (auto-parallelized)
```

## Node Configuration

### Basic Node Structure

```json
{
  "id": "unique_node_id",
  "agent_id": "agent_from_agents_json",
  "description": "Human-readable description",
  "input_transform": ".field.path",
  "output_transform": ".result",
  "config_override": {
    "llm_config": {},
    "tools": [],
    "behavior": {}
  }
}
```

### Node Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier for this node in the workflow |
| `agent_id` | Yes | Reference to agent in `configs/agents.json` |
| `description` | No | Human-readable description of node's purpose |
| `input_transform` | No | jq-style expression to transform input |
| `output_transform` | No | jq-style expression to transform output |
| `config_override` | No | Override agent configuration for this node |

### Input/Output Transformations

Transformations use jq-style syntax to extract or reshape data:

```json
{
  "input_transform": ".research_plan.topics[0]",
  "output_transform": ".findings | {summary: .text, confidence: .score}"
}
```

**Common Patterns:**

```javascript
// Extract field
".field_name"

// Extract nested field
".parent.child"

// Extract array element
".array[0]"

// Extract multiple fields
"{topic: .topics[0], strategy: .strategy}"

// Filter and transform
".results | select(.confidence > 0.8) | .text"
```

## Edge Configuration

### Basic Edge Structure

```json
{
  "from_node": "source_node_id",
  "to_node": "target_node_id",
  "condition": ".field == \"value\"",
  "context_strategy": "full",
  "context_config": {},
  "max_iterations": 3
}
```

### Edge Fields

| Field | Required | Description |
|-------|----------|-------------|
| `from_node` | Yes | Source node ID |
| `to_node` | Yes | Target node ID |
| `condition` | No | jq expression for conditional routing |
| `context_strategy` | No | How to pass context (full/summary/selective) |
| `context_config` | No | Configuration for context passing |
| `max_iterations` | No | Max times this edge can be traversed (for cycles) |

### Context Passing Strategies

#### 1. Full Context

Pass complete conversation history.

```json
{
  "context_strategy": "full",
  "context_config": {
    "include_system_messages": false,
    "include_tool_calls": true
  }
}
```

**Use when:**
- Downstream agent needs complete context
- Conversation history is important
- Context size is manageable

#### 2. Summary Context

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

**Use when:**
- Context is too large
- Only key points needed
- Reducing token costs

#### 3. Selective Context

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

**Use when:**
- Only specific data needed
- Minimizing context size
- Structured data passing

### Conditional Routing

Use jq expressions to route based on agent output:

```json
{
  "condition": ".decision.route == \"complex\"",
  "condition": ".confidence > 0.8",
  "condition": ".status == \"approved\" and .score > 0.7"
}
```

## Termination Conditions

Define when workflow execution should stop:

```json
{
  "termination_conditions": [
    {
      "type": "agent_completion",
      "agent_id": "finalizer"
    },
    {
      "type": "max_iterations",
      "value": 10
    },
    {
      "type": "timeout",
      "value": 600
    }
  ]
}
```

### Condition Types

| Type | Description | Configuration |
|------|-------------|---------------|
| `agent_completion` | Stop when specific agent completes | `{"agent_id": "node_id"}` |
| `max_iterations` | Stop after N iterations | `{"value": 10}` |
| `timeout` | Stop after N seconds | `{"value": 600}` |
| `all_nodes_visited` | Stop when all nodes executed | `{}` |
| `custom_condition` | Stop when condition met | `{"expression": ".done == true"}` |

## Choosing the Right Topology

### Decision Matrix

| Requirement | Recommended Topology |
|-------------|---------------------|
| Strict ordering required | Sequential |
| Independent parallel tasks | Tree |
| Conditional routing needed | Graph |
| Iterative refinement | Graph (with cycles) |
| Mixed dependencies | Hybrid |
| Simple workflow | Sequential |
| Complex workflow | Graph or Hybrid |
| Minimize latency | Tree or Hybrid |
| Maximize throughput | Tree or Hybrid |
| Easy debugging | Sequential |

### Performance Considerations

**Sequential:**
- Latency: High (sum of all agents)
- Throughput: Low
- Resource usage: Low
- Complexity: Low

**Tree:**
- Latency: Medium (max of parallel branches)
- Throughput: High
- Resource usage: High
- Complexity: Medium

**Graph:**
- Latency: Variable
- Throughput: Variable
- Resource usage: Variable
- Complexity: High

**Hybrid:**
- Latency: Optimized
- Throughput: Optimized
- Resource usage: Balanced
- Complexity: Medium

## Validation

The system validates topologies before execution:

### Validation Checks

1. **Structural Validation**
   - All nodes have valid agent IDs
   - All edges reference existing nodes
   - Entry node exists
   - No orphaned nodes (unreachable from entry)

2. **Cycle Detection**
   - Cycles have termination conditions
   - Max iterations specified for cyclic edges
   - No infinite loops possible

3. **Dependency Validation**
   - All dependencies can be satisfied
   - No circular dependencies (except explicit cycles)
   - Execution plan can be generated

4. **Configuration Validation**
   - All config overrides are valid
   - Transformations are valid jq expressions
   - Conditions are valid jq expressions

### Validation Errors

Common validation errors and solutions:

**"Unreachable nodes detected"**
- Ensure all nodes have path from entry node
- Check edge connections

**"Cycle without termination condition"**
- Add `max_iterations` to cyclic edges
- Add termination conditions to topology

**"Invalid agent reference"**
- Verify agent_id exists in agents.json
- Check for typos

**"Invalid transformation expression"**
- Test jq expression separately
- Check field names match agent output

## Best Practices

### 1. Start Simple

Begin with sequential topology and add complexity incrementally:

```
Sequential → Tree → Hybrid → Graph
```

### 2. Use Descriptive IDs

```json
// Good
{"id": "technical_researcher", "agent_id": "knowledge_agent"}

// Bad
{"id": "node1", "agent_id": "knowledge_agent"}
```

### 3. Document Your Topology

Add descriptions to nodes and use comments:

```json
{
  "_comment": "This workflow handles customer support queries",
  "nodes": [
    {
      "id": "classifier",
      "description": "Classifies query type and urgency"
    }
  ]
}
```

### 4. Test Incrementally

Test each node independently before connecting:

1. Test individual agents
2. Test simple sequential flow
3. Add parallel branches
4. Add conditional routing
5. Add cycles last

### 5. Monitor Execution

Use observability features to understand execution:

```json
{
  "observability": {
    "tracing": {"enabled": true},
    "metrics": {"track_execution_time": true}
  }
}
```

### 6. Set Resource Limits

Always configure resource limits:

```json
{
  "resource_limits": {
    "max_concurrent_executions": 5,
    "max_execution_time": 600,
    "max_agent_calls": 30
  }
}
```

## Examples

See complete examples in:
- `configs/templates/topologies/` - Topology templates
- `configs/templates/complete_examples/` - Full workflow examples
- `configs/templates/README.md` - Comprehensive guide

## Next Steps

1. Review [Migration Guide](MIGRATION_GUIDE.md) to convert existing workflows
2. Explore [Execution Strategies](EXECUTION_STRATEGIES.md)
3. Configure [Cache Settings](CACHE_CONFIGURATION.md)
4. Set up [Agent Behaviors](AGENT_BEHAVIOR.md)
5. Read [Troubleshooting Guide](TROUBLESHOOTING.md)

