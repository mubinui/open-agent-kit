# Execution Strategies Guide

## Overview

Execution strategies determine how the orchestration service traverses your workflow topology and executes agents. Choosing the right strategy can significantly impact latency, throughput, resource utilization, and cost.

This guide explains each execution strategy, when to use it, and how to configure it for optimal performance.

## Available Strategies

### 1. Sequential Strategy

**Description:** Execute agents one at a time in strict order.

**Execution Model:**
```
Agent 1 → Wait → Agent 2 → Wait → Agent 3 → Wait → Done
```

**Configuration:**

```json
{
  "execution_strategy": "sequential",
  "strategy_config": {
    "wait_for_completion": true,
    "fail_fast": true,
    "timeout_per_agent": 300
  }
}
```

**When to Use:**

✅ **Use Sequential When:**
- Strict ordering is required
- Each step depends on previous results
- Debugging and testing workflows
- Simple workflows with few agents
- Predictable execution flow needed
- Resource constraints (low memory/CPU)

❌ **Avoid Sequential When:**
- Agents are independent
- Minimizing latency is critical
- High throughput needed
- Workflow has parallel branches

**Characteristics:**

| Metric | Value |
|--------|-------|
| Latency | High (sum of all agents) |
| Throughput | Low |
| Resource Usage | Low |
| Complexity | Low |
| Predictability | High |
| Debugging | Easy |

**Performance Example:**

```
3 agents, each taking 10 seconds:
Sequential: 30 seconds total
Parallel: 10 seconds total (3x faster)
```

**Configuration Options:**

```json
{
  "strategy_config": {
    "wait_for_completion": true,    // Wait for each agent to complete
    "fail_fast": true,               // Stop on first error
    "timeout_per_agent": 300,        // Timeout for each agent (seconds)
    "retry_failed_agents": true,     // Retry failed agents
    "max_retries": 3                 // Max retry attempts
  }
}
```

### 2. Parallel Strategy

**Description:** Execute independent agents concurrently.

**Execution Model:**
```
        ┌─→ Agent 2 ─┐
Agent 1 ─┼─→ Agent 3 ─┼─→ Agent 5 → Done
        └─→ Agent 4 ─┘
    (parallel execution)
```

**Configuration:**

```json
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 5,
    "wait_for_all": true,
    "timeout_per_agent": 180,
    "parallel_branches": ["agent2", "agent3", "agent4"]
  }
}
```

**When to Use:**

✅ **Use Parallel When:**
- Agents are independent
- Minimizing latency is critical
- High throughput needed
- Tree topology with parallel branches
- Sufficient resources available
- Agents don't share state

❌ **Avoid Parallel When:**
- Agents have dependencies
- Resource constraints exist
- Debugging complex issues
- Agents share mutable state
- Order matters

**Characteristics:**

| Metric | Value |
|--------|-------|
| Latency | Low (max of parallel agents) |
| Throughput | High |
| Resource Usage | High |
| Complexity | Medium |
| Predictability | Medium |
| Debugging | Harder |

**Performance Example:**

```
3 independent agents, each taking 10 seconds:
Sequential: 30 seconds
Parallel: 10 seconds (3x faster)

Cost: Same token usage, but faster response
```

**Configuration Options:**

```json
{
  "strategy_config": {
    "max_concurrent": 5,              // Max parallel agents
    "wait_for_all": true,             // Wait for all or first completion
    "timeout_per_agent": 180,         // Timeout per agent
    "parallel_branches": ["a", "b"],  // Explicit parallel branches
    "fail_on_any_error": false,       // Continue if one fails
    "aggregate_results": true,        // Combine results
    "resource_pool_size": 10          // Worker pool size
  }
}
```

### 3. Hybrid Strategy

**Description:** Automatically parallelize independent branches while respecting dependencies.

**Execution Model:**
```
        ┌─→ Agent 2 ─┐
Agent 1 ─┤            ├─→ Agent 5 → Agent 6 → Done
        └─→ Agent 3 ─┘
    (auto-parallelized)
```

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

✅ **Use Hybrid When:**
- Complex workflows with mixed dependencies
- Want automatic optimization
- Balance latency and resources
- Production systems
- Workflows evolve over time
- Don't want to manually specify parallelization

❌ **Avoid Hybrid When:**
- Need explicit control over execution
- Very simple workflows (overhead not worth it)
- Debugging complex issues
- Resource usage must be predictable

**Characteristics:**

| Metric | Value |
|--------|-------|
| Latency | Optimized |
| Throughput | Optimized |
| Resource Usage | Balanced |
| Complexity | Medium |
| Predictability | Medium |
| Debugging | Medium |

**How It Works:**

1. **Dependency Analysis:** Analyzes topology to identify dependencies
2. **Stage Generation:** Groups independent agents into stages
3. **Parallel Execution:** Executes each stage in parallel
4. **Sequential Stages:** Waits for stage completion before next

**Example:**

