# Cache Configuration Guide

## Overview

The orchestration service provides a sophisticated multi-layer caching system that can significantly reduce costs and improve response times. This guide explains how to configure caching at different levels and optimize for your use case.

## Why Caching Matters

### Cost Savings

```
Example: 1000 requests/day, 2000 tokens per request

Without caching:
- API calls: 1000
- Tokens: 2,000,000
- Cost: $20/day ($0.01 per 1K tokens)

With 50% cache hit rate:
- API calls: 500
- Tokens: 1,000,000
- Cost: $10/day
- Savings: $10/day = $300/month
```

### Performance Improvement

```
Without caching:
- LLM API call: 2-5 seconds
- Total response time: 2-5 seconds

With caching:
- Cache lookup: 10-50ms
- Total response time: 10-50ms
- Speedup: 40-500x faster
```

## Cache Architecture

### Cache Layers

The system provides four independent cache layers:

```
┌─────────────────────────────────────────┐
│         Application Layer               │
└─────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────────────┐
│  LLM   │  │Embedding│  │ Session │  │Agent Result│
│Response│  │  Cache  │  │  Cache  │  │   Cache    │
└────────┘  └─────────┘  └─────────┘  └────────────┘
    │             │             │             │
└───────────────────┴─────────────────────────┘
                  │
         ┌────────▼────────┐
         │  Redis Backend  │
         └─────────────────┘
```

### 1. LLM Response Cache

**Purpose:** Cache LLM API responses to avoid redundant calls.

**Cache Key:** Hash of (model, prompt, temperature, max_tokens)

**Use Cases:**
- Repeated queries
- Common questions
- Deterministic responses (low temperature)

**Configuration:**

```json
{
  "llm_response": {
    "enabled": true,
    "ttl": 3600,              // 1 hour
    "max_size": 10000,        // Max cached items
    "eviction_policy": "LRU"  // Least Recently Used
  }
}
```

### 2. Embedding Cache

**Purpose:** Cache vector embeddings for RAG operations.

**Cache Key:** Hash of (text, embedding_model)

**Use Cases:**
- Document embeddings
- Query embeddings
- Semantic search

**Configuration:**

```json
{
  "embedding": {
    "enabled": true,
    "ttl": 86400,             // 24 hours
    "max_size": 50000,
    "eviction_policy": "LFU"  // Least Frequently Used
  }
}
```

### 3. Session Cache

**Purpose:** Cache session state and conversation history.

**Cache Key:** Session ID

**Use Cases:**
- Active sessions
- Conversation history
- User context

**Configuration:**

```json
{
  "session": {
    "enabled": true,
    "ttl": 1800,              // 30 minutes
    "eviction_policy": "TTL"  // Time To Live
  }
}
```

### 4. Agent Result Cache

**Purpose:** Cache complete agent execution results.

**Cache Key:** Hash of (agent_id, input, configuration)

**Use Cases:**
- Expensive agent operations
- Deterministic agents
- Batch processing

**Configuration:**

```json
{
  "agent_result": {
    "enabled": false,         // Disabled by default
    "ttl": 600,               // 10 minutes
    "max_size": 5000,
    "eviction_policy": "LRU"
  }
}
```

## Configuration Hierarchy

### Multi-Layer Configuration

The cache system uses a hierarchical configuration model:

```
Global Config (configs/cache.json)
    ↓
Workflow Config (in workflow definition)
    ↓
Agent Config (in agent definition)
    ↓
Runtime Config (API request)
```

**Override Rules:**
- Lower layers override higher layers
- Only specified fields are overridden
- Unspecified fields inherit from parent

### Example Hierarchy

**Global Config** (`configs/cache.json`):

```json
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
```

**Workflow Override** (in workflow config):

```json
{
  "cache_config": {
    "llm_response": {
      "ttl": 7200  // Override: 2 hours instead of 1
    }
  }
}
```

**Agent Override** (in agent config):

```json
{
  "cache_override": {
    "llm_response": {
      "enabled": false  // Override: Disable for this agent
    }
  }
}
```

**Effective Config:**
```json
{
  "llm_response": {
    "enabled": false,      // From agent override
    "ttl": 7200,           // From workflow override
    "eviction_policy": "LRU"  // From global config
  }
}
```

