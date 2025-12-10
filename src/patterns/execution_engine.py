"""
AUTOGEN 0.2 RESEARCH:
- Feature needed: Async execution engine with worker pool for concurrent agent tasks
- Autogen provides: ConversableAgent with async support via a_initiate_chat
- Using: Autogen's async methods (a_initiate_chat, a_generate_reply) with custom worker pool
- Documentation: https://microsoft.github.io/autogen/0.2/docs/reference/agentchat/conversable_agent
- Decision: Extend Autogen's async capabilities with custom ExecutionEngine for workflow
  orchestration, worker pool management, and resource limits. Autogen provides agent-level
  async but not workflow-level execution management.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

from src.config.execution_models import ExecutionConfig, RetryConfig
from src.patterns.topology_engine import AgentNode, ExecutionPlan, WorkflowGraph
from src.patterns.execution_strategies import (
    ExecutionStrategy,
    ExecutionStrategyFactory,
    ExecutionStrategyType,
)
from src.patterns.error_handler import ErrorHandler, ErrorResolution
from src.patterns.context_passing import (
    ContextPassingEngine,
    ContextPassingConfig,
    ContextStrategy as ContextPassingStrategy,
)
from src.observability import metrics
from src.audit_logging.logger import (
    bind_correlation_ids,
    log_agent_execution_start,
    log_agent_execution_end,
    log_workflow_execution_start,
    log_workflow_execution_end,
    log_llm_call,
    log_error_context,
)
from src.observability.tracing import (
    trace_workflow_execution,
    trace_agent_execution,
    trace_execution_stage,
    add_span_event,
    set_span_error,
)

logger = structlog.get_logger(__name__)


class ExecutionStatus(str, Enum):
    """Status of workflow execution."""
    
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Status of agent execution."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class AgentResult:
    """Result of single agent execution."""
    
    agent_id: str
    node_id: str
    status: AgentStatus
    output: Any
    execution_time: float
    cache_hit: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of workflow execution."""
    
    session_id: UUID
    workflow_id: str
    status: ExecutionStatus
    final_response: str
    agent_results: Dict[str, AgentResult]
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    """Task for agent execution in worker pool."""
    
    task_id: UUID
    node: AgentNode
    context: 'ExecutionContext'
    priority: int = 0
    timeout: float = 300.0
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionContext:
    """Maintains execution state and context for a workflow run."""
    
    session_id: UUID
    workflow_id: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    iteration: int = 0
    _workflow_graph: Optional['WorkflowGraph'] = None
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_agent_result(self, node_id: str) -> Optional[AgentResult]:
        """Get result for a specific agent node."""
        return self.agent_results.get(node_id)
    
    def set_agent_result(self, node_id: str, result: AgentResult) -> None:
        """Set result for a specific agent node."""
        self.agent_results[node_id] = result
    
    def set_workflow_graph(self, graph: 'WorkflowGraph') -> None:
        """Set workflow graph for context passing."""
        self._workflow_graph = graph


