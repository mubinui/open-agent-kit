# Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues with the industry-grade orchestration service. Issues are organized by category with symptoms, diagnosis steps, and solutions.

## Quick Diagnostic Commands

```bash
# Check service health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/api/v1/metrics

# Check logs
curl http://localhost:8000/api/v1/logs?level=ERROR&limit=50

# Validate configuration
curl -X POST http://localhost:8000/api/v1/configs/validate

# Check Redis connection
redis-cli PING

# Check MongoDB connection
mongosh --eval "db.adminCommand('ping')"
```

## Topology Configuration Issues

### Issue: "Unreachable nodes detected"

**Symptoms:**
- Topology validation fails
- Error message mentions unreachable nodes
- Workflow won't deploy

**Diagnosis:**
```bash
# Validate topology
curl -X POST http://localhost:8000/api/v1/workflows/validate \
  -H "Content-Type: application/json" \
  -d @my_workflow.json
```

**Causes:**
1. Node has no incoming edges
2. No path from entry node to some nodes
3. Disconnected subgraph

**Solutions:**

```json
// Bad: Node C is unreachable
{
  "nodes": ["A", "B", "C"],
  "edges": [
    {"from": "A", "to": "B"}
  ],
  "entry_node": "A"
}

// Good: All nodes reachable
{
  "nodes": ["A", "B", "C"],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "C"}
  ],
  "entry_node": "A"
}
```

### Issue: "Cycle detected without termination condition"

**Symptoms:**
- Topology validation fails
- Error mentions cycles
- Workflow has feedback loops

**Diagnosis:**
```bash
# Check for cycles
curl -X POST http://localhost:8000/api/v1/workflows/analyze \
  -d '{"workflow_id": "my_workflow"}'
```

**Causes:**
1. Cyclic edges without max_iterations
2. Missing termination conditions
3. Infinite loop possible

**Solutions:**

```json
// Bad: Cycle without termination
{
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "A"}
  ]
}

// Good: Cycle with termination
{
  "edges": [
    {"from": "A", "to": "B"},
    {
      "from": "B",
      "to": "A",
      "max_iterations": 3
    }
  ],
  "termination_conditions": [
    {"type": "max_iterations", "value": 10}
  ]
}
```

### Issue: "Invalid agent reference"

**Symptoms:**
- Validation error about missing agent
- Agent ID not found
- Workflow won't deploy

**Diagnosis:**
```bash
# List available agents
curl http://localhost:8000/api/v1/agents

# Check specific agent
curl http://localhost:8000/api/v1/agents/my_agent_id
```

**Causes:**
1. Typo in agent_id
2. Agent not defined in agents.json
3. Agent deleted but still referenced

**Solutions:**

```json
// Check agent exists
{
  "nodes": [
    {
      "id": "my_node",
      "agent_id": "reasoning_agent"  // Must exist in agents.json
    }
  ]
}

// Verify in agents.json
{
  "agents": [
    {
      "id": "reasoning_agent",  // Must match
      ...
    }
  ]
}
```

### Issue: "Invalid transformation expression"

**Symptoms:**
- Error about jq expression
- Transformation fails
- Data not passed correctly

**Diagnosis:**
```bash
# Test jq expression
echo '{"result": "test", "confidence": 0.8}' | jq '.result'

# Test in workflow
curl -X POST http://localhost:8000/api/v1/workflows/test-transform \
  -d '{"expression": ".result", "data": {...}}'
```

**Causes:**
1. Invalid jq syntax
2. Field doesn't exist
3. Wrong data type

**Solutions:**

```json
// Bad: Invalid syntax
{
  "input_transform": ".result.field[0"  // Missing ]
}

// Good: Valid syntax
{
  "input_transform": ".result.field[0]"
}

// Test transformations
{
  "input_transform": ".research_plan.topics[0]",
  "output_transform": ".findings | {summary: .text, score: .confidence}"
}
```

## Execution Issues

### Issue: Workflow Timeout

**Symptoms:**
- Workflow exceeds timeout
- Partial results returned
- Timeout error in logs

**Diagnosis:**
```bash
# Check execution time
curl http://localhost:8000/api/v1/metrics | grep execution_time

# Check timeout configuration
curl http://localhost:8000/api/v1/workflows/my_workflow | jq '.resource_limits'
```

**Causes:**
1. Timeout too short
2. Slow agents
3. Too many agents
4. Network issues

**Solutions:**

```json
// Increase timeouts
{
  "resource_limits": {
    "max_execution_time": 600  // Increase from 300
  },
  "strategy_config": {
    "timeout_per_agent": 180  // Increase from 60
  }
}

// Optimize execution
{
  "execution_strategy": "parallel",  // Use parallel instead of sequential
  "cache_config": {
    "llm_response": {"enabled": true}  // Enable caching
  }
}
```

