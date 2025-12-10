"""
Property-based tests for async execution engine.

**Feature: industry-grade-orchestration**

These tests verify correctness properties of the async execution engine
using property-based testing with Hypothesis.
"""

import asyncio
import time
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from src.config.execution_models import ExecutionConfig
from src.config.topology_models import (
    AgentEdge,
    AgentNode,
    ContextStrategy,
    TopologyConfig,
    TopologyType,
)
from src.patterns.execution_engine import (
    AgentStatus,
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


# Helper functions for creating test topologies

def create_sequential_topology(num_agents: int) -> TopologyConfig:
    """Create a sequential topology with N agents."""
    nodes = [
        AgentNode(
            id=f"node_{i}",
            agent_id=f"agent_{i}",
        )
        for i in range(num_agents)
    ]
    
    edges = [
        AgentEdge(
            from_node=f"node_{i}",
            to_node=f"node_{i+1}",
            context_strategy=ContextStrategy.FULL,
        )
        for i in range(num_agents - 1)
    ]
    
    return TopologyConfig(
        type=TopologyType.SEQUENTIAL,
        nodes=nodes,
        edges=edges,
        entry_node="node_0",
    )


def create_tree_topology(num_branches: int) -> TopologyConfig:
    """Create a tree topology with N parallel branches (no aggregator)."""
    # Root node
    nodes = [AgentNode(id="root", agent_id="agent_root")]
    
    # Branch nodes (leaf nodes in the tree)
    for i in range(num_branches):
        nodes.append(AgentNode(id=f"branch_{i}", agent_id=f"agent_branch_{i}"))
    
    # Edges from root to branches (tree structure - each node has only one parent)
    edges = [
        AgentEdge(
            from_node="root",
            to_node=f"branch_{i}",
            context_strategy=ContextStrategy.FULL,
        )
        for i in range(num_branches)
    ]
    
    return TopologyConfig(
        type=TopologyType.TREE,
        nodes=nodes,
        edges=edges,
        entry_node="root",
    )


# Property 1: Concurrent request processing
# **Feature: industry-grade-orchestration, Property 1: Concurrent request processing**
# **Validates: Requirements 1.1**

@given(
    num_requests=st.integers(min_value=2, max_value=3),
    agent_execution_time=st.floats(min_value=0.05, max_value=0.1),
)
@settings(max_examples=10, deadline=None)
def test_concurrent_request_processing(num_requests, agent_execution_time):
    """
    Property 1: Concurrent request processing
    
    For any set of simultaneous session requests, the total execution time
    should be less than the sum of individual execution times when parallel
    execution is enabled.
    
    **Validates: Requirements 1.1**
    """
    async def run_test():
        # Create execution engine with parallel execution enabled
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
        )
        
        agent_factory = MockAgentFactory(execution_time=agent_execution_time)
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create simple single-agent workflows
            workflows = []
            for i in range(num_requests):
                topology = TopologyConfig(
                    type=TopologyType.SINGLE,
                    nodes=[AgentNode(id=f"node_{i}", agent_id=f"agent_{i}")],
                    edges=[],
                    entry_node=f"node_{i}",
                )
                workflows.append(WorkflowGraph(topology))
            
            # Execute all workflows concurrently
            start_time = time.time()
            
            tasks = [
                engine.execute_workflow(
                    workflow_id=f"workflow_{i}",
                    session_id=uuid4(),
                    message=f"Test message {i}",
                    context={},
                    workflow_graph=workflow,
                )
                for i, workflow in enumerate(workflows)
            ]
            
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Calculate sum of individual execution times
            sum_of_individual_times = sum(r.execution_time for r in results)
            
            # Property: Total time should be less than sum of individual times
            # Allow some overhead for scheduling and coordination
            assert total_time < sum_of_individual_times * 0.9, (
                f"Concurrent execution not efficient: "
                f"total_time={total_time:.3f}s, "
                f"sum_of_individual={sum_of_individual_times:.3f}s"
            )
            
            # Verify all workflows succeeded
            for result in results:
                assert result.status == ExecutionStatus.SUCCESS
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


# Property 2: Non-blocking task execution
# **Feature: industry-grade-orchestration, Property 2: Non-blocking task execution**
# **Validates: Requirements 1.4**

