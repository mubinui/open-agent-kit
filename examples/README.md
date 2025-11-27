# Examples

This directory contains example scripts demonstrating various features of the Orchestration Service.

## RabbitMQ Integration Example

**File**: `rabbitmq_example.py`

Demonstrates the RabbitMQ integration for asynchronous agent processing.

### Prerequisites

1. **RabbitMQ Server**: Start RabbitMQ using Docker:
   ```bash
   docker run -d --name rabbitmq \
     -p 5672:5672 \
     -p 15672:15672 \
     rabbitmq:3-management
   ```

2. **Dependencies**: Install required packages:
   ```bash
   uv sync
   ```

### Running the Example

```bash
python3 examples/rabbitmq_example.py
```

### What It Demonstrates

The example includes three scenarios:

#### Example 1: Basic Publish/Subscribe
- Setting up connection pool
- Creating publisher and consumer
- Publishing tasks with different priorities
- Consuming and processing tasks
- Graceful shutdown

#### Example 2: Dead Letter Queue with Retry
- DLQ handler setup
- Automatic retry with exponential backoff
- Failed task handling
- Retry count tracking

#### Example 3: Multiple Agents
- Multiple consumers for different agents
- Agent-specific task routing
- Concurrent processing across agents
- Load distribution

### Expected Output

```
============================================================
RabbitMQ Integration Examples
============================================================

Make sure RabbitMQ is running:
  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

Management UI available at: http://localhost:15672
  Username: guest
  Password: guest

============================================================

============================================================
Example 1: Basic Publish/Subscribe
============================================================
2024-01-15 10:00:00 - INFO - Initializing RabbitMQ connection pool
2024-01-15 10:00:00 - INFO - Consumer started, waiting for tasks...
2024-01-15 10:00:00 - INFO - Published task 0 with priority 0
...
2024-01-15 10:00:15 - INFO - Example 1 completed successfully

============================================================
Example 2: Dead Letter Queue with Retry
============================================================
2024-01-15 10:00:17 - INFO - DLQ handler started
2024-01-15 10:00:17 - INFO - Consumer started
...
2024-01-15 10:00:47 - INFO - Example 2 completed successfully

============================================================
Example 3: Multiple Agents
============================================================
2024-01-15 10:00:49 - INFO - Started consumer for reasoning_agent
2024-01-15 10:00:49 - INFO - Started consumer for knowledge_agent
2024-01-15 10:00:49 - INFO - Started consumer for response_agent
...
2024-01-15 10:01:04 - INFO - Example 3 completed successfully

============================================================
All examples completed successfully!
============================================================
```

### Monitoring

While the example is running, you can monitor RabbitMQ through the management UI:

1. Open http://localhost:15672 in your browser
2. Login with username `guest` and password `guest`
3. Navigate to the "Queues" tab to see:
   - `agent.tasks.example_agent`
   - `agent.tasks.dlq_test_agent`
   - `agent.tasks.reasoning_agent`
   - `agent.tasks.knowledge_agent`
   - `agent.tasks.response_agent`
   - `agent.tasks.dlq` (dead letter queue)

### Customization

You can modify the example to:

- Change the number of tasks published
- Adjust retry delays and max retries
- Add more agents
- Implement custom task handlers
- Test different failure scenarios

### Troubleshooting

**Connection refused**:
- Make sure RabbitMQ is running: `docker ps | grep rabbitmq`
- Check the connection URL in the code

**Tasks not being processed**:
- Check RabbitMQ logs: `docker logs rabbitmq`
- Verify queues are created in the management UI
- Check consumer logs for errors

**Import errors**:
- Make sure dependencies are installed: `uv sync`
- Run from the project root directory

## Additional Examples

More examples will be added as new features are implemented:

- [ ] Async conversation execution
- [ ] Integration with SessionManager
- [ ] Group chat orchestration
- [ ] Vector database RAG
- [ ] API endpoint usage