### Issue: Slow Execution

**Symptoms:**
- Workflow takes too long
- High latency
- Poor user experience

**Diagnosis:**
```bash
# Check execution breakdown
curl http://localhost:8000/api/v1/sessions/SESSION_ID/metrics

# Check agent times
curl http://localhost:8000/api/v1/metrics | grep agent_execution_time
```

**Causes:**
1. Sequential execution of independent agents
2. Cache disabled
3. Slow models
4. Large context

**Solutions:**

```json
// Use parallel execution
{
  "execution_strategy": "parallel",
  "strategy_config": {
    "max_concurrent": 5
  }
}

// Enable caching
{
  "cache_config": {
    "llm_response": {
      "enabled": true,
      "ttl": 7200
    }
  }
}

// Use faster models
{
  "llm_config": {
    "model": "openai/gpt-3.5-turbo"  // Faster than gpt-4
  }
}

// Reduce context
{
  "context_strategy": "selective",
  "context_config": {
    "fields": ["result"]  // Only pass essential fields
  }
}
```

### Issue: High Resource Usage

**Symptoms:**
- High CPU/memory
- System slowdown
- Out of memory errors

**Diagnosis:**
```bash
# Check resource usage
curl http://localhost:8000/api/v1/metrics | grep resource

# Check concurrent executions
curl http://localhost:8000/api/v1/metrics | grep concurrent_executions

# Check memory
free -h
```

**Causes:**
1. Too many concurrent workflows
2. Too many parallel agents
3. Large context sizes
4. Memory leaks

**Solutions:**

```json
// Reduce concurrency
{
  "resource_limits": {
    "max_concurrent_executions": 3,  // Reduce from 10
    "max_context_size": 50000  // Reduce from 100000
  },
  "strategy_config": {
    "max_concurrent": 3  // Reduce from 10
  }
}

// Implement queuing
{
  "queue_config": {
    "enabled": true,
    "max_queue_size": 100,
    "queue_timeout": 300
  }
}
```

### Issue: Agent Failures

**Symptoms:**
- Agent execution fails
- Error in agent output
- Workflow stops

**Diagnosis:**
```bash
# Check agent logs
curl http://localhost:8000/api/v1/logs?agent=my_agent&level=ERROR

# Check agent status
curl http://localhost:8000/api/v1/agents/my_agent/status

# Test agent independently
curl -X POST http://localhost:8000/api/v1/agents/test \
  -d '{"agent_id": "my_agent", "message": "test"}'
```

**Causes:**
1. Invalid agent configuration
2. LLM API errors
3. Tool failures
4. Validation failures

**Solutions:**

```json
// Add retry logic
{
  "retry_strategy": {
    "max_retries": 3,
    "backoff_type": "exponential",
    "retry_on": ["timeout", "rate_limit", "temporary_failure"]
  }
}

// Add error handling
{
  "error_handling": {
    "continue_on_error": true,
    "collect_partial_results": true,
    "fallback_strategy": "sequential"
  }
}

// Fix agent configuration
{
  "llm_config": {
    "timeout": 120,  // Increase timeout
    "max_tokens": 2000  // Ensure sufficient tokens
  }
}
```

## Cache Issues

### Issue: Low Cache Hit Rate

**Symptoms:**
- Cache hit rate < 30%
- High API costs
- Slow responses

**Diagnosis:**
```bash
# Check cache metrics
curl http://localhost:8000/api/v1/metrics | grep cache_hit_rate

# Check cache configuration
curl http://localhost:8000/api/v1/configs/cache
```

**Causes:**
1. TTL too short
2. High query variability
3. High temperature (non-deterministic)
4. Cache size too small

**Solutions:**

```json
// Increase TTL
{
  "cache_config": {
    "llm_response": {
      "ttl": 7200  // Increase from 3600
    }
  }
}

// Lower temperature
{
  "llm_config": {
    "temperature": 0.3  // More deterministic
  }
}

// Increase cache size
{
  "cache_config": {
    "llm_response": {
      "max_size": 20000  // Increase from 10000
    }
  }
}
```

### Issue: Stale Cached Data

**Symptoms:**
- Outdated responses
- Incorrect information
- Data doesn't reflect recent changes

**Diagnosis:**
```bash
# Check cache TTL
curl http://localhost:8000/api/v1/configs/cache | jq '.layers.llm_response.ttl'

# Check cache age
redis-cli TTL "cache:llm_response:KEY"
```

**Causes:**
1. TTL too long
2. No cache invalidation
3. Static data changed

**Solutions:**