## Global Configuration

### File Location

`configs/cache.json`

### Complete Example

```json
{
  "global_enabled": true,
  "layers": {
    "llm_response": {
      "enabled": true,
      "ttl": 3600,
      "max_size": 10000,
      "eviction_policy": "LRU"
    },
    "embedding": {
      "enabled": true,
      "ttl": 86400,
      "max_size": 50000,
      "eviction_policy": "LFU"
    },
    "session": {
      "enabled": true,
      "ttl": 1800,
      "max_size": null,
      "eviction_policy": "TTL"
    },
    "agent_result": {
      "enabled": false,
      "ttl": 600,
      "max_size": 5000,
      "eviction_policy": "LRU"
    }
  },
  "workflow_overrides": {},
  "agent_overrides": {}
}
```

### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `global_enabled` | boolean | Master switch for all caching |
| `layers` | object | Configuration for each cache layer |
| `workflow_overrides` | object | Per-workflow overrides |
| `agent_overrides` | object | Per-agent overrides |

### Layer Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Enable/disable this layer |
| `ttl` | integer | Time to live in seconds |
| `max_size` | integer\|null | Max items (null = unlimited) |
| `eviction_policy` | string | LRU, LFU, or TTL |

## Workflow-Level Configuration

### In Workflow Definition

```json
{
  "id": "my_workflow",
  "topology": {...},
  "cache_config": {
    "llm_response": {
      "enabled": true,
      "ttl": 7200
    },
    "agent_result": {
      "enabled": true,
      "ttl": 3600
    }
  }
}
```

### Use Cases

**Real-time Chat (Disable Caching):**

```json
{
  "id": "realtime_chat",
  "cache_config": {
    "llm_response": {
      "enabled": false
    }
  }
}
```

**Batch Processing (Extended Caching):**

```json
{
  "id": "batch_processing",
  "cache_config": {
    "llm_response": {
      "enabled": true,
      "ttl": 86400  // 24 hours
    }
  }
}
```

**Research Workflow (Selective Caching):**

```json
{
  "id": "research_workflow",
  "cache_config": {
    "llm_response": {
      "enabled": true,
      "ttl": 14400  // 4 hours
    },
    "embedding": {
      "enabled": true,
      "ttl": 86400  // 24 hours
    },
    "agent_result": {
      "enabled": true,
      "ttl": 7200  // 2 hours
    }
  }
}
```

## Agent-Level Configuration

### In Agent Definition

```json
{
  "id": "reasoning_agent",
  "type": "conversable",
  "cache_override": {
    "llm_response": {
      "enabled": true,
      "ttl": 7200
    }
  }
}
```

### Use Cases

**Expensive Agent (Long Cache):**

```json
{
  "id": "expensive_analyzer",
  "cache_override": {
    "llm_response": {
      "enabled": true,
      "ttl": 14400  // 4 hours
    },
    "agent_result": {
      "enabled": true,
      "ttl": 7200  // 2 hours
    }
  }
}
```

**Creative Agent (No Cache):**

```json
{
  "id": "creative_writer",
  "cache_override": {
    "llm_response": {
      "enabled": false  // Always generate fresh content
    }
  }
}
```

**Deterministic Agent (Long Cache):**

```json
{
  "id": "code_validator",
  "llm_config": {
    "temperature": 0.0  // Deterministic
  },
  "cache_override": {
    "llm_response": {
      "enabled": true,
      "ttl": 86400  // 24 hours
    }
  }
}
```

## Eviction Policies

### LRU (Least Recently Used)

**Description:** Evicts items that haven't been accessed recently.

**Best For:**
- General-purpose caching
- Temporal locality (recent items likely to be reused)
- LLM response cache

**Configuration:**

```json
{
  "eviction_policy": "LRU",
  "max_size": 10000
}
```

**Behavior:**
```
Cache full → Evict least recently accessed item
Access item → Move to front of queue
```

### LFU (Least Frequently Used)

**Description:** Evicts items that are accessed least often.

**Best For:**
- Long-term caching
- Frequency-based access patterns
- Embedding cache

**Configuration:**

```json
{
  "eviction_policy": "LFU",
  "max_size": 50000
}
```

**Behavior:**
```
Cache full → Evict item with lowest access count
Access item → Increment access counter
```