```json
{
  "nodes": ["A", "B", "C", "D", "E"],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "A", "to": "C"},
    {"from": "B", "to": "D"},
    {"from": "C", "to": "D"},
    {"from": "D", "to": "E"}
  ]
}

// Hybrid strategy creates stages:
Stage 1: [A]           // Entry node
Stage 2: [B, C]        // Parallel (both depend only on A)
Stage 3: [D]           // Sequential (depends on B and C)
Stage 4: [E]           // Sequential (depends on D)
```

**Configuration Options:**

```json
{
  "strategy_config": {
    "max_concurrent": 10,                    // Max parallel agents
    "dependency_resolution": "automatic",    // or "manual"
    "optimization_level": "balanced",        // "latency", "throughput", "balanced"
    "cycle_detection": true,                 // Detect and handle cycles
    "max_cycle_iterations": 3,               // Max iterations for cycles
    "stage_timeout": 300,                    // Timeout per stage
    "prefer_parallelization": true           // Favor parallel over sequential
  }
}
```

**Optimization Levels:**

```json
// Latency-optimized: Maximize parallelization
{
  "optimization_level": "latency",
  "max_concurrent": 20,
  "prefer_parallelization": true
}

// Throughput-optimized: Balance parallel and sequential
{
  "optimization_level": "throughput",
  "max_concurrent": 10,
  "prefer_parallelization": false
}

// Balanced: Middle ground
{
  "optimization_level": "balanced",
  "max_concurrent": 10,
  "prefer_parallelization": true
}
```

## Strategy Comparison

### Performance Comparison

| Strategy | Latency | Throughput | Resources | Complexity |
|----------|---------|------------|-----------|------------|
| Sequential | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Parallel | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Hybrid | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### Use Case Matrix

| Use Case | Recommended Strategy |
|----------|---------------------|
| Simple chatbot | Sequential |
| Multi-step analysis | Sequential |
| Parallel research | Parallel |
| Tree topology | Parallel or Hybrid |
| Graph topology | Hybrid |
| Production system | Hybrid |
| Development/Testing | Sequential |
| High-traffic API | Parallel or Hybrid |
| Resource-constrained | Sequential |
| Complex workflow | Hybrid |

### Cost Comparison

```
Scenario: 3 agents, 1000 tokens each, $0.01 per 1K tokens

Sequential:
- Time: 30 seconds
- Cost: $0.03 (3 agents × 1000 tokens × $0.01)
- Requests/hour: 120

Parallel:
- Time: 10 seconds (3x faster)
- Cost: $0.03 (same token usage)
- Requests/hour: 360 (3x more)

Hybrid:
- Time: 15 seconds (2x faster)
- Cost: $0.03 (same token usage)
- Requests/hour: 240 (2x more)

Conclusion: Parallel/Hybrid reduce latency without increasing cost
```

## Advanced Configuration

### Resource Limits

Control resource usage across all strategies:

```json
{
  "resource_limits": {
    "max_concurrent_executions": 5,    // Max workflows running
    "max_execution_time": 600,         // Max workflow time
    "max_agent_calls": 30,             // Max agents per workflow
    "max_context_size": 100000,        // Max context tokens
    "max_memory_mb": 1024              // Max memory per workflow
  }
}
```

### Retry Configuration

Configure retry behavior:

```json
{
  "retry_strategy": {
    "max_retries": 3,
    "backoff_type": "exponential",     // "fixed", "exponential", "linear"
    "backoff_factor": 2.0,
    "initial_delay": 1.0,
    "max_delay": 60.0,
    "retry_on": [
      "timeout",
      "rate_limit",
      "temporary_failure"
    ],
    "dont_retry_on": [
      "validation_error",
      "authentication_error"
    ]
  }
}
```

### Timeout Configuration

Set timeouts at multiple levels:

```json
{
  "timeouts": {
    "workflow_timeout": 600,           // Total workflow timeout
    "stage_timeout": 300,              // Timeout per stage (hybrid)
    "agent_timeout": 120,              // Timeout per agent
    "llm_timeout": 60                  // Timeout per LLM call
  }
}
```

### Error Handling

Configure error handling behavior:

```json
{
  "error_handling": {
    "fail_fast": true,                 // Stop on first error
    "continue_on_error": false,        // Continue despite errors
    "collect_partial_results": true,   // Return partial results
    "error_aggregation": "first",      // "first", "all", "last"
    "fallback_strategy": "sequential"  // Fallback if parallel fails
  }
}
```

## Monitoring and Observability

### Execution Metrics

Track execution performance:

```json
{
  "observability": {
    "metrics": {
      "track_execution_time": true,
      "track_agent_time": true,
      "track_stage_time": true,
      "track_parallelization": true,
      "track_resource_usage": true
    }
  }
}
```

### Tracing

Enable distributed tracing:

```json
{
  "observability": {
    "tracing": {
      "enabled": true,
      "trace_all_agents": true,
      "trace_llm_calls": true,
      "include_context": false
    }
  }
}
```

### Logging

Configure logging:

```json
{
  "observability": {
    "logging": {
      "level": "INFO",
      "include_prompts": false,
      "include_responses": true,
      "include_timing": true,
      "include_strategy_decisions": true
    }
  }
}
```