```json
// Reduce TTL
{
  "cache_config": {
    "llm_response": {
      "ttl": 1800  // Reduce from 7200
    }
  }
}

// Disable cache for time-sensitive data
{
  "cache_config": {
    "llm_response": {
      "enabled": false
    }
  }
}

// Manual cache invalidation
curl -X DELETE http://localhost:8000/api/v1/cache/invalidate \
  -d '{"pattern": "workflow:my_workflow:*"}'
```

### Issue: High Memory Usage (Redis)

**Symptoms:**
- Redis memory > 80%
- Evictions increasing
- Cache performance degrading

**Diagnosis:**
```bash
# Check Redis memory
redis-cli INFO memory

# Check eviction stats
redis-cli INFO stats | grep evicted
```

**Causes:**
1. Cache size too large
2. TTL too long
3. Too many cache layers enabled

**Solutions:**

```json
// Reduce cache size
{
  "cache_config": {
    "llm_response": {
      "max_size": 5000  // Reduce from 10000
    }
  }
}

// Reduce TTL
{
  "cache_config": {
    "llm_response": {
      "ttl": 1800  // Reduce from 7200
    }
  }
}

// Disable less important layers
{
  "cache_config": {
    "agent_result": {
      "enabled": false
    }
  }
}
```

## Configuration Issues

### Issue: Configuration Not Loading

**Symptoms:**
- Changes not applied
- Old configuration still active
- Validation passes but no effect

**Diagnosis:**
```bash
# Check configuration reload
curl http://localhost:8000/api/v1/configs/reload

# Check active configuration
curl http://localhost:8000/api/v1/configs/active

# Check configuration file
cat configs/workflows.json | jq '.'
```

**Causes:**
1. File not saved
2. JSON syntax error
3. Hot reload disabled
4. Service not restarted

**Solutions:**

```bash
# Validate JSON
cat configs/workflows.json | jq '.' > /dev/null && echo "Valid JSON"

# Reload configuration
curl -X POST http://localhost:8000/api/v1/configs/reload

# Restart service
docker-compose restart orchestration-service
```

### Issue: Configuration Validation Fails

**Symptoms:**
- Validation error on deploy
- Configuration rejected
- Detailed error message

**Diagnosis:**
```bash
# Validate configuration
curl -X POST http://localhost:8000/api/v1/configs/validate \
  -H "Content-Type: application/json" \
  -d @my_config.json
```

**Causes:**
1. Invalid JSON syntax
2. Missing required fields
3. Invalid references
4. Schema violation

**Solutions:**

```bash
# Check JSON syntax
jsonlint configs/workflows.json

# Validate against schema
curl -X POST http://localhost:8000/api/v1/configs/validate-schema \
  -d @my_config.json

# Fix common issues
{
  "id": "required_field",  // Add missing required fields
  "agent_id": "existing_agent",  // Fix invalid references
  "llm_config": {
    "model": "valid-model"  // Use valid values
  }
}
```

### Issue: Hot Reload Not Working

**Symptoms:**
- Configuration changes not applied
- Need to restart service
- Active sessions use old config

**Diagnosis:**
```bash
# Check hot reload status
curl http://localhost:8000/api/v1/configs/hot-reload/status

# Check file watcher
curl http://localhost:8000/api/v1/configs/watcher/status
```

**Causes:**
1. Hot reload disabled
2. File watcher not running
3. File permissions
4. Configuration errors

**Solutions:**

```json
// Enable hot reload
{
  "hot_reload": {
    "enabled": true,
    "watch_paths": ["configs/"],
    "debounce_ms": 1000
  }
}

// Check file permissions
chmod 644 configs/*.json

// Manual reload
curl -X POST http://localhost:8000/api/v1/configs/reload
```

## API Issues

### Issue: 401 Unauthorized

**Symptoms:**
- API returns 401
- Authentication failed
- Access denied

**Diagnosis:**
```bash
# Check API key
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/sessions

# Check authentication configuration
curl http://localhost:8000/api/v1/auth/config
```

**Causes:**
1. Missing API key
2. Invalid API key
3. Expired token
4. Wrong authentication method

**Solutions:**

```bash
# Set API key
export API_KEY="your-api-key"

# Use correct header
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/sessions

# Get new token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d '{"username": "user", "password": "pass"}'
```

### Issue: 429 Rate Limit Exceeded

**Symptoms:**
- API returns 429
- Too many requests
- Temporary block

**Diagnosis:**
```bash
# Check rate limit
curl -I http://localhost:8000/api/v1/sessions | grep X-RateLimit

# Check rate limit configuration
curl http://localhost:8000/api/v1/configs/rate-limit
```

**Causes:**
1. Too many requests
2. Rate limit too low
3. No request throttling

**Solutions:**

```json
// Increase rate limit
{
  "rate_limit": {
    "requests_per_minute": 100,  // Increase from 60
    "burst": 20
  }
}

// Implement client-side throttling
// Wait for X-RateLimit-Reset header

// Use exponential backoff
for i in {1..5}; do
  curl http://localhost:8000/api/v1/sessions && break
  sleep $((2**i))
done
```

