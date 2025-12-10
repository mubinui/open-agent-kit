"""
Property-based tests for resource management and limits.

**Feature: industry-grade-orchestration**

These tests verify correctness properties of resource management including
resource limits and timeout enforcement using property-based testing with Hypothesis.
"""

import asyncio
import time
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from src.config.execution_models import ExecutionConfig, ResourceLimits
from src.config.topology_models import (
    AgentNode,
    TopologyConfig,
    TopologyType,
)
from src.patterns.execution_engine import (
    ExecutionEngine,
    ExecutionStatus,
)
from src.patterns.topology_engine import WorkflowGraph


# Mock agent factory for testing
class MockAgentFactory:
    """Mock agent factory that returns mock agents."""
    
    def __init__(self, execution_time: float = 0.1):
        self.execution_time = execution_time
        self.agents = {}
    
    async def get_agent(self, agent_id: str):
        """Get or create a mock agent."""
        if agent_id not in self.agents:
            self.agents[agent_id] = MockAgent(agent_id, self.execution_time)
        return self.agents[agent_id]


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id: str, execution_time: float = 0.1):
        self.agent_id = agent_id
        self.name = agent_id
        self.execution_time = execution_time
    
    async def process(self, context):
        """Mock process method."""
        # Simulate agent processing time
        await asyncio.sleep(self.execution_time)
        return {
            'response': f"Response from {self.agent_id}",
            'agent_id': self.agent_id
        }


# Property 18: Resource limit enforcement
# **Feature: industry-grade-orchestration, Property 18: Resource limit enforcement**
# **Validates: Requirements 7.2**

@given(
    max_concurrent=st.integers(min_value=1, max_value=2),
    num_requests=st.integers(min_value=3, max_value=4),
    agent_execution_time=st.floats(min_value=0.1, max_value=0.2),
)
@settings(max_examples=100, deadline=None)
def test_resource_limit_enforcement(max_concurrent, num_requests, agent_execution_time):
    """
    Property 18: Resource limit enforcement
    
    For any workflow at its configured concurrent execution limit, new requests
    should either be queued or rejected with a resource limit error.
    
    **Validates: Requirements 7.2**
    """
    # Ensure we have more requests than the limit
    if num_requests <= max_concurrent:
        num_requests = max_concurrent + 1
    
    async def run_test():
        # Create execution engine with resource limits
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
            resource_limits=ResourceLimits(
                max_concurrent_executions=max_concurrent,
                max_execution_time=10.0,
                max_agent_calls=100,
                max_context_size=100000,
            )
        )
        
        agent_factory = MockAgentFactory(execution_time=agent_execution_time)
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create simple single-agent workflow
            topology = TopologyConfig(
                type=TopologyType.SINGLE,
                nodes=[AgentNode(id="node_0", agent_id="agent_0")],
                edges=[],
                entry_node="node_0",
            )
            workflow = WorkflowGraph(topology)
            
            # Submit all requests concurrently
            tasks = []
            for i in range(num_requests):
                task = asyncio.create_task(
                    engine.execute_workflow(
                        workflow_id="test_workflow",
                        session_id=uuid4(),
                        message=f"Test message {i}",
                        context={},
                        workflow_graph=workflow,
                    )
                )
                tasks.append(task)
                # Small delay to ensure requests arrive in order
                await asyncio.sleep(0.01)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            # Count successful and rejected executions
            successful = [r for r in results if r.status == ExecutionStatus.SUCCESS]
            rejected = [r for r in results if r.status == ExecutionStatus.FAILURE 
                       and "resource limit" in r.final_response.lower()]
            
            # Property: At least some requests should be rejected due to resource limits
            # Since we have more requests than max_concurrent, and they overlap,
            # some should be rejected
            assert len(rejected) > 0, (
                f"Expected some requests to be rejected due to resource limits, "
                f"but all {len(results)} requests completed. "
                f"max_concurrent={max_concurrent}, num_requests={num_requests}"
            )
            
            # Property: The number of successful + rejected should equal total requests
            assert len(successful) + len(rejected) == num_requests, (
                f"Unexpected result distribution: "
                f"successful={len(successful)}, rejected={len(rejected)}, "
                f"total={num_requests}"
            )
            
            # Property: At least max_concurrent requests should succeed
            # (the first batch should go through)
            assert len(successful) >= max_concurrent, (
                f"Expected at least {max_concurrent} successful executions, "
                f"but got {len(successful)}"
            )
            
            # Verify rejected requests have correct error metadata
            for result in rejected:
                assert "resource_limit_reached" in result.metadata.get("error", ""), (
                    f"Rejected request missing resource_limit_reached error in metadata"
                )
                assert result.metadata.get("max_concurrent") == max_concurrent, (
                    f"Rejected request has incorrect max_concurrent in metadata"
                )
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


# Property 19: Timeout enforcement
# **Feature: industry-grade-orchestration, Property 19: Timeout enforcement**
# **Validates: Requirements 7.4**

@given(
    timeout=st.floats(min_value=0.1, max_value=0.2),
    agent_execution_time=st.floats(min_value=0.3, max_value=0.5),
)
@settings(max_examples=100, deadline=None)
def test_timeout_enforcement(timeout, agent_execution_time):
    """
    Property 19: Timeout enforcement
    
    For any agent execution exceeding its configured timeout, the execution
    should be terminated and return a timeout error.
    
    **Validates: Requirements 7.4**
    """
    # Ensure agent takes longer than timeout
    if agent_execution_time <= timeout:
        agent_execution_time = timeout + 0.2
    
    async def run_test():
        # Create execution engine with short timeout
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
            resource_limits=ResourceLimits(
                max_concurrent_executions=10,
                max_execution_time=timeout,
                max_agent_calls=100,
                max_context_size=100000,
            )
        )
        
        agent_factory = MockAgentFactory(execution_time=agent_execution_time)
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create simple single-agent workflow
            topology = TopologyConfig(
                type=TopologyType.SINGLE,
                nodes=[AgentNode(id="slow_node", agent_id="slow_agent")],
                edges=[],
                entry_node="slow_node",
            )
            workflow = WorkflowGraph(topology)
            
            # Execute workflow
            start_time = time.time()
            
            result = await engine.execute_workflow(
                workflow_id="timeout_workflow",
                session_id=uuid4(),
                message="Test timeout",
                context={},
                workflow_graph=workflow,
            )
            
            execution_time = time.time() - start_time
            
            # Property: Execution should timeout
            assert result.status == ExecutionStatus.TIMEOUT, (
                f"Expected TIMEOUT status, got {result.status}. "
                f"Response: {result.final_response}"
            )
            
            # Property: Execution time should be close to timeout (not agent execution time)
            # Allow 50% overhead for timeout detection and cleanup
            assert execution_time < agent_execution_time * 0.8, (
                f"Execution took too long: {execution_time:.3f}s, "
                f"expected close to timeout {timeout:.3f}s, "
                f"agent would take {agent_execution_time:.3f}s"
            )
            
            # Property: Error message should mention timeout
            assert "timed out" in result.final_response.lower() or "timeout" in result.final_response.lower(), (
                f"Timeout error message should mention 'timeout' or 'timed out', "
                f"got: {result.final_response}"
            )
            
            # Property: Metadata should contain timeout information
            assert "timeout" in result.metadata.get("error", ""), (
                f"Metadata should contain timeout error"
            )
            assert "timeout_seconds" in result.metadata, (
                f"Metadata should contain timeout_seconds"
            )
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())
