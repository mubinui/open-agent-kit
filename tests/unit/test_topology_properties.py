"""
Property-based tests for workflow topology engine.

Tests correctness properties for graph-based workflow topologies including
result routing, invalid topology rejection, and cycle termination.
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.config.topology_models import (
    AgentEdge,
    AgentNode,
    ContextStrategy,
    TerminationCondition,
    TerminationConditionType,
    TopologyConfig,
    TopologyType,
)
from src.patterns.topology_engine import WorkflowGraph


# ============================================================================
# Hypothesis Strategies for Generating Test Data
# ============================================================================

@st.composite
def valid_node_id(draw):
    """Generate valid node IDs (lowercase alphanumeric with hyphens/underscores)."""
    length = draw(st.integers(min_value=3, max_value=20))
    chars = st.sampled_from(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
                             'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                             'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3',
                             '4', '5', '6', '7', '8', '9', '_', '-'])
    # Ensure first character is a letter
    first_char = draw(st.sampled_from(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']))
    rest_chars = [draw(chars) for _ in range(length - 1)]
    return first_char + ''.join(rest_chars)


@st.composite
def agent_node_strategy(draw, node_id=None):
    """Generate valid AgentNode instances."""
    if node_id is None:
        node_id = draw(valid_node_id())
    
    agent_id = draw(valid_node_id())
    
    return AgentNode(
        id=node_id,
        agent_id=agent_id,
        config_override=None,
        input_transform=None,
        output_transform=None,
        timeout=None
    )


@st.composite
def tree_topology_strategy(draw, min_nodes=3, max_nodes=10):
    """
    Generate valid tree topology configurations.
    
    A tree has:
    - One root node (entry node)
    - Each non-root node has exactly one parent
    - No cycles
    """
    num_nodes = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    
    # Generate unique node IDs
    node_ids = [f"node_{i}" for i in range(num_nodes)]
    
    # Create nodes
    nodes = [
        AgentNode(
            id=node_id,
            agent_id=f"agent_{i}",
            config_override=None,
            input_transform=None,
            output_transform=None,
            timeout=None
        )
        for i, node_id in enumerate(node_ids)
    ]
    
    # Entry node is always the first node
    entry_node = node_ids[0]
    
    # Create tree edges: each non-root node has exactly one parent
    edges = []
    for i in range(1, num_nodes):
        # Pick a random parent from nodes before this one
        parent_idx = draw(st.integers(min_value=0, max_value=i-1))
        parent_id = node_ids[parent_idx]
        child_id = node_ids[i]
        
        edges.append(
            AgentEdge(
                from_node=parent_id,
                to_node=child_id,
                condition=None,
                context_strategy=ContextStrategy.FULL,
                fields=None
            )
        )
    
    return TopologyConfig(
        type=TopologyType.TREE,
        nodes=nodes,
        edges=edges,
        entry_node=entry_node,
        termination_conditions=[]
    )


@st.composite
def sequential_topology_strategy(draw, min_nodes=2, max_nodes=8):
    """
    Generate valid sequential topology configurations.
    
    A sequential topology is a linear chain of nodes.
    """
    num_nodes = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    
    # Generate unique node IDs
    node_ids = [f"node_{i}" for i in range(num_nodes)]
    
    # Create nodes
    nodes = [
        AgentNode(
            id=node_id,
            agent_id=f"agent_{i}",
            config_override=None,
            input_transform=None,
            output_transform=None,
            timeout=None
        )
        for i, node_id in enumerate(node_ids)
    ]
    
    # Entry node is the first node
    entry_node = node_ids[0]
    
    # Create sequential edges
    edges = []
    for i in range(num_nodes - 1):
        edges.append(
            AgentEdge(
                from_node=node_ids[i],
                to_node=node_ids[i + 1],
                condition=None,
                context_strategy=ContextStrategy.FULL,
                fields=None
            )
        )
    
    return TopologyConfig(
        type=TopologyType.SEQUENTIAL,
        nodes=nodes,
        edges=edges,
        entry_node=entry_node,
        termination_conditions=[]
    )


@st.composite
def graph_with_cycle_strategy(draw, min_nodes=3, max_nodes=6):
    """
    Generate graph topology with at least one cycle.
    
    Creates a graph with a guaranteed cycle and termination conditions.
    """
    num_nodes = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    
    # Generate unique node IDs
    node_ids = [f"node_{i}" for i in range(num_nodes)]
    
    # Create nodes
    nodes = [
        AgentNode(
            id=node_id,
            agent_id=f"agent_{i}",
            config_override=None,
            input_transform=None,
            output_transform=None,
            timeout=None
        )
        for i, node_id in enumerate(node_ids)
    ]
    
    # Entry node is the first node
    entry_node = node_ids[0]
    
    # Create edges with at least one cycle
    edges = []
    
    # Create a cycle: 0 -> 1 -> 2 -> 0 (or similar)
    cycle_length = min(3, num_nodes)
    for i in range(cycle_length):
        from_node = node_ids[i]
        to_node = node_ids[(i + 1) % cycle_length]
        edges.append(
            AgentEdge(
                from_node=from_node,
                to_node=to_node,
                condition=None,
                context_strategy=ContextStrategy.FULL,
                fields=None
            )
        )
    
    # Add some additional random edges if we have more nodes
    for i in range(cycle_length, num_nodes):
        # Connect to a random previous node
        target_idx = draw(st.integers(min_value=0, max_value=i-1))
        edges.append(
            AgentEdge(
                from_node=node_ids[target_idx],
                to_node=node_ids[i],
                condition=None,
                context_strategy=ContextStrategy.FULL,
                fields=None
            )
        )
    
    # Add termination condition (required for cyclic graphs)
    max_iterations = draw(st.integers(min_value=1, max_value=10))
    termination_conditions = [
        TerminationCondition(
            type=TerminationConditionType.MAX_ITERATIONS,
            value=max_iterations
        )
    ]
    
    return TopologyConfig(
        type=TopologyType.GRAPH,
        nodes=nodes,
        edges=edges,
        entry_node=entry_node,
        termination_conditions=termination_conditions
    )


@st.composite
def invalid_topology_with_unreachable_nodes(draw):
    """
    Generate topology with unreachable nodes.
    
    Creates a topology where some nodes cannot be reached from the entry node.
    """
    num_nodes = draw(st.integers(min_value=4, max_value=8))
    
    # Generate unique node IDs
    node_ids = [f"node_{i}" for i in range(num_nodes)]
    
    # Create nodes
    nodes = [
        AgentNode(
            id=node_id,
            agent_id=f"agent_{i}",
            config_override=None,
            input_transform=None,
            output_transform=None,
            timeout=None
        )
        for i, node_id in enumerate(node_ids)
    ]
    
    # Entry node is the first node
    entry_node = node_ids[0]
    
    # Create edges that leave at least one node unreachable
    # Connect first half of nodes
    edges = []
    reachable_count = num_nodes // 2
    for i in range(reachable_count - 1):
        edges.append(
            AgentEdge(
                from_node=node_ids[i],
                to_node=node_ids[i + 1],
                condition=None,
                context_strategy=ContextStrategy.FULL,
                fields=None
            )
        )
    
    # Leave remaining nodes disconnected (unreachable)
    
    return TopologyConfig(
        type=TopologyType.TREE,  # Use tree type which requires all nodes reachable
        nodes=nodes,
        edges=edges,
        entry_node=entry_node,
        termination_conditions=[]
    )


# ============================================================================
# Property 5: Result routing completeness
# **Feature: industry-grade-orchestration, Property 5: Result routing completeness**
# **Validates: Requirements 2.4**
# ============================================================================

@settings(max_examples=100, deadline=None)
@given(topology=tree_topology_strategy(min_nodes=3, max_nodes=8))
def test_result_routing_completeness(topology):
    """
    Property 5: Result routing completeness
    
    For any agent node completion in a topology, all downstream nodes
    connected by edges should receive the agent's result.
    
    This test verifies that:
    1. All edges from a node are captured in the graph
    2. All successor nodes are identified correctly
    3. The routing information is complete and accessible
    """
    # Create workflow graph
    graph = WorkflowGraph(topology)
    
    # For each node in the topology
    for node in topology.nodes:
        # Get all edges originating from this node
        edges_from_node = graph.get_edges_from(node.id)
        
        # Get successor node IDs
        successors = graph.get_successors(node.id)
        
        # Property: All edges should be accounted for in successors
        edge_targets = {edge.to_node for edge in edges_from_node}
        successor_set = set(successors)
        
        assert edge_targets == successor_set, (
            f"Result routing incomplete for node {node.id}: "
            f"edges target {edge_targets} but successors are {successor_set}"
        )
        
        # Property: Each successor should have an edge from this node
        for successor_id in successors:
            matching_edges = [e for e in edges_from_node if e.to_node == successor_id]
            assert len(matching_edges) > 0, (
                f"Successor {successor_id} has no edge from {node.id}"
            )
        
        # Property: All edges should point to valid nodes
        for edge in edges_from_node:
            assert edge.to_node in graph.nodes, (
                f"Edge from {node.id} points to non-existent node {edge.to_node}"
            )


# ============================================================================
# Property 6: Invalid topology rejection
# **Feature: industry-grade-orchestration, Property 6: Invalid topology rejection**
# **Validates: Requirements 2.5**
# ============================================================================

@settings(max_examples=100, deadline=None)
@given(topology=invalid_topology_with_unreachable_nodes())
def test_invalid_topology_rejection(topology):
    """
    Property 6: Invalid topology rejection
    
    For any topology configuration with unreachable nodes (nodes with no path
    from entry node), validation should reject the configuration.
    
    This test verifies that:
    1. Unreachable nodes are detected
    2. Validation fails for invalid topologies
    3. Error messages identify the unreachable nodes
    """
    # Create workflow graph
    graph = WorkflowGraph(topology)
    
    # Validate the topology
    result = graph.validate()
    
    # Property: Topology with unreachable nodes should be invalid
    assert not result.is_valid, (
        "Topology with unreachable nodes should be marked as invalid"
    )
    
    # Property: Validation should report unreachable nodes
    has_unreachable_error = any(
        "unreachable" in error.lower() or "not found" in error.lower()
        for error in result.errors
    )
    assert has_unreachable_error, (
        f"Validation should report unreachable nodes. Errors: {result.errors}"
    )
    
    # Property: At least one error should be present
    assert len(result.errors) > 0, (
        "Invalid topology should have at least one error message"
    )


# ============================================================================
# Property 4: Graph cycle termination
# **Feature: industry-grade-orchestration, Property 4: Graph cycle termination**
# **Validates: Requirements 2.3**
# ============================================================================

@settings(max_examples=100, deadline=None)
@given(topology=graph_with_cycle_strategy(min_nodes=3, max_nodes=6))
def test_graph_cycle_termination(topology):
    """
    Property 4: Graph cycle termination
    
    For any graph topology with cycles, execution should terminate within
    the configured maximum iterations and not loop infinitely.
    
    This test verifies that:
    1. Cyclic graphs have termination conditions
    2. The termination check respects max iterations
    3. Termination is guaranteed within configured bounds
    """
    # Create workflow graph
    graph = WorkflowGraph(topology)
    
    # Validate the topology
    result = graph.validate()
    
    # Property: Cyclic graph should be valid if it has termination conditions
    assert result.is_valid, (
        f"Cyclic graph with termination conditions should be valid. Errors: {result.errors}"
    )
    
    # Property: Graph should have termination conditions
    assert len(graph.termination_conditions) > 0, (
        "Cyclic graph must have termination conditions"
    )
    
    # Property: Max iterations should be retrievable
    max_iterations = graph.get_max_iterations()
    assert max_iterations is not None, (
        "Cyclic graph should have max_iterations termination condition"
    )
    assert max_iterations > 0, (
        f"Max iterations should be positive, got {max_iterations}"
    )
    
    # Property: Termination check should work correctly
    # Should not terminate before max iterations
    for i in range(max_iterations):
        should_terminate = graph.should_terminate(i)
        assert not should_terminate, (
            f"Should not terminate at iteration {i} (max: {max_iterations})"
        )
    
    # Property: Should terminate at or after max iterations
    should_terminate = graph.should_terminate(max_iterations)
    assert should_terminate, (
        f"Should terminate at iteration {max_iterations}"
    )
    
    # Property: Should remain terminated after max iterations
    should_terminate = graph.should_terminate(max_iterations + 1)
    assert should_terminate, (
        f"Should remain terminated after max iterations"
    )


# ============================================================================
# Additional Tests for Edge Cases
# ============================================================================

def test_single_node_topology():
    """Test that single node topology works correctly."""
    node = AgentNode(
        id="single_node",
        agent_id="agent_1",
        config_override=None,
        input_transform=None,
        output_transform=None,
        timeout=None
    )
    
    topology = TopologyConfig(
        type=TopologyType.SINGLE,
        nodes=[node],
        edges=[],
        entry_node="single_node",
        termination_conditions=[]
    )
    
    graph = WorkflowGraph(topology)
    result = graph.validate()
    
    assert result.is_valid, f"Single node topology should be valid. Errors: {result.errors}"
    
    # Should have no successors
    successors = graph.get_successors("single_node")
    assert len(successors) == 0, "Single node should have no successors"
    
    # Execution plan should have one stage with one node
    plan = graph.get_execution_plan()
    assert len(plan.stages) == 1, "Single node should have one execution stage"
    assert len(plan.stages[0].nodes) == 1, "Stage should contain one node"


@settings(max_examples=100, deadline=None)
@given(topology=sequential_topology_strategy(min_nodes=2, max_nodes=8))
def test_sequential_topology_ordering(topology):
    """Test that sequential topology maintains correct ordering."""
    graph = WorkflowGraph(topology)
    result = graph.validate()
    
    assert result.is_valid, f"Sequential topology should be valid. Errors: {result.errors}"
    
    # Get execution plan
    plan = graph.get_execution_plan()
    
    # For sequential topology, each stage should have exactly one node
    for stage in plan.stages:
        assert len(stage.nodes) == 1, (
            f"Sequential topology stage should have 1 node, got {len(stage.nodes)}"
        )
    
    # Number of stages should equal number of nodes
    assert len(plan.stages) == len(topology.nodes), (
        f"Sequential topology should have {len(topology.nodes)} stages, "
        f"got {len(plan.stages)}"
    )


def test_tree_topology_parallel_execution():
    """Test that tree topology identifies parallel execution opportunities."""
    # Create a tree with parallel branches
    #       root
    #      /    \
    #   child1  child2
    #     |       |
    #  grandchild1 grandchild2
    
    nodes = [
        AgentNode(id="root", agent_id="agent_root"),
        AgentNode(id="child1", agent_id="agent_child1"),
        AgentNode(id="child2", agent_id="agent_child2"),
        AgentNode(id="grandchild1", agent_id="agent_gc1"),
        AgentNode(id="grandchild2", agent_id="agent_gc2"),
    ]
    
    edges = [
        AgentEdge(from_node="root", to_node="child1", context_strategy=ContextStrategy.FULL),
        AgentEdge(from_node="root", to_node="child2", context_strategy=ContextStrategy.FULL),
        AgentEdge(from_node="child1", to_node="grandchild1", context_strategy=ContextStrategy.FULL),
        AgentEdge(from_node="child2", to_node="grandchild2", context_strategy=ContextStrategy.FULL),
    ]
    
    topology = TopologyConfig(
        type=TopologyType.TREE,
        nodes=nodes,
        edges=edges,
        entry_node="root",
        termination_conditions=[]
    )
    
    graph = WorkflowGraph(topology)
    result = graph.validate()
    
    assert result.is_valid, f"Tree topology should be valid. Errors: {result.errors}"
    
    # Get execution plan
    plan = graph.get_execution_plan()
    
    # Should have 3 stages: [root], [child1, child2], [grandchild1, grandchild2]
    assert len(plan.stages) == 3, f"Expected 3 stages, got {len(plan.stages)}"
    
    # Stage 0: root
    assert len(plan.stages[0].nodes) == 1
    assert plan.stages[0].nodes[0].id == "root"
    
    # Stage 1: child1 and child2 (parallel)
    assert len(plan.stages[1].nodes) == 2
    stage1_ids = {node.id for node in plan.stages[1].nodes}
    assert stage1_ids == {"child1", "child2"}
    
    # Stage 2: grandchild1 and grandchild2 (parallel)
    assert len(plan.stages[2].nodes) == 2
    stage2_ids = {node.id for node in plan.stages[2].nodes}
    assert stage2_ids == {"grandchild1", "grandchild2"}