### Issue: 500 Internal Server Error

**Symptoms:**
- API returns 500
- Server error
- Unexpected failure

**Diagnosis:**
```bash
# Check server logs
curl http://localhost:8000/api/v1/logs?level=ERROR

# Check service health
curl http://localhost:8000/health

# Check dependencies
curl http://localhost:8000/api/v1/health/dependencies
```

**Causes:**
1. Unhandled exception
2. Database connection failure
3. External service failure
4. Configuration error

**Solutions:**

```bash
# Check logs for stack trace
docker-compose logs orchestration-service | tail -100

# Check database connection
mongosh --eval "db.adminCommand('ping')"

# Check Redis connection
redis-cli PING

# Restart service
docker-compose restart orchestration-service
```

## Infrastructure Issues

### Issue: MongoDB Connection Failed

**Symptoms:**
- Cannot connect to MongoDB
- Session storage fails
- Database errors

**Diagnosis:**
```bash
# Test connection
mongosh $MONGODB_URL --eval "db.adminCommand('ping')"

# Check MongoDB status
docker-compose ps mongodb

# Check connection string
echo $MONGODB_URL
```

**Causes:**
1. MongoDB not running
2. Wrong connection string
3. Authentication failure
4. Network issues

**Solutions:**

```bash
# Start MongoDB
docker-compose up -d mongodb

# Fix connection string
export MONGODB_URL="mongodb://user:pass@localhost:27017/orchestration"

# Check authentication
mongosh $MONGODB_URL --eval "db.auth('user', 'pass')"

# Check network
docker-compose exec orchestration-service ping mongodb
```

### Issue: Redis Connection Failed

**Symptoms:**
- Cannot connect to Redis
- Cache not working
- Connection errors

**Diagnosis:**
```bash
# Test connection
redis-cli -u $REDIS_URL PING

# Check Redis status
docker-compose ps redis

# Check connection string
echo $REDIS_URL
```

**Causes:**
1. Redis not running
2. Wrong connection string
3. Authentication failure
4. Network issues

**Solutions:**

```bash
# Start Redis
docker-compose up -d redis

# Fix connection string
export REDIS_URL="redis://localhost:6379/0"

# Check authentication
redis-cli -u $REDIS_URL AUTH password

# Check network
docker-compose exec orchestration-service ping redis
```

### Issue: High Latency

**Symptoms:**
- Slow API responses
- High response times
- Poor performance

**Diagnosis:**
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/sessions

# Check metrics
curl http://localhost:8000/api/v1/metrics | grep latency

# Check system resources
top
```

**Causes:**
1. Network latency
2. Database slow queries
3. Cache misses
4. Resource contention

**Solutions:**

```bash
# Enable caching
# See Cache Configuration Guide

# Optimize database queries
# Add indexes to MongoDB

# Use connection pooling
{
  "database": {
    "pool_size": 20,
    "max_overflow": 10
  }
}

# Scale horizontally
docker-compose up -d --scale orchestration-service=3
```

## Getting Help

### Collect Diagnostic Information

```bash
#!/bin/bash
# diagnostic.sh - Collect diagnostic information

echo "=== Service Health ===" > diagnostic.txt
curl http://localhost:8000/health >> diagnostic.txt

echo "\n=== Metrics ===" >> diagnostic.txt
curl http://localhost:8000/api/v1/metrics >> diagnostic.txt

echo "\n=== Recent Errors ===" >> diagnostic.txt
curl http://localhost:8000/api/v1/logs?level=ERROR&limit=50 >> diagnostic.txt

echo "\n=== Configuration ===" >> diagnostic.txt
curl http://localhost:8000/api/v1/configs/active >> diagnostic.txt

echo "\n=== System Info ===" >> diagnostic.txt
uname -a >> diagnostic.txt
docker-compose version >> diagnostic.txt

echo "Diagnostic information saved to diagnostic.txt"
```

### Support Resources

- **Documentation**: Check all guides in `docs/`
- **Examples**: Review `configs/templates/complete_examples/`
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions

### Before Reporting Issues

1. Check this troubleshooting guide
2. Review relevant documentation
3. Collect diagnostic information
4. Try to reproduce with minimal example
5. Check for similar existing issues

## Next Steps

1. Review [Topology Configuration](TOPOLOGY_CONFIGURATION.md)
2. Configure [Execution Strategies](EXECUTION_STRATEGIES.md)
3. Set up [Cache Settings](CACHE_CONFIGURATION.md)
4. Configure [Agent Behaviors](AGENT_BEHAVIOR.md)
5. Read [Migration Guide](MIGRATION_GUIDE.md)

