"""
AUTOGEN 0.2 RESEARCH:
- Feature needed: Graph-based workflow topology with execution planning
- Autogen provides: GroupChat for multi-agent, initiate_chats for sequential
- Using: Custom WorkflowGraph class for arbitrary topology representation
- Documentation: https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat
- Decision: Custom implementation - Autogen provides conversation patterns but not
  graph topology abstraction with execution planning. We extend Autogen patterns
  with our topology engine to support tree and graph structures.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from src.config.topology_models import (
    AgentEdge,
    AgentNode,
    ContextStrategy,
    TerminationCondition,
    TerminationConditionType,
    TopologyConfig,
    TopologyType,
)


@dataclass
class ExecutionStage:
    """A stage containing nodes that can execute in parallel."""
    
    nodes: list[AgentNode]
    wait_for_all: bool = True  # Wait for all nodes or first completion
    
    def __post_init__(self):
        """Validate stage has at least one node."""
        if not self.nodes:
            raise ValueError("ExecutionStage must contain at least one node")


@dataclass
class ExecutionPlan:
    """Ordered execution plan with parallelization opportunities."""
    
    stages: list[ExecutionStage]
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate execution plan has at least one stage."""
        if not self.stages:
            raise ValueError("ExecutionPlan must contain at least one stage")


@dataclass
class ValidationResult:
    """Result of topology validation."""
    
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