### TTL (Time To Live)

**Description:** Evicts items after a fixed time period.

**Best For:**
- Time-sensitive data
- Session cache
- Guaranteed freshness

**Configuration:**

```json
{
  "eviction_policy": "TTL",
  "ttl": 1800  // 30 minutes
}
```

**Behavior:**
```
Item added → Set expiration time
Time expired → Automatically evict
```

## Cache Key Generation

### LLM Response Cache

```python
cache_key = hash(
    model_name,
    prompt,
    temperature,
    max_tokens,
    top_p,
    frequency_penalty,
    presence_penalty
)
```

**Important:** Small changes in parameters create different cache keys.

### Embedding Cache

```python
cache_key = hash(
    text,
    embedding_model,
    embedding_dimensions
)
```

### Agent Result Cache

```python
cache_key = hash(
    agent_id,
    input_message,
    agent_config,
    tools_available
)
```

## Monitoring Cache Performance

### Cache Metrics

Track these metrics to optimize caching:

```json
{
  "observability": {
    "metrics": {
      "track_cache_hits": true,
      "track_cache_misses": true,
      "track_cache_size": true,
      "track_evictions": true
    }
  }
}
```

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Hit Rate | % of requests served from cache | > 50% |
| Miss Rate | % of requests requiring API call | < 50% |
| Eviction Rate | Items evicted per minute | Low |
| Average Latency | Cache lookup time | < 50ms |
| Memory Usage | Redis memory consumption | < 80% |

### Checking Metrics

```bash
# Get cache metrics
curl http://localhost:8000/api/v1/metrics | grep cache

# Example output:
cache_hits_total{layer="llm_response"} 1250
cache_misses_total{layer="llm_response"} 750
cache_hit_rate{layer="llm_response"} 0.625
cache_size{layer="llm_response"} 8432
```

### Calculating Hit Rate

```
Hit Rate = Hits / (Hits + Misses)

Example:
Hits: 1250
Misses: 750
Hit Rate: 1250 / (1250 + 750) = 0.625 = 62.5%
```

## Optimization Strategies

### 1. Tune TTL Values

**Too Short:**
- Low hit rate
- Frequent API calls
- Higher costs

**Too Long:**
- Stale data
- Memory pressure
- Evictions

**Optimal TTL by Use Case:**

```json
{
  "chatbot": {
    "llm_response": {"ttl": 3600}  // 1 hour
  },
  "research": {
    "llm_response": {"ttl": 14400}  // 4 hours
  },
  "batch_processing": {
    "llm_response": {"ttl": 86400}  // 24 hours
  },
  "real_time": {
    "llm_response": {"enabled": false}  // No cache
  }
}
```

### 2. Adjust Cache Size

Monitor memory usage and eviction rate:

```bash
# Check Redis memory
redis-cli INFO memory

# If eviction rate is high, increase max_size
{
  "max_size": 20000  // Increased from 10000
}
```

### 3. Choose Right Eviction Policy

```json
{
  "llm_response": {
    "eviction_policy": "LRU"  // Recent queries likely to repeat
  },
  "embedding": {
    "eviction_policy": "LFU"  // Popular documents accessed often
  },
  "session": {
    "eviction_policy": "TTL"  // Time-based expiration
  }
}
```

### 4. Selective Caching

Enable caching only where beneficial:

```json
{
  "workflows": {
    "chatbot": {
      "cache_config": {
        "llm_response": {"enabled": true}
      }
    },
    "creative_writing": {
      "cache_config": {
        "llm_response": {"enabled": false}  // Always fresh
      }
    }
  }
}
```

### 5. Temperature-Based Caching

```json
{
  "agents": {
    "deterministic_agent": {
      "llm_config": {"temperature": 0.0},
      "cache_override": {
        "llm_response": {
          "enabled": true,
          "ttl": 86400  // Long cache for deterministic
        }
      }
    },
    "creative_agent": {
      "llm_config": {"temperature": 1.0},
      "cache_override": {
        "llm_response": {
          "enabled": false  // No cache for creative
        }
      }
    }
  }
}
```

## Common Patterns

### Pattern 1: Development Environment

```json
{
  "global_enabled": true,
  "layers": {
    "llm_response": {
      "enabled": true,
      "ttl": 86400,  // Long cache for development
      "eviction_policy": "LRU"
    }
  }
}
```

