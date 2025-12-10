"""
Property-based tests for workflow retry behavior.

**Feature: industry-grade-orchestration**

These tests verify correctness properties of retry strategies and error handling
using property-based testing with Hypothesis.
"""

import asyncio
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from src.config.execution_models import ExecutionConfig, RetryConfig, BackoffStrategy
from src.config.topology_models import AgentNode, TopologyConfig, TopologyType
from src.patterns.execution_engine import ExecutionEngine, ExecutionStatus, AgentStatus
from src.patterns.topology_engine import WorkflowGraph
from src.patterns.error_handler import ErrorHandler, ErrorCategory


# Mock agent factory for testing
class MockAgentFactory:
    """Mock agent factory that returns mock agents."""
    
    def __init__(self):
        self.agents = {}
    
    async def get_agent(self, agent_id: str):
        """Get or create a mock agent."""
        if agent_id not in self.agents:
            self.agents[agent_id] = MockAgent(agent_id)
        return self.agents[agent_id]


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.name = agent_id
        self.call_count = 0
        self.should_fail = False
        self.failure_count = 0
        self.max_failures = 0
        self.error_type = "temporary_failure"
    
    async def process(self, context):
        """Mock process method."""
        self.call_count += 1
        
        # Simulate transient failures
        if self.should_fail and self.call_count <= self.max_failures:
            self.failure_count += 1
            if self.error_type == "timeout":
                raise TimeoutError(f"Agent {self.agent_id} timed out")
            elif self.error_type == "rate_limit":
                raise Exception("Rate limit exceeded")
            elif self.error_type == "validation_error":
                raise ValueError(f"Validation error in {self.agent_id}")
            else:
                raise Exception(f"Temporary failure in {self.agent_id}")
        
        # Success after retries
        return {
            'response': f"Response from {self.agent_id} after {self.call_count} attempts",
            'agent_id': self.agent_id,
            'call_count': self.call_count,
        }


# Property 17: Workflow retry behavior
# **Feature: industry-grade-orchestration, Property 17: Workflow retry behavior**
# **Validates: Requirements 6.5**

@given(
    max_retries=st.integers(min_value=1, max_value=3),
    num_failures=st.integers(min_value=1, max_value=2),
    backoff_factor=st.floats(min_value=1.0, max_value=1.5),
)
@settings(max_examples=100, deadline=None)
def test_workflow_retry_transient_failures(max_retries, num_failures, backoff_factor):
    """
    Property 17: Workflow retry behavior (transient failures)
    
    For any workflow with retry configuration, transient failures should trigger
    retries according to the configured strategy (max retries, backoff), while
    permanent failures should not retry.
    
    This test verifies that transient failures are retried.
    
    **Validates: Requirements 6.5**
    """
    async def run_test():
        # Ensure num_failures doesn't exceed max_retries
        actual_failures = min(num_failures, max_retries)
        
        # Create execution engine with retry configuration
        retry_config = RetryConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            retry_on=["timeout", "rate_limit", "temporary_failure"],
            dont_retry_on=["validation_error", "authentication_error"],
        )
        
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
            retry_strategy=retry_config,
        )
        
        agent_factory = MockAgentFactory()
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create a simple single-agent workflow
            topology = TopologyConfig(
                type=TopologyType.SINGLE,
                nodes=[AgentNode(id="test_node", agent_id="test_agent")],
                edges=[],
                entry_node="test_node",
            )
            workflow = WorkflowGraph(topology)
            
            # Configure agent to fail N times then succeed
            agent = await agent_factory.get_agent("test_agent")
            agent.should_fail = True
            agent.max_failures = actual_failures
            agent.error_type = "temporary_failure"
            
            # Execute workflow
            result = await engine.execute_workflow(
                workflow_id="retry_test_workflow",
                session_id=uuid4(),
                message="Test retry behavior",
                context={},
                workflow_graph=workflow,
            )
            
            # Property 1: Agent should be called (failures + 1 success) times
            expected_calls = actual_failures + 1
            assert agent.call_count == expected_calls, (
                f"Agent should be called {expected_calls} times "
                f"({actual_failures} failures + 1 success), "
                f"but was called {agent.call_count} times"
            )
            
            # Property 2: Workflow should succeed after retries
            assert result.status == ExecutionStatus.SUCCESS, (
                f"Workflow should succeed after {actual_failures} transient failures, "
                f"but got status: {result.status}"
            )
            
            # Property 3: Agent result should show success
            agent_result = result.agent_results.get("test_node")
            assert agent_result is not None, "Agent result should exist"
            assert agent_result.status == AgentStatus.SUCCESS, (
                f"Agent should succeed after retries, but got status: {agent_result.status}"
            )
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


