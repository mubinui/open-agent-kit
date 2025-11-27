"""Workflow validation logic for visual builder."""

from typing import Dict, List, Set

from src.api.models import (
    WorkflowConnection,
    WorkflowNode,
    WorkflowValidationError,
)


def detect_cycles(connections: List[WorkflowConnection]) -> List[List[str]]:
    """
    Detect cycles in workflow connections using DFS.
    
    Args:
        connections: List of workflow connections
        
    Returns:
        List of cycles, where each cycle is a list of node IDs
    """
    # Build adjacency list for sequential connections only
    graph: Dict[str, List[str]] = {}
    for conn in connections:
        if conn.type == "sequential":
            if conn.from_node not in graph:
                graph[conn.from_node] = []
            graph[conn.from_node].append(conn.to_node)
    
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []
    
    def dfs(node: str) -> bool:
        """DFS helper to detect cycles."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        if node in graph:
            for neighbor in graph[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True
        
        path.pop()
        rec_stack.remove(node)
        return False
    
    # Check all nodes
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return cycles


def validate_agent_references(
    nodes: List[WorkflowNode],
    available_agents: Set[str]
) -> List[WorkflowValidationError]:
    """
    Validate that all agent references in nodes exist.
    
    Args:
        nodes: List of workflow nodes
        available_agents: Set of available agent IDs
        
    Returns:
        List of validation errors
    """
    errors: List[WorkflowValidationError] = []
    
    for node in nodes:
        if node.agent_id not in available_agents:
            errors.append(
                WorkflowValidationError(
                    field=f"nodes[{node.id}].agent_id",
                    message=f"Agent '{node.agent_id}' not found",
                    error_type="missing_reference"
                )
            )
    
    return errors


def validate_connections(
    nodes: List[WorkflowNode],
    connections: List[WorkflowConnection]
) -> List[WorkflowValidationError]:
    """
    Validate workflow connections.
    
    Args:
        nodes: List of workflow nodes
        connections: List of workflow connections
        
    Returns:
        List of validation errors
    """
    errors: List[WorkflowValidationError] = []
    node_ids = {node.id for node in nodes}
    
    for i, conn in enumerate(connections):
        # Check if from_node exists
        if conn.from_node not in node_ids:
            errors.append(
                WorkflowValidationError(
                    field=f"connections[{i}].from_node",
                    message=f"Node '{conn.from_node}' not found",
                    error_type="missing_node"
                )
            )
        
        # Check if to_node exists
        if conn.to_node not in node_ids:
            errors.append(
                WorkflowValidationError(
                    field=f"connections[{i}].to_node",
                    message=f"Node '{conn.to_node}' not found",
                    error_type="missing_node"
                )
            )
        
        # Check connection type
        if conn.type not in ["sequential", "parallel"]:
            errors.append(
                WorkflowValidationError(
                    field=f"connections[{i}].type",
                    message=f"Invalid connection type '{conn.type}'. Must be 'sequential' or 'parallel'",
                    error_type="invalid_value"
                )
            )
    
    return errors


def validate_workflow(
    nodes: List[WorkflowNode],
    connections: List[WorkflowConnection],
    available_agents: Set[str]
) -> tuple[bool, List[WorkflowValidationError], List[str]]:
    """
    Validate a complete workflow configuration.
    
    Args:
        nodes: List of workflow nodes
        connections: List of workflow connections
        available_agents: Set of available agent IDs
        
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors: List[WorkflowValidationError] = []
    warnings: List[str] = []
    
    # Validate agent references
    errors.extend(validate_agent_references(nodes, available_agents))
    
    # Validate connections
    errors.extend(validate_connections(nodes, connections))
    
    # Detect cycles in sequential connections
    cycles = detect_cycles(connections)
    if cycles:
        for cycle in cycles:
            errors.append(
                WorkflowValidationError(
                    field="connections",
                    message=f"Cycle detected: {' -> '.join(cycle)}",
                    error_type="cycle_detected"
                )
            )
    
    # Check for disconnected nodes
    connected_nodes = set()
    for conn in connections:
        connected_nodes.add(conn.from_node)
        connected_nodes.add(conn.to_node)
    
    disconnected = {node.id for node in nodes} - connected_nodes
    if disconnected:
        warnings.append(f"Disconnected nodes: {', '.join(disconnected)}")
    
    is_valid = len(errors) == 0
    return is_valid, errors, warnings