### Pattern 2: Production Environment

```json
{
  "global_enabled": true,
  "layers": {
    "llm_response": {
      "enabled": true,
      "ttl": 3600,  // Shorter cache for freshness
      "max_size": 50000,
      "eviction_policy": "LRU"
    },
    "embedding": {
      "enabled": true,
      "ttl": 86400,
      "max_size": 100000,
      "eviction_policy": "LFU"
    }
  }
}
```

### Pattern 3: Cost-Optimized

```json
{
  "global_enabled": true,
  "layers": {
    "llm_response": {
      "enabled": true,
      "ttl": 14400,  // 4 hours
      "max_size": 100000,  // Large cache
      "eviction_policy": "LFU"  // Keep popular items
    }
  }
}
```

### Pattern 4: Real-Time System

```json
{
  "global_enabled": false,  // Disable all caching
  "layers": {
    "session": {
      "enabled": true,  // Only cache sessions
      "ttl": 1800
    }
  }
}
```

## Troubleshooting

### Issue: Low Hit Rate

**Symptoms:** Cache hit rate < 30%

**Diagnosis:**
```bash
curl http://localhost:8000/api/v1/metrics | grep cache_hit_rate
```

**Possible Causes:**
1. TTL too short
2. High variability in queries
3. Temperature too high (non-deterministic)
4. Cache size too small (evictions)

**Solutions:**
1. Increase TTL
2. Use lower temperature for deterministic agents
3. Increase max_size
4. Analyze query patterns

### Issue: High Memory Usage

**Symptoms:** Redis memory > 80%

**Diagnosis:**
```bash
redis-cli INFO memory
```

**Solutions:**
1. Reduce max_size
2. Reduce TTL
3. Use more aggressive eviction policy
4. Add more Redis memory
5. Disable less important cache layers

### Issue: Stale Data

**Symptoms:** Cached responses are outdated

**Solutions:**
1. Reduce TTL
2. Implement cache invalidation
3. Disable cache for time-sensitive data
4. Use TTL eviction policy

### Issue: Cache Misses

**Symptoms:** High cache miss rate despite caching enabled

**Diagnosis:**
```bash
# Check cache configuration
curl http://localhost:8000/api/v1/configs/cache
```

**Possible Causes:**
1. Cache disabled at some level
2. Different parameters creating different keys
3. Cache size too small
4. TTL too short

**Solutions:**
1. Verify cache enabled at all levels
2. Standardize parameters
3. Increase cache size
4. Increase TTL

## Best Practices

### 1. Start with Defaults

Use recommended defaults, then optimize:

```json
{
  "llm_response": {"enabled": true, "ttl": 3600},
  "embedding": {"enabled": true, "ttl": 86400},
  "session": {"enabled": true, "ttl": 1800},
  "agent_result": {"enabled": false}
}
```

### 2. Monitor and Adjust

Track metrics and adjust based on data:

```bash
# Weekly review
curl http://localhost:8000/api/v1/metrics | grep cache > cache_metrics.txt
# Analyze and adjust TTL/size
```

### 3. Use Hierarchy Wisely

```
Global: Conservative defaults
Workflow: Optimize per use case
Agent: Fine-tune expensive agents
```

### 4. Document Overrides

```json
{
  "_cache_notes": {
    "reasoning_agent": "Long cache due to expensive model",
    "creative_agent": "No cache to ensure variety"
  }
}
```

### 5. Test Cache Impact

```bash
# Test with cache
time curl -X POST http://localhost:8000/api/v1/sessions \
  -d '{"workflow_id": "test", "message": "test"}'

# Test without cache
time curl -X POST http://localhost:8000/api/v1/sessions \
  -d '{"workflow_id": "test_no_cache", "message": "test"}'
```

## Next Steps

1. Review [Topology Configuration](TOPOLOGY_CONFIGURATION.md)
2. Configure [Execution Strategies](EXECUTION_STRATEGIES.md)
3. Set up [Agent Behaviors](AGENT_BEHAVIOR.md)
4. Read [Troubleshooting Guide](TROUBLESHOOTING.md)
5. Explore [Complete Examples](../configs/templates/complete_examples/)