@given(
    max_retries=st.integers(min_value=1, max_value=3),
    backoff_factor=st.floats(min_value=1.0, max_value=1.5),
)
@settings(max_examples=100, deadline=None)
def test_workflow_retry_permanent_failures(max_retries, backoff_factor):
    """
    Property 17: Workflow retry behavior (permanent failures)
    
    For any workflow with retry configuration, permanent failures (validation errors,
    authentication errors) should NOT trigger retries.
    
    This test verifies that permanent failures are not retried.
    
    **Validates: Requirements 6.5**
    """
    async def run_test():
        # Create execution engine with retry configuration
        retry_config = RetryConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            retry_on=["timeout", "rate_limit", "temporary_failure"],
            dont_retry_on=["validation_error", "authentication_error"],
        )
        
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
            retry_strategy=retry_config,
        )
        
        agent_factory = MockAgentFactory()
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create a simple single-agent workflow
            topology = TopologyConfig(
                type=TopologyType.SINGLE,
                nodes=[AgentNode(id="test_node", agent_id="test_agent")],
                edges=[],
                entry_node="test_node",
            )
            workflow = WorkflowGraph(topology)
            
            # Configure agent to always fail with validation error
            agent = await agent_factory.get_agent("test_agent")
            agent.should_fail = True
            agent.max_failures = 999  # Always fail
            agent.error_type = "validation_error"
            
            # Execute workflow
            result = await engine.execute_workflow(
                workflow_id="retry_test_workflow",
                session_id=uuid4(),
                message="Test no retry for permanent failures",
                context={},
                workflow_graph=workflow,
            )
            
            # Property 1: Agent should be called only once (no retries)
            assert agent.call_count == 1, (
                f"Agent should be called only once for permanent failure, "
                f"but was called {agent.call_count} times"
            )
            
            # Property 2: Workflow should fail
            assert result.status == ExecutionStatus.FAILURE, (
                f"Workflow should fail for permanent error, "
                f"but got status: {result.status}"
            )
            
            # Property 3: Agent result should show failure
            agent_result = result.agent_results.get("test_node")
            assert agent_result is not None, "Agent result should exist"
            assert agent_result.status == AgentStatus.FAILURE, (
                f"Agent should fail for permanent error, but got status: {agent_result.status}"
            )
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