@given(
    long_task_time=st.floats(min_value=0.3, max_value=0.5),
    short_task_time=st.floats(min_value=0.05, max_value=0.1),
    num_short_tasks=st.integers(min_value=2, max_value=3),
)
@settings(max_examples=10, deadline=None)
def test_non_blocking_task_execution(long_task_time, short_task_time, num_short_tasks):
    """
    Property 2: Non-blocking task execution
    
    For any long-running agent task, other tasks submitted during its execution
    should complete independently without waiting for the long-running task.
    
    **Validates: Requirements 1.4**
    """
    async def run_test():
        # Create execution engine
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
        )
        
        # Create agent factory with different execution times
        agent_factory = MockAgentFactory(execution_time=short_task_time)
        
        # Add a slow agent
        class SlowMockAgent(MockAgent):
            async def process(self, context):
                await asyncio.sleep(long_task_time)
                return {'response': f"Slow response from {self.agent_id}"}
        
        agent_factory.agents['slow_agent'] = SlowMockAgent('slow_agent', long_task_time)
        
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create long-running workflow
            long_topology = TopologyConfig(
                type=TopologyType.SINGLE,
                nodes=[AgentNode(id="slow_node", agent_id="slow_agent")],
                edges=[],
                entry_node="slow_node",
            )
            long_workflow = WorkflowGraph(long_topology)
            
            # Start long-running task
            long_task = asyncio.create_task(
                engine.execute_workflow(
                    workflow_id="long_workflow",
                    session_id=uuid4(),
                    message="Long task",
                    context={},
                    workflow_graph=long_workflow,
                )
            )
            
            # Wait a bit to ensure long task has started
            await asyncio.sleep(0.05)
            
            # Submit short tasks while long task is running
            short_tasks = []
            for i in range(num_short_tasks):
                topology = TopologyConfig(
                    type=TopologyType.SINGLE,
                    nodes=[AgentNode(id=f"fast_node_{i}", agent_id=f"agent_{i}")],
                    edges=[],
                    entry_node=f"fast_node_{i}",
                )
                workflow = WorkflowGraph(topology)
                
                task = asyncio.create_task(
                    engine.execute_workflow(
                        workflow_id=f"short_workflow_{i}",
                        session_id=uuid4(),
                        message=f"Short task {i}",
                        context={},
                        workflow_graph=workflow,
                    )
                )
                short_tasks.append(task)
            
            # Wait for short tasks to complete
            short_results = await asyncio.gather(*short_tasks)
            
            # Property: Short tasks should complete before long task
            # Check if long task is still running
            assert not long_task.done(), (
                "Long task completed too early - short tasks may have been blocked"
            )
            
            # Verify all short tasks succeeded
            for result in short_results:
                assert result.status == ExecutionStatus.SUCCESS
            
            # Wait for long task to complete
            long_result = await long_task
            assert long_result.status == ExecutionStatus.SUCCESS
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


# Property 14: Parallel workflow execution
# **Feature: industry-grade-orchestration, Property 14: Parallel workflow execution**
# **Validates: Requirements 6.2**

