"""
Property-based tests for execution strategies.

**Feature: industry-grade-orchestration**

These tests verify correctness properties of execution strategies
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
from src.patterns.execution_strategies import (
    ExecutionStrategyFactory,
    ExecutionStrategyType,
    ParallelExecutionStrategy,
    HybridExecutionStrategy,
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

def create_tree_topology_with_branches(num_branches: int) -> TopologyConfig:
    """
    Create a tree topology with N parallel branches (no aggregator).
    
    Structure:
        root
       / | \
      b1 b2 b3 ...
    
    This is a valid tree where each node has at most one parent.
    """
    # Root node
    nodes = [AgentNode(id="root", agent_id="agent_root")]
    
    # Branch nodes (leaf nodes)
    for i in range(num_branches):
        nodes.append(AgentNode(id=f"branch_{i}", agent_id=f"agent_branch_{i}"))
    
    # Edges from root to branches
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


def create_hybrid_topology(num_parallel_branches: int, num_sequential_after: int) -> TopologyConfig:
    """
    Create a hybrid topology with parallel branches followed by sequential nodes.
    
    Structure:
        root
       / | \
      b1 b2 b3 ... (parallel)
       \ | /
      merge
        |
      seq1
        |
      seq2 ...
    """
    # Root node
    nodes = [AgentNode(id="root", agent_id="agent_root")]
    
    # Parallel branch nodes
    for i in range(num_parallel_branches):
        nodes.append(AgentNode(id=f"branch_{i}", agent_id=f"agent_branch_{i}"))
    
    # Merge node
    nodes.append(AgentNode(id="merge", agent_id="agent_merge"))
    
    # Sequential nodes after merge
    for i in range(num_sequential_after):
        nodes.append(AgentNode(id=f"seq_{i}", agent_id=f"agent_seq_{i}"))
    
    # Edges from root to branches
    edges = [
        AgentEdge(
            from_node="root",
            to_node=f"branch_{i}",
            context_strategy=ContextStrategy.FULL,
        )
        for i in range(num_parallel_branches)
    ]
    
    # Edges from branches to merge
    for i in range(num_parallel_branches):
        edges.append(
            AgentEdge(
                from_node=f"branch_{i}",
                to_node="merge",
                context_strategy=ContextStrategy.FULL,
            )
        )
    
    # Edges for sequential chain after merge
    edges.append(
        AgentEdge(
            from_node="merge",
            to_node="seq_0",
            context_strategy=ContextStrategy.FULL,
        )
    )
    
    for i in range(num_sequential_after - 1):
        edges.append(
            AgentEdge(
                from_node=f"seq_{i}",
                to_node=f"seq_{i+1}",
                context_strategy=ContextStrategy.FULL,
            )
        )
    
    return TopologyConfig(
        type=TopologyType.GRAPH,  # Use GRAPH for hybrid
        nodes=nodes,
        edges=edges,
        entry_node="root",
    )


# Property 3: Tree topology parallel execution
# **Feature: industry-grade-orchestration, Property 3: Tree topology parallel execution**
# **Validates: Requirements 2.2**

@given(
    num_branches=st.integers(min_value=2, max_value=4),
    branch_execution_time=st.floats(min_value=0.05, max_value=0.1),
)
@settings(max_examples=10, deadline=None)
def test_tree_topology_parallel_execution(num_branches, branch_execution_time):
    """
    Property 3: Tree topology parallel execution
    
    For any tree topology with multiple child nodes from a single parent,
    the child nodes should execute concurrently (total execution time ≈ max child time,
    not sum of child times).
    
    **Validates: Requirements 2.2**
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
        
        # Use parallel execution strategy explicitly
        strategy = ParallelExecutionStrategy()
        engine = ExecutionEngine(
            config=config,
            agent_factory=agent_factory,
            execution_strategy=strategy
        )
        
        try:
            await engine.start()
            
            # Create tree topology with parallel branches (no aggregator for valid tree)
            topology = create_tree_topology_with_branches(num_branches)
            workflow = WorkflowGraph(topology)
            
            # Validate topology
            validation = workflow.validate()
            assert validation.is_valid, f"Topology validation failed: {validation.errors}"
            
            # Execute workflow and measure time
            start_time = time.time()
            
            result = await engine.execute_workflow(
                workflow_id="tree_parallel_workflow",
                session_id=uuid4(),
                message="Test tree parallel execution",
                context={},
                workflow_graph=workflow,
            )
            
            total_time = time.time() - start_time
            
            # Calculate expected times
            # Sequential: root + (branch1 + branch2 + ... + branchN)
            sequential_time = branch_execution_time * (1 + num_branches)
            
            # Parallel: root + max(branches)
            # Since all branches have same execution time, max = branch_execution_time
            expected_parallel_time = branch_execution_time * 2  # root + branches (parallel)
            
            # Property: Total time should be approximately equal to parallel time,
            # and significantly less than sequential time
            # Allow 60% overhead for coordination and scheduling
            max_acceptable_time = expected_parallel_time * 1.6
            
            assert total_time < max_acceptable_time, (
                f"Tree parallel execution too slow: "
                f"total_time={total_time:.3f}s, "
                f"expected_parallel={expected_parallel_time:.3f}s, "
                f"max_acceptable={max_acceptable_time:.3f}s, "
                f"sequential_time={sequential_time:.3f}s"
            )
            
            # Also verify it's faster than 70% of sequential time
            assert total_time < sequential_time * 0.7, (
                f"Tree parallel execution not efficient enough: "
                f"total_time={total_time:.3f}s should be < 70% of "
                f"sequential_time={sequential_time:.3f}s"
            )
            
            # Verify workflow succeeded
            assert result.status == ExecutionStatus.SUCCESS, (
                f"Workflow failed: {result.final_response}"
            )
            
            # Verify all agents executed (root + branches)
            expected_agents = 1 + num_branches
            assert len(result.agent_results) == expected_agents, (
                f"Expected {expected_agents} agent results, got {len(result.agent_results)}"
            )
            
            # Verify all agents succeeded
            for node_id, agent_result in result.agent_results.items():
                assert agent_result.status == AgentStatus.SUCCESS, (
                    f"Agent {node_id} failed: {agent_result.error}"
                )
        
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())


