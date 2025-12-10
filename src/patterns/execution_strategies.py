"""
AUTOGEN 0.2 RESEARCH:
- Feature needed: Execution strategies for different workflow topologies (sequential, parallel, hybrid)
- Autogen provides: initiate_chat (two-agent), initiate_chats (sequential with carryover), GroupChat (multi-agent)
- Using: Custom ExecutionStrategy classes that leverage Autogen's async methods
- Documentation: https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat
- Decision: Custom implementation - Autogen provides conversation patterns but not execution strategy
  abstraction for topology-based routing. We extend Autogen's async capabilities with custom strategies
  that determine how to execute nodes based on topology and dependencies.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.patterns.topology_engine import AgentNode, ExecutionPlan, ExecutionStage, WorkflowGraph

if TYPE_CHECKING:
    from src.patterns.execution_engine import ExecutionContext, AgentResult, AgentStatus


class ExecutionStrategyType(str, Enum):
    """Type of execution strategy."""
    
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"
    SELECTOR = "selector"


@dataclass
class ExecutionStrategyConfig:
    """Configuration for execution strategy."""
    
    strategy_type: ExecutionStrategyType
    max_parallel_branches: int = 10
    enable_conditional_routing: bool = True
    optimize_execution_plan: bool = True


class ExecutionStrategy(ABC):
    """
    Abstract base class for execution strategies.
    
    Execution strategies determine how to execute agent nodes based on
    workflow topology and dependencies.
    """
    
    def __init__(self, config: ExecutionStrategyConfig):
        """
        Initialize execution strategy.
        
        Args:
            config: Strategy configuration
        """
        self.config = config
    
    @abstractmethod
    async def execute(
        self,
        plan: ExecutionPlan,
        context: Any,  # ExecutionContext
        workflow_graph: WorkflowGraph,
        executor: Any,  # ExecutionEngine instance
    ) -> None:
        """
        Execute the workflow according to the strategy.
        
        Args:
            plan: Execution plan with stages
            context: Execution context
            workflow_graph: Workflow graph for termination checks
            executor: Execution engine instance for executing nodes
        """
        pass
    
    def _should_execute_node(
        self,
        node: AgentNode,
        context: Any,  # ExecutionContext
        workflow_graph: WorkflowGraph,
    ) -> bool:
        """
        Check if a node should be executed based on conditional routing.
        
        Args:
            node: Agent node to check
            context: Execution context
            workflow_graph: Workflow graph
            
        Returns:
            True if node should be executed
        """
        # Import at runtime to avoid circular dependency
        from src.patterns.execution_engine import AgentStatus
        
        if not self.config.enable_conditional_routing:
            return True
        
        # Get incoming edges to this node
        incoming_edges = workflow_graph.get_edges_to(node.id)
        
        # If no incoming edges, always execute (entry node)
        if not incoming_edges:
            return True
        
        # Check if any incoming edge has a condition
        for edge in incoming_edges:
            if edge.condition:
                # Evaluate condition
                # For now, we'll use a simple evaluation
                # In production, this would use a safe expression evaluator
                try:
                    # Get the result from the source node
                    source_result = context.get_agent_result(edge.from_node)
                    if source_result and source_result.status == AgentStatus.SUCCESS:
                        # Simple condition evaluation
                        # TODO: Implement proper expression evaluation
                        return True
                except Exception:
                    # If condition evaluation fails, don't execute
                    return False
        
        # If no conditions or all conditions passed, execute
        return True


class SequentialExecutionStrategy(ExecutionStrategy):
    """
    Sequential execution strategy.
    
    Executes all nodes in strict sequential order, one at a time.
    No parallelization is performed.
    """
    
    def __init__(self, config: Optional[ExecutionStrategyConfig] = None):
        """Initialize sequential execution strategy."""
        if config is None:
            config = ExecutionStrategyConfig(strategy_type=ExecutionStrategyType.SEQUENTIAL)
        super().__init__(config)
    
    async def execute(
        self,
        plan: ExecutionPlan,
        context: Any,  # ExecutionContext
        workflow_graph: WorkflowGraph,
        executor: Any,
    ) -> None:
        """
        Execute workflow sequentially.
        
        Args:
            plan: Execution plan with stages
            context: Execution context
            workflow_graph: Workflow graph
            executor: Execution engine instance
        """
        max_iterations = workflow_graph.get_max_iterations()
        
        for stage in plan.stages:
            # Check termination conditions
            if workflow_graph.should_terminate(
                context.iteration,
                context.conversation_history[-1]["content"] if context.conversation_history else None
            ):
                break
            
            # Check max iterations
            if max_iterations and context.iteration >= max_iterations:
                break
            
            # Execute all nodes in stage sequentially
            for node in stage.nodes:
                # Check if node should be executed based on conditions
                if self._should_execute_node(node, context, workflow_graph):
                    await executor.execute_agent_node(node, context)
            
            context.iteration += 1


class ParallelExecutionStrategy(ExecutionStrategy):
    """
    Parallel execution strategy.
    
    Executes independent nodes in parallel within each stage.
    Nodes in the same stage have no dependencies on each other.
    """
    
    def __init__(self, config: Optional[ExecutionStrategyConfig] = None):
        """Initialize parallel execution strategy."""
        if config is None:
            config = ExecutionStrategyConfig(strategy_type=ExecutionStrategyType.PARALLEL)
        super().__init__(config)
    
    async def execute(
        self,
        plan: ExecutionPlan,
        context: Any,  # ExecutionContext
        workflow_graph: WorkflowGraph,
        executor: Any,
    ) -> None:
        """
        Execute workflow with parallel execution of independent nodes.
        
        Args:
            plan: Execution plan with stages
            context: Execution context
            workflow_graph: Workflow graph
            executor: Execution engine instance
        """
        max_iterations = workflow_graph.get_max_iterations()
        
        for stage in plan.stages:
            # Check termination conditions
            if workflow_graph.should_terminate(
                context.iteration,
                context.conversation_history[-1]["content"] if context.conversation_history else None
            ):
                break
            
            # Check max iterations
            if max_iterations and context.iteration >= max_iterations:
                break
            
            # Filter nodes based on conditional routing
            nodes_to_execute = [
                node for node in stage.nodes
                if self._should_execute_node(node, context, workflow_graph)
            ]
            
            # Execute all nodes in stage in parallel
            if len(nodes_to_execute) > 1:
                # Limit parallelism to max_parallel_branches
                if len(nodes_to_execute) > self.config.max_parallel_branches:
                    # Execute in batches
                    for i in range(0, len(nodes_to_execute), self.config.max_parallel_branches):
                        batch = nodes_to_execute[i:i + self.config.max_parallel_branches]
                        await executor.execute_parallel_branch(batch, context)
                else:
                    # Execute all in parallel
                    await executor.execute_parallel_branch(nodes_to_execute, context)
            elif len(nodes_to_execute) == 1:
                # Single node, execute directly
                await executor.execute_agent_node(nodes_to_execute[0], context)
            
            context.iteration += 1


class HybridExecutionStrategy(ExecutionStrategy):
    """
    Hybrid execution strategy with dependency resolution.
    
    Intelligently parallelizes independent branches while respecting dependencies.
    Uses the execution plan's stage structure to identify parallelization opportunities.
    """
    
    def __init__(self, config: Optional[ExecutionStrategyConfig] = None):
        """Initialize hybrid execution strategy."""
        if config is None:
            config = ExecutionStrategyConfig(strategy_type=ExecutionStrategyType.HYBRID)
        super().__init__(config)
    
    async def execute(
        self,
        plan: ExecutionPlan,
        context: Any,  # ExecutionContext
        workflow_graph: WorkflowGraph,
        executor: Any,
    ) -> None:
        """
        Execute workflow with hybrid strategy.
        
        Parallelizes independent branches while respecting dependencies.
        
        Args:
            plan: Execution plan with stages
            context: Execution context
            workflow_graph: Workflow graph
            executor: Execution engine instance
        """
        max_iterations = workflow_graph.get_max_iterations()
        
        # Optimize execution plan if enabled
        if self.config.optimize_execution_plan:
            plan = self._optimize_plan(plan, workflow_graph)
        
        for stage in plan.stages:
            # Check termination conditions
            if workflow_graph.should_terminate(
                context.iteration,
                context.conversation_history[-1]["content"] if context.conversation_history else None
            ):
                break
            
            # Check max iterations
            if max_iterations and context.iteration >= max_iterations:
                break
            
            # Analyze dependencies within stage
            independent_groups = self._group_independent_nodes(
                stage.nodes,
                plan.dependencies,
                context
            )
            
            # Execute each group
            for group in independent_groups:
                # Filter nodes based on conditional routing
                nodes_to_execute = [
                    node for node in group
                    if self._should_execute_node(node, context, workflow_graph)
                ]
                
                if not nodes_to_execute:
                    continue
                
                # Execute group based on size
                if len(nodes_to_execute) > 1:
                    # Parallel execution for multiple nodes
                    if len(nodes_to_execute) > self.config.max_parallel_branches:
                        # Execute in batches
                        for i in range(0, len(nodes_to_execute), self.config.max_parallel_branches):
                            batch = nodes_to_execute[i:i + self.config.max_parallel_branches]
                            await executor.execute_parallel_branch(batch, context)
                    else:
                        await executor.execute_parallel_branch(nodes_to_execute, context)
                else:
                    # Sequential execution for single node
                    await executor.execute_agent_node(nodes_to_execute[0], context)
            
            context.iteration += 1
    
    def _optimize_plan(
        self,
        plan: ExecutionPlan,
        workflow_graph: WorkflowGraph,
    ) -> ExecutionPlan:
        """
        Optimize execution plan by identifying additional parallelization opportunities.
        
        Args:
            plan: Original execution plan
            workflow_graph: Workflow graph
            
        Returns:
            Optimized execution plan
        """
        # For now, return the original plan
        # In a full implementation, this would analyze the plan and potentially
        # reorganize stages to maximize parallelization
        return plan
    
    def _group_independent_nodes(
        self,
        nodes: List[AgentNode],
        dependencies: Dict[str, List[str]],
        context: Any,  # ExecutionContext
    ) -> List[List[AgentNode]]:
        """
        Group nodes into independent execution groups.
        
        Nodes in the same group have no dependencies on each other and can
        execute in parallel. Groups must execute sequentially.
        
        Args:
            nodes: List of nodes in the stage
            dependencies: Dependency map
            context: Execution context
            
        Returns:
            List of node groups (each group can execute in parallel)
        """
        # Build dependency graph for nodes in this stage
        node_ids = {node.id for node in nodes}
        stage_dependencies = {
            node.id: [dep for dep in dependencies.get(node.id, []) if dep in node_ids]
            for node in nodes
        }
        
        # Find nodes with no dependencies in this stage (can execute first)
        groups = []
        remaining_nodes = {node.id: node for node in nodes}
        completed_nodes = set()
        
        while remaining_nodes:
            # Find nodes whose dependencies are all completed
            ready_nodes = []
            for node_id, node in remaining_nodes.items():
                node_deps = stage_dependencies.get(node_id, [])
                # Check if all dependencies are completed
                if all(dep in completed_nodes or dep not in node_ids for dep in node_deps):
                    # Also check if dependencies from previous stages are completed
                    all_deps = dependencies.get(node_id, [])
                    prev_stage_deps = [dep for dep in all_deps if dep not in node_ids]
                    if all(context.get_agent_result(dep) is not None for dep in prev_stage_deps):
                        ready_nodes.append(node)
            
            if not ready_nodes:
                # No nodes are ready, but we have remaining nodes
                # This shouldn't happen with a valid execution plan
                # Execute remaining nodes sequentially as fallback
                ready_nodes = list(remaining_nodes.values())
            
            # Add ready nodes as a group
            groups.append(ready_nodes)
            
            # Mark nodes as completed
            for node in ready_nodes:
                completed_nodes.add(node.id)
                remaining_nodes.pop(node.id)
        
        return groups


class SelectorExecutionStrategy(ExecutionStrategy):
    """
    Selector execution strategy for routing-based workflows.
    
    Uses a selector agent to analyze user intent and route to specialized
    domain agents. The selector agent returns a JSON routing decision that
    determines which agent handles the query.
    """
    
    def __init__(self, config: Optional[ExecutionStrategyConfig] = None):
        """Initialize selector execution strategy."""
        if config is None:
            config = ExecutionStrategyConfig(strategy_type=ExecutionStrategyType.SELECTOR)
        super().__init__(config)
    
    async def execute(
        self,
        plan: ExecutionPlan,
        context: Any,  # ExecutionContext
        workflow_graph: WorkflowGraph,
        executor: Any,
    ) -> None:
        """
        Execute workflow using selector-based routing.
        
        1. Execute the selector agent to get routing decision
        2. Parse the routing decision JSON
        3. Route to the appropriate domain agent
        
        Args:
            plan: Execution plan with stages
            context: Execution context
            workflow_graph: Workflow graph
            executor: Execution engine instance
        """
        import json
        import structlog
        
        logger = structlog.get_logger(__name__)
        
        max_iterations = workflow_graph.get_max_iterations() or 10
        
        # Get selector config from workflow graph
        selector_config = getattr(workflow_graph.config, 'selector_config', None)
        if not selector_config:
            logger.error("selector_config_missing", workflow_id=context.workflow_id)
            return
        
        routing_agents = selector_config.get('routing_agents', {})
        default_agent = selector_config.get('default_agent')
        max_routing_attempts = selector_config.get('max_routing_attempts', 3)
        
        # Find the selector agent node (entry node)
        selector_node = None
        for stage in plan.stages:
            for node in stage.nodes:
                if node.id == workflow_graph.config.entry_node:
                    selector_node = node
                    break
            if selector_node:
                break
        
        if not selector_node:
            logger.error("selector_node_not_found", entry_node=workflow_graph.config.entry_node)
            return
        
        # Execute selector agent to get routing decision
        await executor.execute_agent_node(selector_node, context)
        
        # Get the selector's response
        selector_result = context.get_agent_result(selector_node.id)
        if not selector_result or not selector_result.output:
            logger.error("selector_no_output", node_id=selector_node.id)
            return
        
        # Parse routing decision from selector output
        routing_decision = self._parse_routing_decision(selector_result.output, logger)
        
        if not routing_decision:
            logger.warning("routing_decision_parse_failed", output=str(selector_result.output)[:200])
            return
        
        # Check if clarification is needed
        if routing_decision.get('requires_clarification'):
            # The selector agent's response already contains the clarification prompt
            # No further routing needed
            logger.info("clarification_required", prompt=routing_decision.get('clarification_prompt'))
            return
        
        # Get the target agent based on domain
        domain = routing_decision.get('domain', 'general')
        target_agent_id = routing_agents.get(domain, default_agent)
        
        if not target_agent_id:
            logger.warning("no_target_agent_for_domain", domain=domain)
            return
        
        # Find the target agent node
        target_node = None
        for stage in plan.stages:
            for node in stage.nodes:
                if node.agent_id == target_agent_id:
                    target_node = node
                    break
            if target_node:
                break
        
        # If target node not in plan, create a temporary node
        if not target_node:
            from src.patterns.topology_engine import AgentNode
            target_node = AgentNode(
                id=target_agent_id,
                agent_id=target_agent_id,
                timeout=300.0,
            )
        
        # Add routing context to metadata
        context.metadata['routing_decision'] = routing_decision
        context.metadata['routed_to_agent'] = target_agent_id
        context.metadata['routed_domain'] = domain
        
        # Execute the target agent
        logger.info(
            "routing_to_agent",
            domain=domain,
            target_agent=target_agent_id,
            intent=routing_decision.get('intent'),
        )
        
        await executor.execute_agent_node(target_node, context)
        
        context.iteration += 1
    
    def _parse_routing_decision(self, output: Any, logger: Any) -> Optional[Dict[str, Any]]:
        """
        Parse routing decision from selector agent output.
        
        Args:
            output: Selector agent output (may be string or dict)
            logger: Logger instance
            
        Returns:
            Parsed routing decision dict or None
        """
        import json
        import re
        
        if isinstance(output, dict):
            return output
        
        if not isinstance(output, str):
            output = str(output)
        
        # Try to extract JSON from the output
        # The selector agent should return JSON, but it might be wrapped in text
        
        # First, try direct JSON parse
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in the output
        json_match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON with nested objects
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        logger.warning("could_not_parse_routing_decision", output=output[:200])
        return None


class ExecutionStrategyFactory:
    """Factory for creating execution strategies."""
    
    @staticmethod
    def create_strategy(
        strategy_type: ExecutionStrategyType,
        config: Optional[ExecutionStrategyConfig] = None,
    ) -> ExecutionStrategy:
        """
        Create an execution strategy.
        
        Args:
            strategy_type: Type of strategy to create
            config: Optional strategy configuration
            
        Returns:
            ExecutionStrategy instance
            
        Raises:
            ValueError: If strategy type is unknown
        """
        if config is None:
            config = ExecutionStrategyConfig(strategy_type=strategy_type)
        
        if strategy_type == ExecutionStrategyType.SEQUENTIAL:
            return SequentialExecutionStrategy(config)
        elif strategy_type == ExecutionStrategyType.PARALLEL:
            return ParallelExecutionStrategy(config)
        elif strategy_type == ExecutionStrategyType.HYBRID:
            return HybridExecutionStrategy(config)
        elif strategy_type == ExecutionStrategyType.SELECTOR:
            return SelectorExecutionStrategy(config)
        else:
            raise ValueError(f"Unknown execution strategy type: {strategy_type}")
    
    @staticmethod
    def create_from_topology(
        workflow_graph: WorkflowGraph,
        config: Optional[ExecutionStrategyConfig] = None,
    ) -> ExecutionStrategy:
        """
        Create an appropriate execution strategy based on workflow topology.
        
        Args:
            workflow_graph: Workflow graph
            config: Optional strategy configuration
            
        Returns:
            ExecutionStrategy instance
        """
        from src.config.topology_models import TopologyType
        
        # Determine strategy based on topology type
        if workflow_graph.config.type == TopologyType.SINGLE:
            strategy_type = ExecutionStrategyType.SEQUENTIAL
        elif workflow_graph.config.type == TopologyType.SEQUENTIAL:
            strategy_type = ExecutionStrategyType.SEQUENTIAL
        elif workflow_graph.config.type == TopologyType.TREE:
            strategy_type = ExecutionStrategyType.PARALLEL
        elif workflow_graph.config.type == TopologyType.GRAPH:
            strategy_type = ExecutionStrategyType.HYBRID
        else:
            strategy_type = ExecutionStrategyType.HYBRID
        
        return ExecutionStrategyFactory.create_strategy(strategy_type, config)
