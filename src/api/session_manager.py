"""Session manager for handling conversation sessions with Autogen agents."""

from typing import Any, Dict, Optional
from uuid import UUID

from autogen.agentchat import ConversableAgent

from src.audit_logging import get_logger
from src.config.agent_models import AgentConfig, AgentsConfig
from src.config.registries import get_prompt_registry, get_provider_registry
from src.config.settings import get_settings
from src.config.tool_registry import get_tool_registry
from src.config.workflow_models import ConversationPattern, WorkflowConfig
from src.config.topology_models import TopologyType
from src.config.workflow_registry import get_workflow_registry, WorkflowRegistry
from src.config.execution_models import ExecutionConfig
from src.factory.agent_factory import AgentFactory
from src.memory.inmemory import InMemoryConversationStore
from src.memory.models import ConversationState, MessageRole
from src.memory.store import ConversationStore
from src.patterns.conversation_engine import ConversationPatternEngine
from src.patterns.execution_engine import ExecutionEngine, ExecutionStatus
from src.patterns.topology_engine import WorkflowGraph

logger = get_logger(__name__)


class SessionManager:
    """
    Manager for conversation sessions with Autogen agents.
    
    This class handles:
    - Creating and managing conversation sessions
    - Loading agent configurations for workflows
    - Processing messages through configured agents
    - Managing conversation state and history
    """

    def __init__(
        self,
        conversation_store: Optional[ConversationStore] = None,
        agent_factory: Optional[AgentFactory] = None,
        workflow_registry: Optional[WorkflowRegistry] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ) -> None:
        """
        Initialize the session manager.

        Args:
            conversation_store: Store for persisting conversation state (default store, can be overridden per workflow)
            agent_factory: Factory for creating agents
            workflow_registry: Registry for workflow configurations
            execution_engine: Optional execution engine for topology-based workflows
        """
        self.default_conversation_store = conversation_store or InMemoryConversationStore()
        self._custom_store_provided = conversation_store is not None
        self._settings = get_settings()
        
        # Initialize agent factory if not provided
        if agent_factory is None:
            provider_registry = get_provider_registry()
            prompt_registry = get_prompt_registry()
            tool_registry = get_tool_registry()
            agent_factory = AgentFactory(
                provider_registry=provider_registry,
                prompt_registry=prompt_registry,
                tool_registry=tool_registry,
            )
        
        self.agent_factory = agent_factory
        self.workflow_registry = workflow_registry or get_workflow_registry()
        self.pattern_engine = ConversationPatternEngine()
        
        # Initialize execution engine for topology-based workflows
        if execution_engine is None:
            # Create default execution config from settings
            execution_config = ExecutionConfig()
            execution_engine = ExecutionEngine(
                config=execution_config,
                agent_factory=agent_factory,
            )
        self.execution_engine = execution_engine
        
        # Cache for active sessions and their agents
        self._session_agents: Dict[UUID, Dict[str, ConversableAgent]] = {}
        self._session_workflows: Dict[UUID, WorkflowConfig] = {}
        self._session_stores: Dict[UUID, ConversationStore] = {}
        
        # Initialize MongoDB store if configured
        self._mongo_store: Optional[ConversationStore] = None
        self._init_persistence_stores()

    def _init_persistence_stores(self) -> None:
        """Initialize persistence stores based on configuration."""
        settings = self._settings
        
        # Initialize MongoDB store if configured
        if settings.memory.mongodb_url:
            try:
                from src.infrastructure.database.mongo_store import MongoDBConversationStore
                
                self._mongo_store = MongoDBConversationStore(
                    connection_string=settings.memory.mongodb_url,
                    database_name=settings.memory.mongodb_database,
                )
                
                # Create indexes on startup
                self._mongo_store.create_indexes()
                
                logger.info("MongoDB conversation store initialized")
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB store: {e}")

        self._configure_default_store()

    def _configure_default_store(self) -> None:
        """Select the default conversation store based on settings."""
        if self._custom_store_provided:
            return

        preferred_backend = (self._settings.memory.backend or "").lower()

        if preferred_backend in {"mongodb", "mongo"} and self._mongo_store is not None:
            self.default_conversation_store = self._mongo_store
            return

        if self._mongo_store is not None:
            # Use MongoDB when available to persist sessions by default
            self.default_conversation_store = self._mongo_store

    def _get_conversation_store(self, workflow: WorkflowConfig) -> ConversationStore:
        """
        Get the appropriate conversation store for a workflow based on persistence configuration.
        
        Args:
            workflow: Workflow configuration
            
        Returns:
            ConversationStore instance
            
        Raises:
            ValueError: If required store is not configured
            
        Requirements: 16.1, 16.4, 16.5
        """
        persistence = (workflow.persistence or "").lower()
        
        if persistence in {"mongo_only", "mongodb", "mongo"}:
            if self._mongo_store is None:
                raise ValueError(
                    f"Workflow {workflow.id} requires MongoDB but MONGODB_URL is not configured"
                )
            logger.debug(f"Using MongoDB store for workflow {workflow.id}")
            return self._mongo_store
        
        logger.debug(f"Using default store for workflow {workflow.id}")
        return self.default_conversation_store

    async def create_session(
        self,
        workflow_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationState:
        """
        Create a new conversation session.

        Args:
            workflow_id: ID of the workflow to use
            user_id: Optional user identifier
            metadata: Optional additional metadata

        Returns:
            Created conversation state

        Raises:
            ValueError: If workflow not found or invalid
        """
        logger.info(
            "Creating session",
            workflow_id=workflow_id,
            user_id=user_id,
        )

        # Get and validate workflow
        workflow = self.workflow_registry.get_workflow(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if not workflow.enabled:
            raise ValueError(f"Workflow is disabled: {workflow_id}")

        # Get appropriate conversation store for this workflow
        conversation_store = self._get_conversation_store(workflow)
        
        # Create session state
        session = await conversation_store.create_session()
        
        # Store workflow ID and metadata
        session.metadata["workflow_id"] = workflow_id
        session.metadata["workflow_pattern"] = workflow.pattern.value
        if user_id:
            session.metadata["user_id"] = user_id
        if metadata:
            session.metadata.update(metadata)
        
        # Update session
        await conversation_store.update_session(session)
        
        # Store workflow and store mappings
        self._session_workflows[session.session_id] = workflow
        self._session_stores[session.session_id] = conversation_store
        
        logger.info(
            "Created session",
            session_id=session.session_id,
            workflow_id=workflow_id,
            pattern=workflow.pattern.value,
        )

        return session

    async def get_session(self, session_id: UUID) -> Optional[ConversationState]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Conversation state or None if not found
        """
        # Try to get from cached store first
        if session_id in self._session_stores:
            return await self._session_stores[session_id].get_session(session_id)
        
        # Try all available stores
        for store in [self._postgres_store, self._mongo_store, self.default_conversation_store]:
            if store is not None:
                session = await store.get_session(session_id)
                if session is not None:
                    # Cache the store for this session
                    self._session_stores[session_id] = store
                    return session
        
        return None

    async def delete_session(self, session_id: UUID) -> bool:
        """
        End and delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        logger.info("Deleting session", session_id=session_id)
        
        # Get the appropriate store for this session
        store = self._session_stores.get(session_id, self.default_conversation_store)
        
        # Clean up cached agents
        if session_id in self._session_agents:
            del self._session_agents[session_id]
        
        if session_id in self._session_workflows:
            del self._session_workflows[session_id]
        
        if session_id in self._session_stores:
            del self._session_stores[session_id]
        
        # Delete from store
        result = await store.delete_session(session_id)
        
        logger.info("Deleted session", session_id=session_id, success=result)
        
        return result

    async def process_message(
        self,
        session_id: UUID,
        message: str,
        max_turns: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a message through configured agents using the workflow pattern.

        Args:
            session_id: Session identifier
            message: User message to process
            max_turns: Maximum conversation turns (overrides workflow default)
            metadata: Optional additional metadata

        Returns:
            Dictionary containing response and conversation metadata

        Raises:
            ValueError: If session not found or invalid
        """
        logger.info(
            "Processing message",
            session_id=session_id,
            message_length=len(message),
        )

        # Get session
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        if not session.active:
            raise ValueError(f"Session is not active: {session_id}")

        # Add user message to history
        session.add_message(MessageRole.USER, message, **(metadata or {}))
        
        # Get workflow and agents for this session
        workflow = await self._get_workflow(session_id, session)
        agents = await self._get_or_create_agents(session_id, session, workflow)
        
        # Execute conversation based on workflow pattern
        try:
            result = await self._execute_workflow(
                session_id=session_id,
                workflow=workflow,
                agents=agents,
                message=message,
                max_turns=max_turns,
                session=session,
            )
            
            # Extract response
            response_text = result.get("response", "")
            
            # Add assistant response to history
            session.add_message(MessageRole.ASSISTANT, response_text)
            session.increment_turn()
            
            # Update session using the appropriate store
            store = self._session_stores.get(session_id, self.default_conversation_store)
            await store.update_session(session)
            
            # Get chat history for response
            chat_history = [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else "",
                }
                for msg in session.messages
            ]
            
            # Add session metadata to result
            result["session_id"] = session_id
            result["turn_count"] = session.turn_count
            result["chat_history"] = chat_history
            result["summary"] = result.get("summary", "")  # Use summary from workflow execution if available
            result["safety_passed"] = True  # Default to True, can be enhanced with content moderation
            if metadata:
                result.setdefault("metadata", {}).update(metadata)
            
            logger.info(
                "Processed message",
                session_id=session_id,
                pattern=workflow.pattern.value,
                turn_count=session.turn_count,
                response_length=len(response_text),
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to process message",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_chat_history(self, session_id: UUID) -> Dict[str, Any]:
        """
        Get chat history for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary containing messages and agent notes

        Raises:
            ValueError: If session not found
        """
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        return {
            "session_id": session_id,
            "messages": [msg.model_dump() for msg in session.messages],
            "agent_notes": [note.model_dump() for note in session.agent_notes],
            "turn_count": session.turn_count,
        }

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        active_only: bool = True,
    ) -> list[ConversationState]:
        """
        List all sessions, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter sessions
            active_only: If True, only return active sessions

        Returns:
            List of ConversationState objects
        """
        logger.info(
            "Listing sessions",
            user_id=user_id,
            active_only=active_only,
        )

        # Get all sessions from the default store
        all_sessions = await self.default_conversation_store.list_sessions(active_only=active_only)
        
        # Also check MongoDB store if available and different from default
        if self._mongo_store is not None and self._mongo_store != self.default_conversation_store:
            mongo_sessions = await self._mongo_store.list_sessions(active_only=active_only)
            # Merge sessions, avoiding duplicates by session_id
            existing_ids = {s.session_id for s in all_sessions}
            for session in mongo_sessions:
                if session.session_id not in existing_ids:
                    all_sessions.append(session)
        
        # Filter by user_id if provided
        if user_id:
            all_sessions = [
                s for s in all_sessions
                if s.metadata.get("user_id") == user_id
            ]
        
        # Sort by updated_at descending
        all_sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        logger.info(
            "Listed sessions",
            total_count=len(all_sessions),
            user_id=user_id,
        )
        
        return all_sessions

    async def _get_workflow(
        self,
        session_id: UUID,
        session: ConversationState,
    ) -> WorkflowConfig:
        """
        Get workflow configuration for a session.

        Args:
            session_id: Session identifier
            session: Conversation state

        Returns:
            WorkflowConfig

        Raises:
            ValueError: If workflow not found
        """
        # Check cache
        if session_id in self._session_workflows:
            return self._session_workflows[session_id]

        # Get workflow ID from session metadata
        workflow_id = session.metadata.get("workflow_id")
        if not workflow_id:
            raise ValueError("Session missing workflow_id in metadata")

        # Load workflow
        workflow = self.workflow_registry.get_workflow(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # Cache workflow
        self._session_workflows[session_id] = workflow

        return workflow

    async def _get_or_create_agents(
        self,
        session_id: UUID,
        session: ConversationState,
        workflow: WorkflowConfig,
    ) -> Dict[str, ConversableAgent]:
        """
        Get or create agents for a session based on workflow configuration.

        Args:
            session_id: Session identifier
            session: Conversation state
            workflow: Workflow configuration

        Returns:
            Dictionary mapping agent IDs to agent instances

        Raises:
            ValueError: If agent creation fails
        """
        # Check cache
        if session_id in self._session_agents:
            return self._session_agents[session_id]

        # Get all agent IDs needed for this workflow
        agent_ids = workflow.get_all_agent_ids()
        
        logger.debug(
            "Creating agents for session",
            session_id=session_id,
            workflow_id=workflow.id,
            agent_count=len(agent_ids),
        )

        # Load agents config to get agent configurations
        from src.config.loader import load_agents_config
        agents_config = load_agents_config()

        # Create agents
        agents: Dict[str, ConversableAgent] = {}
        for agent_id in agent_ids:
            try:
                # Get agent configuration
                agent_config = agents_config.get_agent(agent_id)
                if agent_config is None:
                    raise ValueError(f"Agent configuration not found: {agent_id}")

                # Create agent based on type
                if agent_config.type.value == "retrieve_user_proxy":
                    agent = self.agent_factory.create_retrieve_agent(agent_config)
                else:
                    agent = self.agent_factory.create_agent(agent_config)

                agents[agent_id] = agent
                
                logger.debug(
                    "Created agent",
                    agent_id=agent_id,
                    agent_type=agent_config.type.value,
                )

            except Exception as e:
                logger.error(
                    "Failed to create agent",
                    agent_id=agent_id,
                    error=str(e),
                )
                raise ValueError(f"Failed to create agent {agent_id}: {e}")

        # For two-agent workflows with tools, register tools across agents
        if workflow.pattern == ConversationPattern.TWO_AGENT:
            self._register_tools_for_two_agent_pattern(
                workflow, agents, agents_config
            )

        # Cache agents
        self._session_agents[session_id] = agents

        logger.info(
            "Created agents for session",
            session_id=session_id,
            agent_count=len(agents),
        )

        return agents

    def _register_tools_for_two_agent_pattern(
        self,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        agents_config: Any,
    ) -> None:
        """
        Register tools for two-agent pattern with proper LLM/executor separation.
        
        In two-agent pattern:
        - Recipient (with LLM) should have register_for_llm (can suggest tool calls)
        - Sender (executor) should have register_for_execution (can run tools)
        
        Args:
            workflow: Workflow configuration
            agents: Dictionary of created agents
            agents_config: Agents configuration with tool lists
        """
        sender = agents.get(workflow.entry_agent_id)
        recipient = agents.get(workflow.recipient_agent_id)
        
        if not sender or not recipient:
            return
            
        # Get recipient's tool list
        recipient_config = agents_config.get_agent(workflow.recipient_agent_id)
        if not recipient_config or not recipient_config.tools:
            return
            
        # Register tools: recipient for LLM, sender for execution
        tool_registry = self.agent_factory.tool_registry
        if not tool_registry:
            logger.warning(
                "Tool registry not available, skipping cross-agent tool registration"
            )
            return
            
        for tool_id in recipient_config.tools:
            try:
                tool_registry.register_tool_with_agents(
                    tool_id=tool_id,
                    caller=recipient,  # Agent with LLM that suggests tool calls
                    executor=sender,   # Agent that executes the tools
                )
                logger.info(
                    "Registered tool for two-agent pattern",
                    tool_id=tool_id,
                    caller=recipient.name,
                    executor=sender.name,
                )
            except Exception as e:
                logger.warning(
                    "Failed to register tool for two-agent pattern",
                    tool_id=tool_id,
                    error=str(e),
                )

    async def _execute_workflow(
        self,
        session_id: UUID,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        message: str,
        max_turns: Optional[int] = None,
        session: Optional[ConversationState] = None,
    ) -> Dict[str, Any]:
        """
        Execute a workflow based on its pattern or topology.

        Args:
            session_id: Session identifier
            workflow: Workflow configuration
            agents: Dictionary of agent instances
            message: User message
            max_turns: Optional override for max turns
            session: Optional conversation state for context

        Returns:
            Dictionary containing response and metadata

        Raises:
            ValueError: If workflow execution fails
        """
        # Check if workflow has topology configuration (new execution engine)
        if hasattr(workflow, 'topology') and workflow.topology is not None:
            return await self._execute_topology_workflow(
                session_id, workflow, message, max_turns
            )
        
        # Fall back to pattern-based execution (legacy)
        pattern = workflow.pattern

        if pattern == ConversationPattern.TWO_AGENT:
            return await self._execute_two_agent_workflow(
                workflow, agents, message, max_turns, session
            )
        elif pattern == ConversationPattern.SEQUENTIAL:
            return await self._execute_sequential_workflow(
                workflow, agents, message
            )
        elif pattern == ConversationPattern.GROUP_CHAT:
            return await self._execute_group_chat_workflow(
                workflow, agents, message
            )
        elif pattern == ConversationPattern.NESTED:
            return await self._execute_nested_workflow(
                workflow, agents, message, max_turns
            )
        elif pattern == ConversationPattern.SELECTOR:
            return await self._execute_selector_workflow(
                session_id, workflow, agents, message, max_turns, session
            )
        else:
            raise ValueError(f"Unsupported conversation pattern: {pattern}")

    async def _execute_topology_workflow(
        self,
        session_id: UUID,
        workflow: WorkflowConfig,
        message: str,
        max_turns: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a workflow using the topology-based execution engine.
        
        Args:
            session_id: Session identifier
            workflow: Workflow configuration with topology
            message: User message
            max_turns: Optional override for max turns
            
        Returns:
            Dictionary containing response and metadata
            
        Raises:
            ValueError: If workflow execution fails
        """
        # Ensure execution engine is started
        if not self.execution_engine._started:
            await self.execution_engine.start()
        
        # Create workflow graph from topology configuration
        workflow_graph = WorkflowGraph(workflow.topology)
        
        # Build context from session metadata
        context = {
            "workflow_id": workflow.id,
            "session_id": str(session_id),
            "max_turns": max_turns,
        }
        
        # Execute workflow using execution engine
        result = await self.execution_engine.execute_workflow(
            workflow_id=workflow.id,
            session_id=session_id,
            message=message,
            context=context,
            workflow_graph=workflow_graph,
            timeout=workflow.topology.resource_limits.max_execution_time if hasattr(workflow.topology, 'resource_limits') else None,
        )
        
        # Convert ExecutionResult to response format
        response_dict = {
            "response": result.final_response,
            "status": result.status.value,
            "execution_time": result.execution_time,
            "agent_results": {
                node_id: {
                    "agent_id": agent_result.agent_id,
                    "status": agent_result.status.value,
                    "output": agent_result.output,
                    "execution_time": agent_result.execution_time,
                    "cache_hit": agent_result.cache_hit,
                    "error": agent_result.error,
                }
                for node_id, agent_result in result.agent_results.items()
            },
            "pattern": "topology",
            "topology_type": workflow.topology.type.value,
            "metadata": result.metadata,
        }
        
        # Add error details if execution failed
        if result.status in [ExecutionStatus.FAILURE, ExecutionStatus.TIMEOUT]:
            response_dict["error"] = {
                "type": result.status.value,
                "message": result.final_response,
                "agent_errors": [
                    {
                        "node_id": node_id,
                        "agent_id": agent_result.agent_id,
                        "error": agent_result.error,
                    }
                    for node_id, agent_result in result.agent_results.items()
                    if agent_result.error
                ],
            }
        
        return response_dict

    async def _execute_two_agent_workflow(
        self,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        message: str,
        max_turns: Optional[int] = None,
        session: Optional[ConversationState] = None,
    ) -> Dict[str, Any]:
        """Execute a two-agent workflow."""
        sender = agents.get(workflow.entry_agent_id)
        recipient = agents.get(workflow.recipient_agent_id)

        if sender is None or recipient is None:
            raise ValueError("Required agents not found for two-agent workflow")

        # Use workflow max_turns if not overridden
        turns = max_turns if max_turns is not None else workflow.max_turns

        # Build message with conversation history context
        message_with_context = message
        if session and session.messages:
            # Get previous messages (excluding the current one which was just added)
            previous_messages = session.messages[:-1] if len(session.messages) > 1 else []
            
            if previous_messages:
                # Build conversation history context
                history_parts = []
                for msg in previous_messages[-10:]:  # Last 10 messages for context
                    role = "User" if msg.role.value == "user" else "Assistant"
                    history_parts.append(f"{role}: {msg.content}")
                
                history_context = "\n".join(history_parts)
                message_with_context = f"""[Previous conversation context]
{history_context}

[Current message]
{message}

Please respond to the current message, taking into account the previous conversation context above."""
                
                logger.debug(
                    "Added conversation history to message",
                    history_messages=len(previous_messages),
                    context_length=len(history_context),
                )

        logger.debug(
            "Executing two-agent workflow",
            sender=workflow.entry_agent_id,
            sender_name=sender.name,
            sender_has_llm=sender.llm_config is not False,
            recipient=workflow.recipient_agent_id,
            recipient_name=recipient.name,
            recipient_has_llm=recipient.llm_config is not False,
            max_turns=turns,
            has_history_context=session is not None and len(session.messages) > 1,
        )

        chat_result = self.pattern_engine.execute_two_agent_chat(
            sender=sender,
            recipient=recipient,
            message=message_with_context,
            max_turns=turns,
            summary_method=workflow.summary_method.value,
        )

        # Log the chat result for debugging
        logger.debug(
            "Chat result received",
            result_type=type(chat_result).__name__,
            has_summary=hasattr(chat_result, 'summary'),
            summary_value=getattr(chat_result, 'summary', None),
            has_chat_history=hasattr(chat_result, 'chat_history'),
            chat_history_count=len(getattr(chat_result, 'chat_history', [])),
            has_cost=hasattr(chat_result, 'cost'),
        )
        
        # Log chat history details
        if hasattr(chat_result, 'chat_history'):
            logger.debug(
                "Chat history details",
                messages=[
                    {
                        "name": msg.get("name", "unknown"),
                        "role": msg.get("role", "unknown"),
                        "content_preview": msg.get("content", "")[:100]
                    }
                    for msg in chat_result.chat_history[-5:]  # Last 5 messages
                ]
            )

        # Extract response
        response_text = self._extract_response_from_chat_result(chat_result, recipient)

        # Extract cost properly - handle both dict and object access
        cost = {}
        if hasattr(chat_result, 'cost'):
            cost_obj = chat_result.cost
            if isinstance(cost_obj, dict):
                cost = cost_obj
            elif hasattr(cost_obj, '__dict__'):
                cost = cost_obj.__dict__

        return {
            "response": response_text,
            "cost": cost,
            "pattern": "two_agent",
            "metadata": {},
        }

    async def _execute_sequential_workflow(
        self,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        message: str,
    ) -> Dict[str, Any]:
        """Execute a sequential workflow."""
        if not workflow.steps:
            raise ValueError("Sequential workflow has no steps")

        # Build chat sequence for Autogen
        chat_sequence = []
        for step in workflow.steps:
            sender = agents.get(step.sender_id)
            recipient = agents.get(step.recipient_id)

            if sender is None or recipient is None:
                raise ValueError(f"Required agents not found for step: {step.sender_id} -> {step.recipient_id}")

            chat_config = {
                "recipient": recipient,
                "max_turns": step.max_turns,
                "summary_method": step.summary_method.value,
                "clear_history": step.clear_history,
            }

            # Add message for first step or if specified
            if len(chat_sequence) == 0:
                chat_config["message"] = message
            elif step.message:
                chat_config["message"] = step.message

            chat_sequence.append(chat_config)

        # Execute sequential chats
        entry_agent = agents.get(workflow.entry_agent_id)
        if entry_agent is None:
            raise ValueError(f"Entry agent not found: {workflow.entry_agent_id}")

        chat_results = self.pattern_engine.execute_sequential_chat(
            sender=entry_agent,
            chat_sequence=chat_sequence,
        )

        # Extract response from last chat result
        last_result = chat_results[-1] if chat_results else None
        response_text = ""
        if last_result:
            last_recipient = chat_sequence[-1]["recipient"]
            response_text = self._extract_response_from_chat_result(last_result, last_recipient)

        # Aggregate costs
        total_cost = {}
        for result in chat_results:
            cost = getattr(result, 'cost', {})
            for key, value in cost.items():
                total_cost[key] = total_cost.get(key, 0) + value

        return {
            "response": response_text,
            "cost": total_cost,
            "pattern": "sequential",
            "steps_completed": len(chat_results),
            "metadata": {},
        }

    async def _execute_group_chat_workflow(
        self,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        message: str,
    ) -> Dict[str, Any]:
        """Execute a group chat workflow."""
        if not workflow.group_chat:
            raise ValueError("Group chat workflow missing group_chat configuration")

        # Get agents for group chat
        group_agents = []
        for agent_id in workflow.group_chat.agents:
            agent = agents.get(agent_id)
            if agent is None:
                raise ValueError(f"Agent not found for group chat: {agent_id}")
            group_agents.append(agent)

        # Prepare allowed transitions if specified
        allowed_transitions = None
        if workflow.group_chat.allowed_transitions:
            allowed_transitions = {}
            for from_id, to_ids in workflow.group_chat.allowed_transitions.items():
                from_agent = agents.get(from_id)
                to_agents = [agents.get(to_id) for to_id in to_ids]
                if from_agent and all(to_agents):
                    allowed_transitions[from_agent] = to_agents

        chat_result = self.pattern_engine.execute_group_chat(
            agents=group_agents,
            initial_message=message,
            max_round=workflow.group_chat.max_round,
            speaker_selection_method=workflow.group_chat.speaker_selection_method.value,
            allowed_transitions=allowed_transitions,
            speaker_transitions_type=workflow.group_chat.speaker_transitions_type,
            send_introductions=workflow.group_chat.send_introductions,
            admin_name=workflow.group_chat.admin_name,
        )

        # Extract response from last message
        response_text = ""
        if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            last_msg = chat_result.chat_history[-1]
            response_text = last_msg.get('content', '')
        elif hasattr(chat_result, 'summary') and chat_result.summary:
            response_text = chat_result.summary

        return {
            "response": response_text,
            "cost": getattr(chat_result, 'cost', {}),
            "pattern": "group_chat",
            "metadata": {},
        }

    async def _execute_nested_workflow(
        self,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        message: str,
        max_turns: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a nested workflow."""
        if not workflow.nested_chats:
            raise ValueError("Nested workflow has no nested chat configurations")

        # Register nested chats
        for nested_config in workflow.nested_chats:
            trigger_agent = agents.get(nested_config.trigger_agent_id)
            if trigger_agent is None:
                raise ValueError(f"Trigger agent not found: {nested_config.trigger_agent_id}")

            # Build nested chat queue
            nested_chat_queue = []
            for nested_chat in nested_config.nested_chats:
                recipient_id = nested_chat.get("recipient")
                recipient = agents.get(recipient_id)
                if recipient:
                    nested_chat_queue.append({
                        "recipient": recipient,
                        "message": nested_chat.get("message"),
                        "max_turns": nested_chat.get("max_turns", 10),
                        "summary_method": nested_chat.get("summary_method", "last_msg"),
                    })

            # Register nested chats
            self.pattern_engine.register_nested_chat(
                trigger_agent=trigger_agent,
                nested_chats=nested_chat_queue,
                trigger=nested_config.trigger_condition,
                position=nested_config.position,
            )

        # Execute as two-agent chat (nested chats will trigger automatically)
        entry_agent = agents.get(workflow.entry_agent_id)
        if entry_agent is None:
            raise ValueError(f"Entry agent not found: {workflow.entry_agent_id}")

        # For nested pattern, we need a recipient (use first agent that's not entry)
        recipient = None
        for agent_id, agent in agents.items():
            if agent_id != workflow.entry_agent_id:
                recipient = agent
                break

        if recipient is None:
            raise ValueError("No recipient agent found for nested workflow")

        turns = max_turns if max_turns is not None else 10

        chat_result = self.pattern_engine.execute_two_agent_chat(
            sender=entry_agent,
            recipient=recipient,
            message=message,
            max_turns=turns,
        )

        response_text = self._extract_response_from_chat_result(chat_result, recipient)

        return {
            "response": response_text,
            "cost": getattr(chat_result, 'cost', {}),
            "pattern": "nested",
            "metadata": {},
        }

    async def _execute_selector_workflow(
        self,
        session_id: UUID,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        message: str,
        max_turns: Optional[int] = None,
        session: Optional[ConversationState] = None,
    ) -> Dict[str, Any]:
        """
        Execute a selector (router) workflow.
        
        The selector pattern uses a routing agent to analyze user intent
        and route queries to specialized domain agents.
        
        Flow:
        1. Send message to selector agent to get routing decision
        2. Parse the JSON routing decision
        3. Route to the appropriate domain agent
        4. Return the domain agent's response
        
        Args:
            workflow: Workflow configuration with selector_config
            agents: Dictionary of agent instances
            message: User message
            max_turns: Optional override for max turns
            session: Optional conversation state for context
            
        Returns:
            Dictionary containing response and metadata
        """
        import json
        import re
        
        if not workflow.selector_config:
            raise ValueError("Selector workflow missing selector_config")
        
        selector_config = workflow.selector_config
        routing_agents = selector_config.routing_agents
        default_agent_id = selector_config.default_agent
        
        # Get the selector agent
        selector_agent = agents.get(workflow.entry_agent_id)
        if selector_agent is None:
            raise ValueError(f"Selector agent not found: {workflow.entry_agent_id}")
        
        logger.info(
            "Executing selector workflow",
            selector_agent=workflow.entry_agent_id,
            routing_agents=list(routing_agents.keys()),
        )
        
        # Step 1: Get routing decision from selector agent
        # Create a user proxy to interact with the selector
        from autogen.agentchat import ConversableAgent as AutogenAgent
        
        user_proxy = AutogenAgent(
            name="UserProxy",
            llm_config=False,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
        )
        
        # Build message with conversation context for selector
        # This helps the selector understand references like "the number I gave you"
        selector_message = message
        if session and session.messages:
            recent_messages = session.messages[-6:]  # Last 3 exchanges for context
            if len(recent_messages) > 1:
                # Build a compact context summary for the selector
                context_parts = []
                for m in recent_messages[:-1]:  # Exclude current message
                    content = m.content
                    # Skip messages that are just context wrappers
                    if "[Previous conversation context]" in content or "[Recent conversation for context]" in content:
                        continue
                    role = "User" if m.role.value == "user" else "Assistant"
                    # Truncate long messages for selector context
                    if len(content) > 200:
                        content = content[:200] + "..."
                    context_parts.append(f"{role}: {content}")
                
                if context_parts:
                    context_summary = "\n".join(context_parts)
                    selector_message = f"""[Recent conversation for context]
{context_summary}

[Current user message to route]
{message}

Analyze the CURRENT message and route it appropriately. Use the conversation context to understand any references (like "the number", "that requisition", etc.)."""
                    
                    logger.debug(
                        "Added context to selector message",
                        context_messages=len(context_parts),
                    )
        
        # Execute chat with selector to get routing decision
        turns = max_turns if max_turns is not None else 2
        
        selector_result = self.pattern_engine.execute_two_agent_chat(
            sender=user_proxy,
            recipient=selector_agent,
            message=selector_message,
            max_turns=turns,
            summary_method="last_msg",
        )
        
        # Extract selector's response - look for the selector agent's response (not user message)
        selector_response = ""
        if hasattr(selector_result, 'chat_history') and selector_result.chat_history:
            # Log chat history for debugging
            logger.debug(
                "Selector chat history",
                history_count=len(selector_result.chat_history),
                messages=[
                    {"name": m.get("name"), "role": m.get("role"), "content_preview": m.get("content", "")[:100]}
                    for m in selector_result.chat_history[:5]
                ]
            )
            
            # Find the selector agent's response (skip user messages)
            for msg in selector_result.chat_history:
                msg_name = msg.get('name', '')
                msg_role = msg.get('role', '')
                content = msg.get('content', '')
                
                # Skip user/proxy messages
                if msg_name == 'UserProxy' or msg_role == 'user':
                    continue
                
                # Look for selector agent's response
                if (msg_name == selector_agent.name or msg_role == 'assistant') and content:
                    # Check if content looks like JSON (routing decision)
                    if '{' in content and 'domain' in content:
                        selector_response = content
                        break
                    # Otherwise keep looking but save this as fallback
                    if not selector_response:
                        selector_response = content
        
        # Fallback to summary if no response found
        if not selector_response:
            selector_response = getattr(selector_result, 'summary', '') or ''
        
        logger.debug(
            "Selector response received",
            response_preview=selector_response[:200] if selector_response else "EMPTY",
        )
        
        # Step 2: Parse routing decision
        routing_decision = self._parse_selector_routing_decision(selector_response)
        
        if not routing_decision:
            logger.warning(
                "Could not parse routing decision, using default agent",
                selector_response=selector_response[:200],
            )
            routing_decision = {"domain": "general", "intent": "general_query"}
        
        # Check if clarification is needed
        if routing_decision.get('requires_clarification'):
            clarification_prompt = routing_decision.get('clarification_prompt', selector_response)
            return {
                "response": clarification_prompt,
                "cost": getattr(selector_result, 'cost', {}),
                "pattern": "selector",
                "routing_decision": routing_decision,
                "metadata": {"requires_clarification": True},
            }
        
        # Step 3: Route to domain agent
        domain = routing_decision.get('domain', 'general')
        target_agent_id = routing_agents.get(domain, default_agent_id)
        
        logger.info(
            "Routing to domain agent",
            domain=domain,
            target_agent=target_agent_id,
            intent=routing_decision.get('intent'),
        )
        
        # Handle "general" domain queries directly without routing to avoid loops
        if domain == 'general' or target_agent_id == workflow.entry_agent_id:
            # Generate a helpful response for general queries
            general_response = self._generate_general_help_response(
                message=message,
                routing_agents=routing_agents,
                selector_agent=selector_agent,
            )
            return {
                "response": general_response,
                "cost": getattr(selector_result, 'cost', {}),
                "pattern": "selector",
                "routing_decision": routing_decision,
                "metadata": {"domain": "general", "handled_directly": True},
            }
        
        target_agent = agents.get(target_agent_id)
        if target_agent is None:
            logger.warning(
                "Target agent not found, using selector response",
                target_agent_id=target_agent_id,
            )
            return {
                "response": selector_response,
                "cost": getattr(selector_result, 'cost', {}),
                "pattern": "selector",
                "routing_decision": routing_decision,
                "metadata": {"agent_not_found": target_agent_id},
            }
        
        # Step 4: Execute domain agent
        # Create a new user proxy for the domain agent interaction
        # Use max_consecutive_auto_reply=3 to stop after getting a substantive response
        domain_user_proxy = AutogenAgent(
            name="UserProxy",
            llm_config=False,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=3,
        )
        
        # Build message with conversation context if available
        # Use passed session or fetch if not provided
        if session is None:
            session = await self.get_session(session_id)
        
        context_message = message
        if session and session.messages:
            # Build context from recent conversation history (last 5 exchanges)
            recent_messages = session.messages[-10:]  # Last 10 messages (5 exchanges)
            if len(recent_messages) > 1:  # Only add context if there's history
                history_parts = []
                for m in recent_messages[:-1]:  # Exclude current message
                    content = m.content
                    # Strip out any existing context markers to avoid nesting
                    if "[Previous conversation context]" in content:
                        # Extract just the actual response, not the context wrapper
                        if "[Current message]" in content:
                            # This was a wrapped message, skip it or extract the response
                            continue
                    # Truncate very long messages to keep context manageable
                    if len(content) > 500:
                        content = content[:500] + "..."
                    role = "User" if m.role.value == "user" else "Assistant"
                    history_parts.append(f"{role}: {content}")
                
                if history_parts:
                    history_text = "\n".join(history_parts)
                    context_message = f"""[Previous conversation context]
{history_text}

[Current message]
{message}

Please respond to the current message, taking into account the previous conversation context above."""
        
        # Register tools for the domain agent if it has any
        # Note: domain_user_proxy is created fresh each request, so we must always
        # register tools for execution on it. We only skip LLM registration if
        # already done on the cached target_agent.
        from src.config.loader import load_agents_config
        agents_config = load_agents_config()
        target_agent_config = agents_config.get_agent(target_agent_id)
        
        if target_agent_config and target_agent_config.tools:
            tool_registry = self.agent_factory.tool_registry
            logger.info(
                "Tool registration check",
                has_tool_registry=tool_registry is not None,
                target_agent_tools=target_agent_config.tools,
                available_tools=tool_registry.list_tools() if tool_registry else [],
                get_self_tool_exists='get_self_requisition_info' in (tool_registry.list_tools() if tool_registry else []),
            )
            if tool_registry:
                # Check which tools are already registered for LLM on the target agent
                llm_registered_tools = getattr(target_agent, '_registered_tool_ids', set())
                
                for tool_id in target_agent_config.tools:
                    try:
                        tool_def = tool_registry.get_tool(tool_id)
                        if tool_def is None:
                            logger.warning(
                                "Tool not found in registry",
                                tool_id=tool_id,
                            )
                            continue
                        
                        # Get the function and ensure it has the correct name
                        tool_func = tool_def.function
                        
                        # Log function details for debugging
                        logger.debug(
                            "Registering tool function",
                            tool_id=tool_id,
                            func_name=getattr(tool_func, '__name__', 'unknown'),
                            func_type=type(tool_func).__name__,
                            is_coroutine=str(tool_func).startswith('<coroutine') or 'async' in str(type(tool_func)),
                        )
                        
                        # Always register for execution on the new domain_user_proxy
                        # Use the decorator pattern correctly
                        registered_func = domain_user_proxy.register_for_execution(
                            name=tool_id,
                        )(tool_func)
                        
                        # Verify the function was registered by checking the function_map
                        func_map = getattr(domain_user_proxy, 'function_map', {})
                        is_registered = tool_id in func_map
                        
                        logger.info(
                            "Tool registered for execution",
                            tool_id=tool_id,
                            executor=domain_user_proxy.name,
                            registered_func_name=getattr(registered_func, '__name__', 'unknown'),
                            is_in_function_map=is_registered,
                            function_map_keys=list(func_map.keys()) if func_map else [],
                        )
                        
                        # Only register for LLM if not already done on cached agent
                        if tool_id not in llm_registered_tools:
                            description = tool_def.description
                            if tool_def.name and tool_def.name != tool_id:
                                description = f"{tool_def.name}: {description}"
                            
                            target_agent.register_for_llm(
                                name=tool_id,
                                description=description,
                            )(tool_func)
                            
                            llm_registered_tools.add(tool_id)
                            target_agent._registered_tool_ids = llm_registered_tools
                        
                        logger.info(
                            "Registered tool with agents",
                            tool_id=tool_id,
                            tool_name=tool_id,
                            caller=target_agent.name,
                            executor=domain_user_proxy.name,
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to register tool",
                            tool_id=tool_id,
                            error=str(e),
                            exc_info=True,
                        )
        
        # Execute chat with domain agent
        domain_turns = max_turns if max_turns is not None else workflow.max_turns
        
        # Log the function map before initiating chat
        logger.info(
            "Starting domain agent chat",
            target_agent=target_agent_id,
            executor_name=domain_user_proxy.name,
            executor_id=id(domain_user_proxy),
            executor_function_map=list(domain_user_proxy.function_map.keys()) if domain_user_proxy.function_map else [],
            executor_can_execute_get_self=domain_user_proxy.can_execute_function('get_self_requisition_info'),
            target_agent_name=target_agent.name,
            target_agent_id=id(target_agent),
            target_agent_tools=list(getattr(target_agent, '_registered_tool_ids', set())),
            target_agent_function_map=list(target_agent.function_map.keys()) if target_agent.function_map else [],
        )
        
        domain_result = self.pattern_engine.execute_two_agent_chat(
            sender=domain_user_proxy,
            recipient=target_agent,
            message=context_message,  # Use message with conversation context
            max_turns=domain_turns,
            summary_method=workflow.summary_method.value,
        )
        
        # Extract domain agent's response
        response_text = self._extract_response_from_chat_result(domain_result, target_agent)
        
        # Combine costs
        total_cost = {}
        for cost_dict in [getattr(selector_result, 'cost', {}), getattr(domain_result, 'cost', {})]:
            if isinstance(cost_dict, dict):
                for key, value in cost_dict.items():
                    if isinstance(value, (int, float)):
                        total_cost[key] = total_cost.get(key, 0) + value
        
        return {
            "response": response_text,
            "cost": total_cost,
            "pattern": "selector",
            "routing_decision": routing_decision,
            "routed_to": target_agent_id,
            "metadata": {
                "domain": domain,
                "intent": routing_decision.get('intent'),
            },
        }

    def _generate_general_help_response(
        self,
        message: str,
        routing_agents: Dict[str, str],
        selector_agent: Any,
    ) -> str:
        """
        Generate a helpful response for general queries.
        
        Args:
            message: Original user message
            routing_agents: Available domain agents
            selector_agent: The selector agent instance
            
        Returns:
            Helpful response string
        """
        # Build list of available domains
        domains = list(routing_agents.keys())
        domain_descriptions = {
            "requisition": "requisitions and purchase requests",
            "purchase_order": "purchase orders and PO status",
            "framework_agreement": "framework agreements and contracts",
        }
        
        capabilities = []
        for domain in domains:
            desc = domain_descriptions.get(domain, domain.replace("_", " "))
            capabilities.append(f"• **{domain.replace('_', ' ').title()}**: I can help you with {desc}")
        
        capabilities_text = "\n".join(capabilities)
        
        response = f"""Hello! I'm your Procurement Assistant. I can help you with various procurement-related queries.

**Here's what I can help you with:**

{capabilities_text}

**Example questions you can ask:**
• "What is the status of requisition REQ20250010638?"
• "Show me details of purchase order PO-2024-001"
• "What framework agreements are available?"

Please ask me a specific question about requisitions, purchase orders, or framework agreements, and I'll be happy to help!"""
        
        return response

    def _parse_selector_routing_decision(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse routing decision from selector agent response.
        
        Args:
            response: Selector agent's response (should contain JSON)
            
        Returns:
            Parsed routing decision dict or None
        """
        import json
        import re
        
        if not response:
            return None
        
        # Try direct JSON parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in the response
        # Match the outermost JSON object
        json_patterns = [
            r'\{[^{}]*"domain"[^{}]*\}',  # Simple object with domain
            r'\{.*?"domain".*?\}',  # More permissive
            r'```json\s*(\{.*?\})\s*```',  # JSON in code block
            r'```\s*(\{.*?\})\s*```',  # JSON in generic code block
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1) if match.lastindex else match.group()
                    return json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    continue
        
        # Try to find any JSON-like structure
        try:
            # Find the first { and last }
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return None

    def _extract_response_from_chat_result(
        self,
        chat_result: Any,
        recipient: ConversableAgent,
    ) -> str:
        """Extract response text from a chat result.
        
        For tool-using workflows, we want the FIRST substantive response from the
        recipient agent after a tool call, not the last message (which may be a
        follow-up question asking for more input).
        """
        response_text = ""
        
        # Log what we got for debugging
        logger.debug(
            "Extracting response from chat result",
            has_summary=hasattr(chat_result, 'summary'),
            summary_value=getattr(chat_result, 'summary', None),
            has_chat_history=hasattr(chat_result, 'chat_history'),
            chat_history_len=len(getattr(chat_result, 'chat_history', [])),
        )
        
        # For tool-using workflows: find the first substantive response after a tool result
        if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            tool_result_found = False
            
            for msg in chat_result.chat_history:
                msg_name = msg.get('name', '')
                msg_role = msg.get('role', '')
                msg_content = msg.get('content', '')
                
                # Check if this is a tool result message
                if msg_role == 'tool' or (msg_content and 'Response from calling tool' in msg_content):
                    tool_result_found = True
                    continue
                
                # After finding a tool result, get the next substantive assistant response
                if tool_result_found:
                    if (msg_name == recipient.name or msg_role == 'assistant') and msg_content and msg_content.strip():
                        # Skip follow-up questions that don't contain substantive data
                        lower_content = msg_content.lower()
                        if ('didn\'t contain a question' not in lower_content and
                            'how can i help' not in lower_content and
                            'anything else' not in lower_content and
                            len(msg_content) > 50):  # Substantive responses are usually longer
                            response_text = msg_content
                            break
        
        # If no post-tool response found, fall back to finding the longest assistant response
        if not response_text and hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            longest_response = ""
            for msg in chat_result.chat_history:
                msg_name = msg.get('name', '')
                msg_role = msg.get('role', '')
                msg_content = msg.get('content', '')
                
                if (msg_name == recipient.name or msg_role == 'assistant') and msg_content:
                    # Prefer longer responses (more likely to be substantive)
                    if len(msg_content) > len(longest_response):
                        longest_response = msg_content
            
            if longest_response:
                response_text = longest_response
        
        # Fall back to summary if no response found in history
        if not response_text and hasattr(chat_result, 'summary') and chat_result.summary:
            response_text = chat_result.summary
        
        # Final fallback - get any last non-empty message
        if not response_text and hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            for msg in reversed(chat_result.chat_history):
                content = msg.get('content', '')
                if content and content.strip():
                    response_text = content
                    break
        
        logger.debug(
            "Extracted response",
            response_length=len(response_text),
            response_preview=response_text[:100] if response_text else "EMPTY",
        )
        
        return response_text


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the singleton session manager instance.

    Returns:
        SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        logger.info("Initialized session manager")
    return _session_manager
