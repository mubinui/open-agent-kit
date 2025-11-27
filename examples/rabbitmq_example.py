"""
Example script demonstrating RabbitMQ integration for async agent processing.

This script shows how to:
1. Setup RabbitMQ connection pool
2. Create publisher and consumers
3. Publish and process agent tasks
4. Handle results asynchronously

Requirements:
- RabbitMQ server running (docker run -d -p 5672:5672 rabbitmq:3)
- aio-pika installed (uv sync)
"""

import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from src.infrastructure import (
    AgentTask,
    AgentTaskConsumer,
    AgentTaskPublisher,
    DeadLetterQueueHandler,
    RabbitMQConnectionPool,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def simple_task_handler(task: AgentTask) -> None:
    """
    Simple task handler that simulates agent processing.
    
    Args:
        task: The agent task to process
    """
    logger.info(f"Processing task {task.task_id} for agent {task.agent_id}")
    logger.info(f"Message: {task.message}")
    
    # Simulate some processing time
    await asyncio.sleep(2)
    
    # Simulate occasional failures for DLQ testing
    if "fail" in task.message.lower() and task.retry_count == 0:
        logger.warning(f"Simulating failure for task {task.task_id}")
        raise Exception("Simulated failure for testing")
    
    logger.info(f"Completed task {task.task_id}")


async def example_basic_pubsub():
    """
    Example 1: Basic publish/subscribe pattern.
    
    Demonstrates:
    - Setting up connection pool
    - Creating publisher and consumer
    - Publishing tasks
    - Consuming and processing tasks
    """
    logger.info("=" * 60)
    logger.info("Example 1: Basic Publish/Subscribe")
    logger.info("=" * 60)
    
    # Setup connection pool
    pool = RabbitMQConnectionPool(
        url="amqp://guest:guest@localhost:5672/",
        max_connections=5,
        max_channels=50,
    )
    await pool.initialize()
    
    try:
        # Setup publisher
        publisher = AgentTaskPublisher(pool)
        await publisher.initialize()
        
        # Setup consumer
        consumer = AgentTaskConsumer(
            connection_pool=pool,
            agent_id="example_agent",
            task_handler=simple_task_handler,
            prefetch_count=5,
        )
        await consumer.initialize()
        
        # Start consuming
        await consumer.consume_tasks()
        logger.info("Consumer started, waiting for tasks...")
        
        # Publish some tasks
        for i in range(5):
            task = AgentTask(
                task_id=uuid4(),
                session_id=uuid4(),
                agent_id="example_agent",
                message=f"Task {i}: Process this message",
                context={"task_number": i},
                created_at=datetime.utcnow(),
                priority=i % 3,  # Vary priority
            )
            await publisher.publish_task(task)
            logger.info(f"Published task {i} with priority {task.priority}")
        
        # Wait for processing
        logger.info("Waiting for tasks to be processed...")
        await asyncio.sleep(15)
        
        # Cleanup
        await consumer.close()
        await publisher.close()
        logger.info("Example 1 completed successfully")
        
    finally:
        await pool.close()


async def example_with_dlq():
    """
    Example 2: Dead Letter Queue with retry logic.
    
    Demonstrates:
    - DLQ handler setup
    - Automatic retry with exponential backoff
    - Failed task handling
    """
    logger.info("=" * 60)
    logger.info("Example 2: Dead Letter Queue with Retry")
    logger.info("=" * 60)
    
    # Setup connection pool
    pool = RabbitMQConnectionPool(
        url="amqp://guest:guest@localhost:5672/",
        max_connections=5,
    )
    await pool.initialize()
    
    try:
        # Setup publisher
        publisher = AgentTaskPublisher(pool)
        await publisher.initialize()
        
        # Setup DLQ handler
        dlq_handler = DeadLetterQueueHandler(
            connection_pool=pool,
            publisher=publisher,
            max_retries=3,
            initial_retry_delay=2000,  # 2 seconds
            max_retry_delay=10000,     # 10 seconds
        )
        await dlq_handler.initialize()
        await dlq_handler.start_processing()
        logger.info("DLQ handler started")
        
        # Setup consumer
        consumer = AgentTaskConsumer(
            connection_pool=pool,
            agent_id="dlq_test_agent",
            task_handler=simple_task_handler,
            prefetch_count=5,
        )
        await consumer.initialize()
        await consumer.consume_tasks()
        logger.info("Consumer started")
        
        # Publish tasks (some will fail initially)
        tasks_to_publish = [
            "Task 1: This will succeed",
            "Task 2: This will FAIL initially",  # Will trigger retry
            "Task 3: This will succeed",
            "Task 4: This will FAIL initially",  # Will trigger retry
        ]
        
        for i, message in enumerate(tasks_to_publish):
            task = AgentTask(
                task_id=uuid4(),
                session_id=uuid4(),
                agent_id="dlq_test_agent",
                message=message,
                context={"task_number": i},
                created_at=datetime.utcnow(),
                max_retries=3,
            )
            await publisher.publish_task(task)
            logger.info(f"Published: {message}")
        
        # Wait for processing and retries
        logger.info("Waiting for tasks to be processed (including retries)...")
        await asyncio.sleep(30)
        
        # Cleanup
        await dlq_handler.close()
        await consumer.close()
        await publisher.close()
        logger.info("Example 2 completed successfully")
        
    finally:
        await pool.close()


async def example_multiple_agents():
    """
    Example 3: Multiple agents with separate queues.
    
    Demonstrates:
    - Multiple consumers for different agents
    - Agent-specific task routing
    - Concurrent processing across agents
    """
    logger.info("=" * 60)
    logger.info("Example 3: Multiple Agents")
    logger.info("=" * 60)
    
    # Setup connection pool
    pool = RabbitMQConnectionPool(
        url="amqp://guest:guest@localhost:5672/",
        max_connections=5,
    )
    await pool.initialize()
    
    try:
        # Setup publisher
        publisher = AgentTaskPublisher(pool)
        await publisher.initialize()
        
        # Setup consumers for different agents
        agents = ["reasoning_agent", "knowledge_agent", "response_agent"]
        consumers = []
        
        for agent_id in agents:
            consumer = AgentTaskConsumer(
                connection_pool=pool,
                agent_id=agent_id,
                task_handler=simple_task_handler,
                prefetch_count=3,
            )
            await consumer.initialize()
            await consumer.consume_tasks()
            consumers.append(consumer)
            logger.info(f"Started consumer for {agent_id}")
        
        # Publish tasks to different agents
        for agent_id in agents:
            for i in range(3):
                task = AgentTask(
                    task_id=uuid4(),
                    session_id=uuid4(),
                    agent_id=agent_id,
                    message=f"Task {i} for {agent_id}",
                    context={"agent": agent_id, "task_number": i},
                    created_at=datetime.utcnow(),
                )
                await publisher.publish_task(task)
                logger.info(f"Published task {i} to {agent_id}")
        
        # Wait for processing
        logger.info("Waiting for all agents to process tasks...")
        await asyncio.sleep(15)
        
        # Cleanup
        for consumer in consumers:
            await consumer.close()
        await publisher.close()
        logger.info("Example 3 completed successfully")
        
    finally:
        await pool.close()


async def main():
    """Run all examples."""
    try:
        # Run examples sequentially
        await example_basic_pubsub()
        await asyncio.sleep(2)
        
        await example_with_dlq()
        await asyncio.sleep(2)
        
        await example_multiple_agents()
        
        logger.info("=" * 60)
        logger.info("All examples completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RabbitMQ Integration Examples")
    print("=" * 60)
    print("\nMake sure RabbitMQ is running:")
    print("  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
    print("\nManagement UI available at: http://localhost:15672")
    print("  Username: guest")
    print("  Password: guest")
    print("\n" + "=" * 60 + "\n")
    
    asyncio.run(main())