# Property 16: Hybrid workflow parallelization
# **Feature: industry-grade-orchestration, Property 16: Hybrid workflow parallelization**
# **Validates: Requirements 6.4**

@given(
    num_parallel_branches=st.integers(min_value=2, max_value=3),
    num_sequential_after=st.integers(min_value=1, max_value=2),
    execution_time=st.floats(min_value=0.05, max_value=0.1),
)
@settings(max_examples=10, deadline=None)
def test_hybrid_workflow_parallelization(num_parallel_branches, num_sequential_after, execution_time):
    """
    Property 16: Hybrid workflow parallelization
    
    For any hybrid workflow, independent branches should execute in parallel
    while dependent branches should wait for their dependencies to complete.
    
    **Validates: Requirements 6.4**
    """
    async def run_test():
        # Create execution engine with hybrid strategy
        config = ExecutionConfig(
            max_workers=10,
            queue_size=100,
            enable_parallel=True,
            default_timeout=10.0,
        )
        
        agent_factory = MockAgentFactory(execution_time=execution_time)
        
        # Use hybrid execution strategy explicitly
        strategy = HybridExecutionStrategy()
        engine = ExecutionEngine(
            config=config,
            agent_factory=agent_factory,
            execution_strategy=strategy
        )
        
        try:
            await engine.start()
            
            # Create hybrid topology
            topology = create_hybrid_topology(num_parallel_branches, num_sequential_after)
            workflow = WorkflowGraph(topology)
            
            # Validate topology
            validation = workflow.validate()
            assert validation.is_valid, f"Topology validation failed: {validation.errors}"
            
            # Execute workflow and measure time
            start_time = time.time()
            
            result = await engine.execute_workflow(
                workflow_id="hybrid_workflow",
                session_id=uuid4(),
                message="Test hybrid execution",
                context={},
                workflow_graph=workflow,
            )
            
            total_time = time.time() - start_time
            
            # Calculate expected times
            # Fully sequential: root + (branch1 + branch2 + ...) + merge + seq1 + seq2 + ...
            fully_sequential_time = execution_time * (
                1 +  # root
                num_parallel_branches +  # branches (sequential)
                1 +  # merge
                num_sequential_after  # sequential chain
            )
            
            # Hybrid (optimal): root + max(branches) + merge + seq1 + seq2 + ...
            expected_hybrid_time = execution_time * (
                1 +  # root
                1 +  # branches (parallel, so just max time)
                1 +  # merge
                num_sequential_after  # sequential chain
            )
            
            # Property: Hybrid execution should parallelize independent branches
            # Allow 60% overhead for coordination
            max_acceptable_time = expected_hybrid_time * 1.6
            
            assert total_time < max_acceptable_time, (
                f"Hybrid execution too slow: "
                f"total_time={total_time:.3f}s, "
                f"expected_hybrid={expected_hybrid_time:.3f}s, "
                f"max_acceptable={max_acceptable_time:.3f}s"
            )
            
            # Property: Should be faster than fully sequential when there are parallel branches
            # Note: We use 90% threshold to account for coordination overhead and async scheduling
            # The benefit of parallelization decreases as the sequential portion increases
            if num_parallel_branches >= 2:
                # Calculate the theoretical speedup
                # If we have N parallel branches and M sequential nodes,
                # the parallel portion saves (N-1) * execution_time
                # So the speedup is: (N-1) / (N + M + 2) where +2 is for root and merge
                theoretical_speedup = (num_parallel_branches - 1) / (num_parallel_branches + num_sequential_after + 2)
                # We expect at least 50% of the theoretical speedup due to overhead
                min_speedup = theoretical_speedup * 0.5
                max_time_ratio = 1.0 - min_speedup
                
                assert total_time < fully_sequential_time * max_time_ratio, (
                    f"Hybrid execution not efficient: "
                    f"total_time={total_time:.3f}s should be < {max_time_ratio*100:.0f}% of "
                    f"fully_sequential={fully_sequential_time:.3f}s "
                    f"(theoretical_speedup={theoretical_speedup:.2f}, min_speedup={min_speedup:.2f})"
                )
            
            # Verify workflow succeeded
            assert result.status == ExecutionStatus.SUCCESS, (
                f"Workflow failed: {result.final_response}"
            )
            
            # Verify all agents executed
            expected_agents = (
                1 +  # root
                num_parallel_branches +  # branches
                1 +  # merge
                num_sequential_after  # sequential chain
            )
            assert len(result.agent_results) == expected_agents, (
                f"Expected {expected_agents} agent results, got {len(result.agent_results)}"
            )
            
            # Verify all agents succeeded
            for node_id, agent_result in result.agent_results.items():
                assert agent_result.status == AgentStatus.SUCCESS, (
                    f"Agent {node_id} failed: {agent_result.error}"
                )
        
        finally:
            await engine.shutdown(wait=False)
    
    # Run the async test
    asyncio.run(run_test())