@given(
    max_retries=st.integers(min_value=2, max_value=4),
    backoff_factor=st.floats(min_value=1.0, max_value=1.5),
)
@settings(max_examples=100, deadline=None)
def test_workflow_retry_exhaustion(max_retries, backoff_factor):
    """
    Property 17: Workflow retry behavior (retry exhaustion)
    
    For any workflow with retry configuration, if transient failures continue
    beyond max_retries, the workflow should fail after exhausting all retries.
    
    This test verifies that retries are exhausted correctly.
    
    **Validates: Requirements 6.5**
    """
    async def run_test():
        # Create execution engine with retry configuration
        retry_config = RetryConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            retry_on=["timeout", "rate_limit", "temporary_failure"],
            dont_retry_on=["validation_error", "authentication_error"],
        )
        
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
            retry_strategy=retry_config,
        )
        
        agent_factory = MockAgentFactory()
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create a simple single-agent workflow
            topology = TopologyConfig(
                type=TopologyType.SINGLE,
                nodes=[AgentNode(id="test_node", agent_id="test_agent")],
                edges=[],
                entry_node="test_node",
            )
            workflow = WorkflowGraph(topology)
            
            # Configure agent to always fail with transient error
            agent = await agent_factory.get_agent("test_agent")
            agent.should_fail = True
            agent.max_failures = 999  # Always fail
            agent.error_type = "temporary_failure"
            
            # Execute workflow
            result = await engine.execute_workflow(
                workflow_id="retry_test_workflow",
                session_id=uuid4(),
                message="Test retry exhaustion",
                context={},
                workflow_graph=workflow,
            )
            
            # Property 1: Agent should be called (max_retries + 1) times
            expected_calls = max_retries + 1
            assert agent.call_count == expected_calls, (
                f"Agent should be called {expected_calls} times "
                f"(1 initial + {max_retries} retries), "
                f"but was called {agent.call_count} times"
            )
            
            # Property 2: Workflow should fail after exhausting retries
            assert result.status == ExecutionStatus.FAILURE, (
                f"Workflow should fail after exhausting {max_retries} retries, "
                f"but got status: {result.status}"
            )
            
            # Property 3: Agent result should show failure
            agent_result = result.agent_results.get("test_node")
            assert agent_result is not None, "Agent result should exist"
            assert agent_result.status == AgentStatus.FAILURE, (
                f"Agent should fail after exhausting retries, "
                f"but got status: {agent_result.status}"
            )
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


@given(
    max_retries=st.integers(min_value=1, max_value=3),
    backoff_strategy=st.sampled_from([BackoffStrategy.CONSTANT, BackoffStrategy.LINEAR, BackoffStrategy.EXPONENTIAL]),
)
@settings(max_examples=100, deadline=None)
def test_workflow_retry_backoff_strategy(max_retries, backoff_strategy):
    """
    Property 17: Workflow retry behavior (backoff strategy)
    
    For any workflow with retry configuration, the backoff strategy should be
    applied correctly between retry attempts.
    
    This test verifies that different backoff strategies work correctly.
    
    **Validates: Requirements 6.5**
    """
    async def run_test():
        # Use small backoff factor for testing (must be >= 1.0)
        backoff_factor = 1.0
        
        # Create execution engine with retry configuration
        retry_config = RetryConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            backoff_strategy=backoff_strategy,
            retry_on=["timeout", "rate_limit", "temporary_failure"],
            dont_retry_on=["validation_error", "authentication_error"],
        )
        
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
            retry_strategy=retry_config,
        )
        
        agent_factory = MockAgentFactory()
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create a simple single-agent workflow
            topology = TopologyConfig(
                type=TopologyType.SINGLE,
                nodes=[AgentNode(id="test_node", agent_id="test_agent")],
                edges=[],
                entry_node="test_node",
            )
            workflow = WorkflowGraph(topology)
            
            # Configure agent to fail once then succeed
            agent = await agent_factory.get_agent("test_agent")
            agent.should_fail = True
            agent.max_failures = 1
            agent.error_type = "temporary_failure"
            
            # Execute workflow
            result = await engine.execute_workflow(
                workflow_id="retry_test_workflow",
                session_id=uuid4(),
                message="Test backoff strategy",
                context={},
                workflow_graph=workflow,
            )
            
            # Property: Workflow should succeed after retry
            assert result.status == ExecutionStatus.SUCCESS, (
                f"Workflow should succeed with {backoff_strategy.value} backoff, "
                f"but got status: {result.status}"
            )
            
            # Property: Agent should be called twice (1 failure + 1 success)
            assert agent.call_count == 2, (
                f"Agent should be called twice, but was called {agent.call_count} times"
            )
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())