## Performance Tuning

### Optimizing Sequential Strategy

```json
{
  "execution_strategy": "sequential",
  "strategy_config": {
    "fail_fast": true,              // Stop early on errors
    "timeout_per_agent": 60,        // Shorter timeouts
    "skip_optional_agents": true    // Skip non-critical agents
  },
  "cache_config": {
    "llm_response": {
      "enabled": true,              // Enable caching
      "ttl": 7200
    }
  }
}
```

### Optimizing Parallel Strategy

```json
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 10,           // Increase parallelism
    "wait_for_all": false,          // Don't wait for slow agents
    "timeout_per_agent": 30,        // Aggressive timeouts
    "fail_on_any_error": false      // Continue on errors
  },
  "resource_limits": {
    "max_concurrent_executions": 10  // Allow more workflows
  }
}
```

### Optimizing Hybrid Strategy

```json
{
  "execution_strategy": "hybrid",
  "strategy_config": {
    "optimization_level": "latency",  // Prioritize speed
    "max_concurrent": 15,             // High parallelism
    "prefer_parallelization": true,   // Favor parallel
    "stage_timeout": 120              // Reasonable stage timeout
  }
}
```

## Common Patterns

### Pattern 1: Fast Response Chatbot

```json
{
  "execution_strategy": "sequential",
  "strategy_config": {
    "timeout_per_agent": 30,
    "fail_fast": true
  },
  "cache_config": {
    "llm_response": {"enabled": true, "ttl": 3600}
  }
}
```

### Pattern 2: Comprehensive Research

```json
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 5,
    "wait_for_all": true,
    "timeout_per_agent": 180
  }
}
```

### Pattern 3: Adaptive Workflow

```json
{
  "execution_strategy": "hybrid",
  "strategy_config": {
    "optimization_level": "balanced",
    "max_concurrent": 10,
    "cycle_detection": true
  }
}
```

### Pattern 4: High-Throughput API

```json
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 20,
    "wait_for_all": false,
    "fail_on_any_error": false
  },
  "resource_limits": {
    "max_concurrent_executions": 50
  }
}
```

## Troubleshooting

### Issue: Slow Execution

**Symptoms:** Workflow takes longer than expected

**Diagnosis:**
```bash
# Check execution metrics
curl http://localhost:8000/api/v1/metrics | grep execution_time
```

**Solutions:**
1. Switch to parallel or hybrid strategy
2. Increase `max_concurrent`
3. Reduce `timeout_per_agent`
4. Enable caching
5. Optimize agent prompts

### Issue: High Resource Usage

**Symptoms:** High CPU/memory usage, system slowdown

**Diagnosis:**
```bash
# Check resource metrics
curl http://localhost:8000/api/v1/metrics | grep resource_usage
```

**Solutions:**
1. Reduce `max_concurrent`
2. Lower `max_concurrent_executions`
3. Switch to sequential strategy
4. Add resource limits
5. Implement request queuing

### Issue: Inconsistent Results

**Symptoms:** Different results on repeated runs

**Diagnosis:**
- Check if parallel execution causes race conditions
- Verify agents don't share mutable state

**Solutions:**
1. Switch to sequential strategy
2. Use proper synchronization
3. Make agents stateless
4. Use selective context passing

### Issue: Timeouts

**Symptoms:** Agents timing out frequently

**Diagnosis:**
```bash
# Check timeout metrics
curl http://localhost:8000/api/v1/metrics | grep timeout
```

**Solutions:**
1. Increase timeout values
2. Optimize agent prompts
3. Use faster models
4. Enable caching
5. Split complex agents

## Best Practices

### 1. Start Simple

Begin with sequential, then optimize:

```
Sequential → Parallel (if independent) → Hybrid (if complex)
```

### 2. Measure Performance

Always measure before optimizing:

```bash
# Benchmark different strategies
for strategy in sequential parallel hybrid; do
  echo "Testing $strategy..."
  time curl -X POST http://localhost:8000/api/v1/sessions \
    -d "{\"workflow_id\": \"test_$strategy\"}"
done
```

### 3. Set Appropriate Limits

Don't over-parallelize:

```json
{
  "max_concurrent": 10,  // Good: Reasonable limit
  "max_concurrent": 100  // Bad: Too high, resource exhaustion
}
```

### 4. Use Caching

Enable caching for expensive operations:

```json
{
  "cache_config": {
    "llm_response": {"enabled": true, "ttl": 7200}
  }
}
```

### 5. Monitor in Production

Track key metrics:
- Execution time per strategy
- Resource usage
- Error rates
- Cache hit rates
- Parallelization efficiency

## Next Steps

1. Review [Topology Configuration](TOPOLOGY_CONFIGURATION.md)
2. Configure [Cache Settings](CACHE_CONFIGURATION.md)
3. Set up [Agent Behaviors](AGENT_BEHAVIOR.md)
4. Read [Troubleshooting Guide](TROUBLESHOOTING.md)
5. Explore [Complete Examples](../configs/templates/complete_examples/)