class WorkflowGraph:
    """
    Directed graph representation of agent workflow.
    
    Supports single-agent, sequential, tree, and graph topologies with
    validation and execution plan generation.
    """
    
    def __init__(self, config: TopologyConfig):
        """
        Initialize workflow graph from topology configuration.
        
        Args:
            config: Topology configuration
        """
        self.config = config
        self.nodes: dict[str, AgentNode] = {node.id: node for node in config.nodes}
        self.edges: list[AgentEdge] = config.edges
        self.entry_node: str = config.entry_node
        self.termination_conditions: list[TerminationCondition] = config.termination_conditions
        
        # Build adjacency lists for efficient traversal
        self._adjacency: dict[str, list[str]] = self._build_adjacency()
        self._reverse_adjacency: dict[str, list[str]] = self._build_reverse_adjacency()
    
    def _build_adjacency(self) -> dict[str, list[str]]:
        """Build forward adjacency list (node -> successors)."""
        adjacency = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            adjacency[edge.from_node].append(edge.to_node)
        return adjacency
    
    def _build_reverse_adjacency(self) -> dict[str, list[str]]:
        """Build reverse adjacency list (node -> predecessors)."""
        reverse_adjacency = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            reverse_adjacency[edge.to_node].append(edge.from_node)
        return reverse_adjacency
    
    def add_node(self, node: AgentNode) -> None:
        """
        Add a node to the graph.
        
        Args:
            node: Agent node to add
            
        Raises:
            ValueError: If node with same ID already exists
        """
        if node.id in self.nodes:
            raise ValueError(f"Node with ID '{node.id}' already exists")
        
        self.nodes[node.id] = node
        self._adjacency[node.id] = []
        self._reverse_adjacency[node.id] = []
    
    def add_edge(self, edge: AgentEdge) -> None:
        """
        Add an edge to the graph.
        
        Args:
            edge: Agent edge to add
            
        Raises:
            ValueError: If edge references non-existent nodes
        """
        if edge.from_node not in self.nodes:
            raise ValueError(f"Edge from_node '{edge.from_node}' not found in graph")
        if edge.to_node not in self.nodes:
            raise ValueError(f"Edge to_node '{edge.to_node}' not found in graph")
        
        self.edges.append(edge)
        self._adjacency[edge.from_node].append(edge.to_node)
        self._reverse_adjacency[edge.to_node].append(edge.from_node)
    
    def get_node(self, node_id: str) -> Optional[AgentNode]:
        """
        Get node by ID.
        
        Args:
            node_id: Node identifier
            
        Returns:
            AgentNode or None if not found
        """
        return self.nodes.get(node_id)
    
    def get_edges_from(self, node_id: str) -> list[AgentEdge]:
        """
        Get all edges originating from a node.
        
        Args:
            node_id: Source node identifier
            
        Returns:
            List of edges from the node
        """
        return [edge for edge in self.edges if edge.from_node == node_id]
    
    def get_edges_to(self, node_id: str) -> list[AgentEdge]:
        """
        Get all edges pointing to a node.
        
        Args:
            node_id: Destination node identifier
            
        Returns:
            List of edges to the node
        """
        return [edge for edge in self.edges if edge.to_node == node_id]
    
    def get_successors(self, node_id: str) -> list[str]:
        """
        Get successor node IDs.
        
        Args:
            node_id: Node identifier
            
        Returns:
            List of successor node IDs
        """
        return self._adjacency.get(node_id, [])
    
    def get_predecessors(self, node_id: str) -> list[str]:
        """
        Get predecessor node IDs.
        
        Args:
            node_id: Node identifier
            
        Returns:
            List of predecessor node IDs
        """
        return self._reverse_adjacency.get(node_id, [])
    
    def validate(self) -> ValidationResult:
        """
        Validate the workflow graph structure.
        
        Performs comprehensive validation including:
        - Topology-specific constraints (single, sequential, tree, graph)
        - Unreachable node detection
        - Cycle detection for non-graph topologies
        - Termination condition validation for cyclic graphs
        
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        # Use the config's validate_topology method
        config_errors = self.config.validate_topology()
        for error in config_errors:
            result.add_error(error)
        
        # Additional validation for edges
        for edge in self.edges:
            # Validate selective context strategy has fields
            if edge.context_strategy == ContextStrategy.SELECTIVE and not edge.fields:
                result.add_error(
                    f"Edge {edge.from_node}->{edge.to_node}: "
                    "selective context strategy requires fields to be specified"
                )
        
        # Validate termination conditions for cyclic graphs
        if self._has_cycle() and self.config.type == TopologyType.GRAPH:
            if not self.termination_conditions:
                result.add_error(
                    "Graph topology with cycles must have termination conditions"
                )
            else:
                # Validate termination condition values
                for condition in self.termination_conditions:
                    if condition.type == TerminationConditionType.MAX_ITERATIONS:
                        if not isinstance(condition.value, int) or condition.value < 1:
                            result.add_error(
                                f"Invalid max_iterations value: {condition.value}. "
                                "Must be a positive integer"
                            )
        
        return result
    
    def _has_cycle(self) -> bool:
        """Check if graph has a cycle using DFS."""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self._adjacency:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    def _get_reachable_nodes(self, start: str) -> set[str]:
        """
        Get all nodes reachable from start node using BFS.
        
        Args:
            start: Starting node ID
            
        Returns:
            Set of reachable node IDs
        """
        visited = {start}
        queue = [start]
        
        while queue:
            current = queue.pop(0)
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return visited
    
    def get_execution_plan(self) -> ExecutionPlan:
        """
        Generate execution plan with parallelization opportunities.
        
        Uses topological sort to identify stages where nodes can execute in parallel.
        Nodes in the same stage have no dependencies on each other.
        
        Returns:
            ExecutionPlan with stages and dependencies
            
        Raises:
            ValueError: If graph has cycles (for non-graph topologies)
        """
        # For single node topology, return simple plan
        if self.config.type == TopologyType.SINGLE:
            node = list(self.nodes.values())[0]
            return ExecutionPlan(
                stages=[ExecutionStage(nodes=[node])],
                dependencies={}
            )
        
        # For graph topology with cycles, we can't do full topological sort
        # Instead, we'll create a sequential plan starting from entry node
        if self._has_cycle():
            if self.config.type != TopologyType.GRAPH:
                raise ValueError(
                    f"Cycle detected in {self.config.type.value} topology. "
                    "Only graph topology supports cycles."
                )
            
            # For cyclic graphs, create a sequential plan
            # Actual execution will handle cycles via termination conditions
            return self._create_sequential_plan()
        
        # For acyclic graphs, use topological sort to find parallelization opportunities
        return self._create_parallel_plan()
    
    def _create_sequential_plan(self) -> ExecutionPlan:
        """Create a sequential execution plan (for cyclic graphs)."""
        # Start from entry node and do BFS to get execution order
        visited = set()
        queue = [self.entry_node]
        stages = []
        dependencies = {}
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            
            visited.add(current)
            node = self.nodes[current]
            stages.append(ExecutionStage(nodes=[node]))
            
            # Track dependencies
            predecessors = self.get_predecessors(current)
            if predecessors:
                dependencies[current] = predecessors
            
            # Add successors to queue
            for successor in self._adjacency.get(current, []):
                if successor not in visited:
                    queue.append(successor)
        
        return ExecutionPlan(stages=stages, dependencies=dependencies)
    
    def _create_parallel_plan(self) -> ExecutionPlan:
        """
        Create execution plan with parallelization using topological sort.
        
        Returns:
            ExecutionPlan with parallel stages
        """
        # Calculate in-degree for each node
        in_degree = {node_id: len(self._reverse_adjacency[node_id]) for node_id in self.nodes}
        
        # Track dependencies
        dependencies = {
            node_id: list(self._reverse_adjacency[node_id])
            for node_id in self.nodes
            if self._reverse_adjacency[node_id]
        }
        
        # Find all nodes with in-degree 0 (can start immediately)
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        stages = []
        
        while queue:
            # All nodes in queue can execute in parallel (same stage)
            stage_nodes = [self.nodes[node_id] for node_id in queue]
            stages.append(ExecutionStage(nodes=stage_nodes))
            
            # Process all nodes in current stage
            next_queue = []
            for node_id in queue:
                # Reduce in-degree of successors
                for successor in self._adjacency.get(node_id, []):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        next_queue.append(successor)
            
            queue = next_queue
        
        # Check if all nodes were processed (no cycles)
        if len(stages) == 0 or sum(len(stage.nodes) for stage in stages) != len(self.nodes):
            raise ValueError("Failed to create execution plan: graph may contain cycles")
        
        return ExecutionPlan(stages=stages, dependencies=dependencies)
    
    def get_max_iterations(self) -> Optional[int]:
        """
        Get maximum iterations from termination conditions.
        
        Returns:
            Maximum iterations or None if not specified
        """
        for condition in self.termination_conditions:
            if condition.type == TerminationConditionType.MAX_ITERATIONS:
                return condition.value
        return None
    
    def should_terminate(self, iteration: int, last_message: Optional[str] = None) -> bool:
        """
        Check if execution should terminate based on conditions.
        
        Args:
            iteration: Current iteration number
            last_message: Last message in conversation (for pattern matching)
            
        Returns:
            True if execution should terminate
        """
        for condition in self.termination_conditions:
            if condition.type == TerminationConditionType.MAX_ITERATIONS:
                if iteration >= condition.value:
                    return True
            
            elif condition.type == TerminationConditionType.MESSAGE_PATTERN:
                if last_message and condition.value in last_message:
                    return True
        
        return False