class WorkerPool:
    """Manages async worker tasks for agent execution."""
    
    def __init__(self, max_workers: int, queue_size: int):
        """
        Initialize worker pool.
        
        Args:
            max_workers: Maximum number of concurrent workers
            queue_size: Maximum size of task queue
        """
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.task_queue: asyncio.Queue[AgentTask] = asyncio.Queue(maxsize=queue_size)
        self.workers: List[asyncio.Task] = []
        self.active_tasks: Dict[UUID, asyncio.Task] = {}
        self._shutdown = False
    
    async def start(self) -> None:
        """Start worker pool."""
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes tasks from queue."""
        while not self._shutdown:
            try:
                # Wait for task with timeout to allow checking shutdown flag
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                # Process the task
                # Note: Actual task execution is handled by ExecutionEngine
                # Workers just manage the queue
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # No task available, continue loop
                continue
            except Exception as e:
                # Log error but continue processing
                print(f"Worker {worker_id} error: {e}")
    
    async def submit_task(self, task: AgentTask) -> asyncio.Future:
        """
        Submit a task to the worker pool.
        
        Args:
            task: Agent task to execute
            
        Returns:
            Future that will contain the task result
            
        Raises:
            asyncio.QueueFull: If queue is full
        """
        # Create a future for the result
        future: asyncio.Future[AgentResult] = asyncio.Future()
        
        # Store the future with task ID
        self.active_tasks[task.task_id] = future
        
        # Add task to queue (will raise QueueFull if full)
        await self.task_queue.put(task)
        
        return future
    
    def complete_task(self, task_id: UUID, result: AgentResult) -> None:
        """
        Mark a task as complete with result.
        
        Args:
            task_id: Task identifier
            result: Task result
        """
        future = self.active_tasks.pop(task_id, None)
        if future and not future.done():
            future.set_result(result)
    
    def fail_task(self, task_id: UUID, error: Exception) -> None:
        """
        Mark a task as failed with error.
        
        Args:
            task_id: Task identifier
            error: Exception that caused failure
        """
        future = self.active_tasks.pop(task_id, None)
        if future and not future.done():
            future.set_exception(error)
    
    async def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown worker pool.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        self._shutdown = True
        
        if wait:
            # Wait for queue to be empty
            await self.task_queue.join()
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Cancel any remaining active tasks
        for future in self.active_tasks.values():
            if not future.done():
                future.cancel()
        
        self.active_tasks.clear()


class ExecutionEngine:
    """Async execution engine with worker pool management."""
    
    def __init__(
        self,
        config: ExecutionConfig,
        agent_factory: Optional[Any] = None,
        execution_strategy: Optional[ExecutionStrategy] = None,
        error_handler: Optional[ErrorHandler] = None,
        context_passing_config: Optional[ContextPassingConfig] = None,
    ):
        """
        Initialize execution engine.
        
        Args:
            config: Execution configuration
            agent_factory: Factory for creating agent instances
            execution_strategy: Optional execution strategy (will be auto-selected if not provided)
            error_handler: Optional error handler (will be created with config if not provided)
            context_passing_config: Optional context passing configuration
        """
        self.config = config
        self.agent_factory = agent_factory
        self.execution_strategy = execution_strategy
        self.error_handler = error_handler or ErrorHandler(config.retry_strategy)
        self.context_engine = ContextPassingEngine(context_passing_config)
        self.worker_pool = WorkerPool(
            max_workers=config.max_workers,
            queue_size=config.queue_size
        )
        self._started = False
        self._active_workflows: Dict[UUID, asyncio.Task] = {}
        
        # Resource management
        self._workflow_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._workflow_execution_counts: Dict[str, int] = {}
        self._pending_requests: Dict[str, asyncio.Queue] = {}
    
    async def start(self) -> None:
        """Start the execution engine."""
        if not self._started:
            await self.worker_pool.start()
            self._started = True
    
    async def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the execution engine.
        
        Args:
            wait: Whether to wait for pending workflows to complete
        """
        if self._started:
            # Cancel active workflows if not waiting
            if not wait:
                for workflow_task in self._active_workflows.values():
                    workflow_task.cancel()
            
            # Wait for workflows to complete
            if self._active_workflows:
                await asyncio.gather(
                    *self._active_workflows.values(),
                    return_exceptions=True
                )
            
            # Shutdown worker pool
            await self.worker_pool.shutdown(wait=wait)
            self._started = False
    
    def _get_workflow_semaphore(self, workflow_id: str) -> asyncio.Semaphore:
        """
        Get or create semaphore for workflow resource limiting.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Semaphore for the workflow
        """
        if workflow_id not in self._workflow_semaphores:
            max_concurrent = self.config.resource_limits.max_concurrent_executions
            self._workflow_semaphores[workflow_id] = asyncio.Semaphore(max_concurrent)
            self._workflow_execution_counts[workflow_id] = 0
        return self._workflow_semaphores[workflow_id]
    
    def _get_pending_queue(self, workflow_id: str) -> asyncio.Queue:
        """
        Get or create pending request queue for workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Queue for pending requests
        """
        if workflow_id not in self._pending_requests:
            self._pending_requests[workflow_id] = asyncio.Queue()
        return self._pending_requests[workflow_id]
    
    def get_workflow_execution_count(self, workflow_id: str) -> int:
        """
        Get current execution count for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Number of currently executing workflows
        """
        return self._workflow_execution_counts.get(workflow_id, 0)
    
    async def execute_workflow(
        self,
        workflow_id: str,
        session_id: UUID,
        message: str,
        context: Dict[str, Any],
        workflow_graph: WorkflowGraph,
        timeout: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute a workflow using the topology graph with resource limits.
        
        Args:
            workflow_id: Workflow identifier
            session_id: Session identifier
            message: Initial message
            context: Additional context
            workflow_graph: Workflow topology graph
            timeout: Optional timeout override (uses config default if not provided)
            
        Returns:
            ExecutionResult with workflow outcome
        """
        start_time = time.time()
        
        # Bind correlation IDs for logging
        bind_correlation_ids(
            session_id=session_id,
            workflow_id=workflow_id,
        )
        
        # Log workflow execution start
        log_workflow_execution_start(
            logger,
            workflow_id=workflow_id,
            session_id=str(session_id),
            message=message,
        )
        
        # Start distributed tracing span
        topology_type = workflow_graph.topology_type.value if hasattr(workflow_graph, 'topology_type') else None
        span = trace_workflow_execution(
            workflow_id=workflow_id,
            session_id=str(session_id),
            topology_type=topology_type,
        )
        
        try:
            # Get semaphore for resource limiting
            semaphore = self._get_workflow_semaphore(workflow_id)
        
            # Try to acquire semaphore (non-blocking check)
            if semaphore.locked() and self._workflow_execution_counts.get(workflow_id, 0) >= self.config.resource_limits.max_concurrent_executions:
                # Resource limit reached - track metric
                metrics.track_workflow_resource_limit_rejection(workflow_id)
                
                # Add span event
                add_span_event(span, "resource_limit_reached", {
                    "max_concurrent": self.config.resource_limits.max_concurrent_executions,
                    "current_count": self._workflow_execution_counts.get(workflow_id, 0),
                })
                
                result = ExecutionResult(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    status=ExecutionStatus.FAILURE,
                    final_response=f"Resource limit reached: maximum {self.config.resource_limits.max_concurrent_executions} concurrent executions for workflow {workflow_id}",
                    agent_results={},
                    execution_time=time.time() - start_time,
                    metadata={"error": "resource_limit_reached", "max_concurrent": self.config.resource_limits.max_concurrent_executions}
                )
                
                # Log workflow end
                log_workflow_execution_end(
                    logger,
                    workflow_id=workflow_id,
                    session_id=str(session_id),
                    status="failure",
                    execution_time=result.execution_time,
                    agent_count=0,
                    final_response=result.final_response,
                )
                
                return result
        
            # Acquire semaphore
            async with semaphore:
                # Increment execution count
                self._workflow_execution_counts[workflow_id] = self._workflow_execution_counts.get(workflow_id, 0) + 1
                
                # Track active executions
                metrics.track_workflow_execution_active(workflow_id, self._workflow_execution_counts[workflow_id])
                
                # Add span event
                add_span_event(span, "workflow_started", {
                    "active_executions": self._workflow_execution_counts[workflow_id],
                })
                
                try:
                    # Determine timeout
                    workflow_timeout = timeout or self.config.resource_limits.max_execution_time
                    
                    # Execute workflow with timeout
                    result = await asyncio.wait_for(
                        self._execute_workflow_internal(
                            workflow_id,
                            session_id,
                            message,
                            context,
                            workflow_graph
                        ),
                        timeout=workflow_timeout
                    )
                    
                    # Track execution time
                    metrics.track_execution_time("workflow", workflow_id, time.time() - start_time)
                    
                    # Add span event
                    add_span_event(span, "workflow_completed", {
                        "status": result.status.value,
                        "agent_count": len(result.agent_results),
                        "execution_time": result.execution_time,
                    })
                    
                    # Log workflow end
                    log_workflow_execution_end(
                        logger,
                        workflow_id=workflow_id,
                        session_id=str(session_id),
                        status=result.status.value,
                        execution_time=result.execution_time,
                        agent_count=len(result.agent_results),
                        final_response=result.final_response,
                    )
                    
                    return result
                    
                except asyncio.TimeoutError:
                    # Track timeout
                    metrics.track_workflow_timeout(workflow_id)
                    
                    # Add span event
                    add_span_event(span, "workflow_timeout", {
                        "timeout_seconds": workflow_timeout,
                    })
                    
                    result = ExecutionResult(
                        session_id=session_id,
                        workflow_id=workflow_id,
                        status=ExecutionStatus.TIMEOUT,
                        final_response=f"Workflow execution timed out after {workflow_timeout}s",
                        agent_results={},
                        execution_time=time.time() - start_time,
                        metadata={"error": "timeout", "timeout_seconds": workflow_timeout}
                    )
                    
                    # Log workflow end
                    log_workflow_execution_end(
                        logger,
                        workflow_id=workflow_id,
                        session_id=str(session_id),
                        status="timeout",
                        execution_time=result.execution_time,
                        agent_count=0,
                    )
                    
                    return result
                finally:
                    # Decrement execution count
                    self._workflow_execution_counts[workflow_id] = max(0, self._workflow_execution_counts.get(workflow_id, 1) - 1)
                    
                    # Update active executions metric
                    metrics.track_workflow_execution_active(workflow_id, self._workflow_execution_counts[workflow_id])
        
        finally:
            # End tracing span
            if span is not None:
                span.end()
    
    async def _execute_workflow_internal(
        self,
        workflow_id: str,
        session_id: UUID,
        message: str,
        context: Dict[str, Any],
        workflow_graph: WorkflowGraph,
    ) -> ExecutionResult:
        """
        Internal workflow execution without resource management.
        
        Args:
            workflow_id: Workflow identifier
            session_id: Session identifier
            message: Initial message
            context: Additional context
            workflow_graph: Workflow topology graph
            
        Returns:
            ExecutionResult with workflow outcome
        """
        start_time = time.time()
        
        # Create execution context
        exec_context = ExecutionContext(
            session_id=session_id,
            workflow_id=workflow_id,
            metadata=context
        )
        exec_context.add_message("user", message)
        exec_context.set_workflow_graph(workflow_graph)
        
        # Validate workflow graph
        validation = workflow_graph.validate()
        if not validation.is_valid:
            return ExecutionResult(
                session_id=session_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.FAILURE,
                final_response=f"Invalid workflow: {', '.join(validation.errors)}",
                agent_results={},
                execution_time=time.time() - start_time,
                metadata={"validation_errors": validation.errors}
            )
        
        # Get execution plan
        try:
            execution_plan = workflow_graph.get_execution_plan()
        except ValueError as e:
            return ExecutionResult(
                session_id=session_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.FAILURE,
                final_response=f"Failed to create execution plan: {str(e)}",
                agent_results={},
                execution_time=time.time() - start_time,
                metadata={"error": str(e)}
            )
        
        # Execute the workflow using strategy
        try:
            # Select execution strategy if not provided
            strategy = self.execution_strategy
            if strategy is None:
                strategy = ExecutionStrategyFactory.create_from_topology(workflow_graph)
            
            await strategy.execute(execution_plan, exec_context, workflow_graph, self)
            
            # Determine final status
            failed_agents = [
                r for r in exec_context.agent_results.values()
                if r.status != AgentStatus.SUCCESS
            ]
            
            if not failed_agents:
                status = ExecutionStatus.SUCCESS
            elif len(failed_agents) < len(exec_context.agent_results):
                status = ExecutionStatus.PARTIAL_FAILURE
            else:
                status = ExecutionStatus.FAILURE
            
            # Get final response (from last agent or error message)
            final_response = self._get_final_response(exec_context)
            
            return ExecutionResult(
                session_id=session_id,
                workflow_id=workflow_id,
                status=status,
                final_response=final_response,
                agent_results=exec_context.agent_results,
                execution_time=time.time() - start_time,
                metadata=exec_context.metadata
            )
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                session_id=session_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.TIMEOUT,
                final_response="Workflow execution timed out",
                agent_results=exec_context.agent_results,
                execution_time=time.time() - start_time,
                metadata=exec_context.metadata
            )
        except Exception as e:
            return ExecutionResult(
                session_id=session_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.FAILURE,
                final_response=f"Workflow execution failed: {str(e)}",
                agent_results=exec_context.agent_results,
                execution_time=time.time() - start_time,
                metadata={"error": str(e), **exec_context.metadata}
            )
    
    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
        workflow_graph: WorkflowGraph,
    ) -> None:
        """
        Execute an execution plan stage by stage (legacy method).
        
        This method is kept for backward compatibility. New code should use
        execution strategies instead.
        
        Args:
            plan: Execution plan with stages
            context: Execution context
            workflow_graph: Workflow graph for termination checks
        """
        # Use hybrid strategy as default
        strategy = ExecutionStrategyFactory.create_strategy(ExecutionStrategyType.HYBRID)
        await strategy.execute(plan, context, workflow_graph, self)
    
    async def execute_agent_node(
        self,
        node: AgentNode,
        context: ExecutionContext,
    ) -> AgentResult:
        """
        Execute a single agent node.
        
        Args:
            node: Agent node to execute
            context: Execution context
            
        Returns:
            AgentResult with execution outcome
        """
        start_time = time.time()
        
        # Bind correlation IDs for this agent
        bind_correlation_ids(
            session_id=context.session_id,
            workflow_id=context.workflow_id,
            agent_id=node.agent_id,
            node_id=node.id,
        )
        
        # Prepare input message
        input_message = self._prepare_input(node, context)
        
        # Log agent execution start
        log_agent_execution_start(
            logger,
            agent_id=node.agent_id,
            node_id=node.id,
            workflow_id=context.workflow_id,
            input_message=input_message,
        )
        
        # Start distributed tracing span
        span = trace_agent_execution(
            agent_id=node.agent_id,
            node_id=node.id,
            workflow_id=context.workflow_id,
        )
        
        try:
            # Get agent instance from factory
            if self.agent_factory is None:
                raise RuntimeError("Agent factory not configured")
            
            agent = await self.agent_factory.get_agent(node.agent_id)
            
            # Add span event
            add_span_event(span, "agent_loaded", {
                "agent_type": type(agent).__name__,
            })
            
            # Execute agent with retry logic
            # Note: Timeout is applied per-attempt, not to the entire retry loop
            # This allows retries to complete even if total time exceeds timeout
            try:
                agent_timeout = node.timeout or self.config.default_timeout
                
                output = await self._execute_agent_with_retry(
                    agent, 
                    input_message, 
                    context,
                    timeout=agent_timeout
                )
                
                # Add span event
                add_span_event(span, "agent_completed", {
                    "output_length": len(str(output)) if output else 0,
                })
                
                # Apply output transformation if specified
                if node.output_transform:
                    try:
                        output = self.context_engine.transform_output(
                            output,
                            transformation=node.output_transform
                        )
                        
                        # Add span event
                        add_span_event(span, "output_transformed", {
                            "transformation": node.output_transform,
                        })
                    except Exception as e:
                        # Log warning but don't fail - use original output
                        logger.warning(
                            "output_transformation_failed",
                            node_id=node.id,
                            error=str(e),
                        )
                
                # Create successful result
                result = AgentResult(
                    agent_id=node.agent_id,
                    node_id=node.id,
                    status=AgentStatus.SUCCESS,
                    output=output,
                    execution_time=time.time() - start_time,
                    cache_hit=False,  # TODO: Implement cache checking
                )
                
                # Track execution time metric
                metrics.track_execution_time("agent", node.agent_id, result.execution_time)
                
            except asyncio.TimeoutError:
                # Track agent timeout
                metrics.track_agent_timeout(node.agent_id)
                
                # Add span event
                add_span_event(span, "agent_timeout", {
                    "timeout_seconds": agent_timeout,
                })
                
                result = AgentResult(
                    agent_id=node.agent_id,
                    node_id=node.id,
                    status=AgentStatus.TIMEOUT,
                    output=None,
                    execution_time=time.time() - start_time,
                    error=f"Agent execution timed out after {agent_timeout}s"
                )
            
            # Store result in context
            context.set_agent_result(node.id, result)
            
            # Add agent response to conversation history
            if result.status == AgentStatus.SUCCESS and result.output:
                context.add_message("assistant", str(result.output))
            
            # Log agent execution end
            log_agent_execution_end(
                logger,
                agent_id=node.agent_id,
                node_id=node.id,
                workflow_id=context.workflow_id,
                status=result.status.value,
                execution_time=result.execution_time,
                output=str(result.output) if result.output else None,
                error=result.error,
            )
            
            return result
            
        except Exception as e:
            # Log error with full context
            log_error_context(
                logger,
                error=e,
                agent_id=node.agent_id,
                node_id=node.id,
                workflow_id=context.workflow_id,
                session_id=str(context.session_id),
                conversation_history=context.conversation_history,
            )
            
            # Set span error
            set_span_error(span, e)
            
            # Use ErrorHandler to format error message
            error_result = self.error_handler.handle_error(
                error=e,
                retry_count=0,  # Already retried in _execute_agent_with_retry
                agent_id=node.agent_id,
                node_id=node.id,
                workflow_id=context.workflow_id,
                session_id=str(context.session_id),
            )
            
            result = AgentResult(
                agent_id=node.agent_id,
                node_id=node.id,
                status=AgentStatus.FAILURE,
                output=None,
                execution_time=time.time() - start_time,
                error=error_result.message or str(e),
                metadata={
                    'error_category': error_result.error_context.category.value if error_result.error_context else 'unknown',
                    'error_type': type(e).__name__,
                }
            )
            context.set_agent_result(node.id, result)
            
            # Log agent execution end
            log_agent_execution_end(
                logger,
                agent_id=node.agent_id,
                node_id=node.id,
                workflow_id=context.workflow_id,
                status=result.status.value,
                execution_time=result.execution_time,
                error=result.error,
            )
            
            return result
        
        finally:
            # End tracing span
            if span is not None:
                span.end()
    
    async def _execute_agent_with_retry(
        self,
        agent: Any,
        message: str,
        context: ExecutionContext,
        timeout: float = 300.0,
    ) -> Any:
        """
        Execute agent with retry logic using ErrorHandler.
        
        Args:
            agent: Agent instance
            message: Input message
            context: Execution context
            timeout: Timeout per attempt (not for entire retry loop)
            
        Returns:
            Agent output
            
        Raises:
            Exception: If execution fails after all retries
        """
        last_error = None
        retry_count = 0  # Track number of retries performed (not including initial attempt)
        
        # Loop allows for 1 initial attempt + max_retries retry attempts
        while True:
            try:
                # Execute agent with timeout per attempt
                # This is a placeholder - actual implementation would use
                # agent's process method or Autogen's a_generate_reply
                if hasattr(agent, 'process'):
                    # Use custom process method with timeout
                    result = await asyncio.wait_for(
                        agent.process(context),
                        timeout=timeout
                    )
                    return result.get('response', '')
                else:
                    # Fallback to simple execution
                    return f"Agent {agent.name} processed: {message}"
                
            except Exception as e:
                last_error = e
                
                # Use ErrorHandler to determine if we should retry
                error_result = self.error_handler.handle_error(
                    error=e,
                    retry_count=retry_count,
                    agent_id=getattr(agent, 'agent_id', getattr(agent, 'name', 'unknown')),
                    workflow_id=context.workflow_id,
                    session_id=str(context.session_id),
                )
                
                # Check if we should retry
                # The error_handler.should_retry already checks if retry_count >= max_retries
                if error_result.should_retry:
                    # Wait before retrying
                    if error_result.retry_delay > 0:
                        await asyncio.sleep(error_result.retry_delay)
                    
                    # Increment retry count and try again
                    retry_count += 1
                    continue
                
                # Don't retry, raise the error
                raise
        
        # This should never be reached, but just in case
        raise last_error or RuntimeError("Agent execution failed after all retries")
    

    
    async def execute_parallel_branch(
        self,
        nodes: List[AgentNode],
        context: ExecutionContext,
    ) -> List[AgentResult]:
        """
        Execute multiple agent nodes in parallel.
        
        Args:
            nodes: List of agent nodes to execute in parallel
            context: Execution context
            
        Returns:
            List of agent results
        """
        return await self._execute_parallel_branch(nodes, context)
    
    async def _execute_parallel_branch(
        self,
        nodes: List[AgentNode],
        context: ExecutionContext,
    ) -> List[AgentResult]:
        """
        Internal method to execute nodes in parallel.
        
        Args:
            nodes: List of agent nodes
            context: Execution context
            
        Returns:
            List of agent results
        """
        # Create tasks for all nodes
        tasks = [
            self.execute_agent_node(node, context)
            for node in nodes
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(AgentResult(
                    agent_id=nodes[i].agent_id,
                    node_id=nodes[i].id,
                    status=AgentStatus.FAILURE,
                    output=None,
                    execution_time=0.0,
                    error=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def _prepare_input(self, node: AgentNode, context: ExecutionContext) -> str:
        """
        Prepare input message for agent node with context passing.
        
        Args:
            node: Agent node
            context: Execution context
            
        Returns:
            Input message string
        """
        # Build context from conversation history and agent results
        source_context = {
            "conversation_history": context.conversation_history,
            "metadata": context.metadata,
        }
        
        # Add results from predecessor nodes
        from src.config.topology_models import ContextStrategy
        predecessors = []
        if hasattr(context, '_workflow_graph'):
            predecessors = context._workflow_graph.get_predecessors(node.id)
        
        for pred_id in predecessors:
            pred_result = context.get_agent_result(pred_id)
            if pred_result and pred_result.status == AgentStatus.SUCCESS:
                source_context[f"agent_{pred_id}"] = {
                    "output": pred_result.output,
                    "metadata": pred_result.metadata,
                }
        
        # Get last message from conversation history
        if context.conversation_history:
            last_message = context.conversation_history[-1]["content"]
            source_context["last_message"] = last_message
        else:
            last_message = ""
            source_context["last_message"] = ""
        
        # Apply input transformation if specified
        if node.input_transform:
            try:
                transformed = self.context_engine.transform_output(
                    source_context,
                    transformation=node.input_transform
                )
                # Convert transformed output to string
                if isinstance(transformed, dict):
                    if "value" in transformed:
                        return str(transformed["value"])
                    elif "text" in transformed:
                        return str(transformed["text"])
                    else:
                        import json
                        return json.dumps(transformed)
                else:
                    return str(transformed)
            except Exception as e:
                # If transformation fails, fall back to last message
                print(f"Warning: Input transformation failed for node {node.id}: {e}")
                return last_message
        
        return last_message
    
    def prepare_context_for_edge(
        self,
        edge: 'AgentEdge',
        source_node_id: str,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """
        Prepare context for passing along an edge based on edge configuration.
        
        Args:
            edge: Agent edge with context passing configuration
            source_node_id: Source node ID
            context: Execution context
            
        Returns:
            Prepared context dictionary
        """
        from src.config.topology_models import ContextStrategy
        
        # Get source agent result
        source_result = context.get_agent_result(source_node_id)
        if not source_result:
            return {}
        
        # Build source context
        source_context = {
            "output": source_result.output,
            "metadata": source_result.metadata,
            "conversation_history": context.conversation_history,
            "workflow_metadata": context.metadata,
        }
        
        # Apply context passing strategy from edge
        strategy_map = {
            ContextStrategy.FULL: ContextPassingStrategy.FULL,
            ContextStrategy.SUMMARY: ContextPassingStrategy.SUMMARY,
            ContextStrategy.SELECTIVE: ContextPassingStrategy.SELECTIVE,
        }
        
        strategy = strategy_map.get(edge.context_strategy, ContextPassingStrategy.FULL)
        
        prepared_context = self.context_engine.prepare_context(
            source_context=source_context,
            strategy=strategy,
            fields=edge.fields if edge.context_strategy == ContextStrategy.SELECTIVE else None,
        )
        
        return prepared_context
    
    def _get_final_response(self, context: ExecutionContext) -> str:
        """
        Get final response from execution context.
        
        Args:
            context: Execution context
            
        Returns:
            Final response string
        """
        # Get last assistant message
        for message in reversed(context.conversation_history):
            if message["role"] == "assistant":
                return message["content"]
        
        # No assistant message found, check for errors
        failed_results = [
            r for r in context.agent_results.values()
            if r.status != AgentStatus.SUCCESS
        ]
        
        if failed_results:
            errors = [r.error for r in failed_results if r.error]
            return f"Workflow failed: {'; '.join(errors)}"
        
        return "No response generated"