@given(
    num_branches=st.integers(min_value=2, max_value=3),
    branch_execution_time=st.floats(min_value=0.05, max_value=0.1),
)
@settings(max_examples=10, deadline=None)
def test_parallel_workflow_execution(num_branches, branch_execution_time):
    """
    Property 14: Parallel workflow execution
    
    For any workflow with independent branches (no dependencies between them),
    the branches should execute concurrently with total time approximately
    equal to the longest branch time.
    
    **Validates: Requirements 6.2**
    """
    async def run_test():
        # Create execution engine with parallel execution enabled
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
        )
        
        agent_factory = MockAgentFactory(execution_time=branch_execution_time)
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create tree topology with parallel branches
            topology = create_tree_topology(num_branches)
            workflow = WorkflowGraph(topology)
            
            # Execute workflow
            start_time = time.time()
            
            result = await engine.execute_workflow(
                workflow_id="parallel_workflow",
                session_id=uuid4(),
                message="Test parallel execution",
                context={},
                workflow_graph=workflow,
            )
            
            total_time = time.time() - start_time
            
            # Calculate expected time for sequential execution
            # Root + all branches
            sequential_time = branch_execution_time * (1 + num_branches)
            
            # Property: Total time should be much less than sequential time
            # With parallel execution, time should be approximately:
            # root_time + max(branch_times)
            expected_parallel_time = branch_execution_time * 2  # root + branches (parallel)
            
            # Allow 50% overhead for coordination
            assert total_time < sequential_time * 0.7, (
                f"Parallel execution not efficient: "
                f"total_time={total_time:.3f}s, "
                f"sequential_time={sequential_time:.3f}s, "
                f"expected_parallel={expected_parallel_time:.3f}s"
            )
            
            # Debug: Print result details if failed
            if result.status != ExecutionStatus.SUCCESS:
                print(f"\nWorkflow failed with status: {result.status}")
                print(f"Final response: {result.final_response}")
                print(f"Agent results: {result.agent_results}")
                print(f"Metadata: {result.metadata}")
            
            # Verify workflow succeeded
            assert result.status == ExecutionStatus.SUCCESS, (
                f"Workflow failed: {result.final_response}, "
                f"agent_results={result.agent_results}"
            )
            
            # Verify all agents executed
            assert len(result.agent_results) == num_branches + 1  # root + branches
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


# Property 15: Sequential workflow ordering
# **Feature: industry-grade-orchestration, Property 15: Sequential workflow ordering**
# **Validates: Requirements 6.3**

@given(
    num_agents=st.integers(min_value=2, max_value=3),
    agent_execution_time=st.floats(min_value=0.05, max_value=0.1),
)
@settings(max_examples=10, deadline=None)
def test_sequential_workflow_ordering(num_agents, agent_execution_time):
    """
    Property 15: Sequential workflow ordering
    
    For any sequential workflow, agents should execute in the exact order
    specified in the configuration, with each agent starting only after
    the previous completes.
    
    **Validates: Requirements 6.3**
    """
    async def run_test():
        # Track execution order
        execution_order = []
        execution_times = {}
        
        class OrderTrackingAgent(MockAgent):
            async def process(self, context):
                # Record start time
                start_time = time.time()
                execution_order.append(self.agent_id)
                execution_times[self.agent_id] = {'start': start_time}
                
                # Execute
                result = await super().process(context)
                
                # Record end time
                execution_times[self.agent_id]['end'] = time.time()
                
                return result
        
        # Create execution engine
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
        )
        
        agent_factory = MockAgentFactory(execution_time=agent_execution_time)
        
        # Replace agents with order-tracking agents
        for i in range(num_agents):
            agent_id = f"agent_{i}"
            agent_factory.agents[agent_id] = OrderTrackingAgent(agent_id, agent_execution_time)
        
        engine = ExecutionEngine(config=config, agent_factory=agent_factory)
        
        try:
            await engine.start()
            
            # Create sequential topology
            topology = create_sequential_topology(num_agents)
            workflow = WorkflowGraph(topology)
            
            # Execute workflow
            result = await engine.execute_workflow(
                workflow_id="sequential_workflow",
                session_id=uuid4(),
                message="Test sequential execution",
                context={},
                workflow_graph=workflow,
            )
            
            # Property 1: Agents executed in correct order
            expected_order = [f"agent_{i}" for i in range(num_agents)]
            assert execution_order == expected_order, (
                f"Agents executed in wrong order: "
                f"expected={expected_order}, actual={execution_order}"
            )
            
            # Property 2: Each agent started after previous completed
            for i in range(num_agents - 1):
                current_agent = f"agent_{i}"
                next_agent = f"agent_{i+1}"
                
                current_end = execution_times[current_agent]['end']
                next_start = execution_times[next_agent]['start']
                
                assert next_start >= current_end, (
                    f"Agent {next_agent} started before {current_agent} completed: "
                    f"{current_agent} ended at {current_end:.3f}, "
                    f"{next_agent} started at {next_start:.3f}"
                )
            
            # Verify workflow succeeded
            assert result.status == ExecutionStatus.SUCCESS
            
            # Verify all agents executed
            assert len(result.agent_results) == num_agents
            
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())
