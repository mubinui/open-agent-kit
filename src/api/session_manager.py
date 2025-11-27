"""Session manager for handling conversation sessions with Autogen agents."""

from typing import Any, Dict, Optional
from uuid import UUID

from autogen.agentchat import ConversableAgent

from src.audit_logging import get_logger
from src.config.agent_models import AgentConfig, AgentsConfig
from src.config.registries import get_prompt_registry, get_provider_registry
from src.config.tool_registry import get_tool_registry
from src.config.workflow_models import ConversationPattern, WorkflowConfig
from src.config.workflow_registry import get_workflow_registry, WorkflowRegistry
from src.factory.agent_factory import AgentFactory
from src.memory.inmemory import InMemoryConversationStore
from src.memory.models import ConversationState, MessageRole
from src.memory.store import ConversationStore
from src.patterns.conversation_engine import ConversationPatternEngine

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
    ) -> None:
        """
        Initialize the session manager.

        Args:
            conversation_store: Store for persisting conversation state (default store, can be overridden per workflow)
            agent_factory: Factory for creating agents
            workflow_registry: Registry for workflow configurations
        """
        self.default_conversation_store = conversation_store or InMemoryConversationStore()
        
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
        
        # Cache for active sessions and their agents
        self._session_agents: Dict[UUID, Dict[str, ConversableAgent]] = {}
        self._session_workflows: Dict[UUID, WorkflowConfig] = {}
        self._session_stores: Dict[UUID, ConversationStore] = {}
        
        # Initialize MongoDB store if configured
        self._mongo_store: Optional[ConversationStore] = None
        self._postgres_store: Optional[ConversationStore] = None
        self._init_persistence_stores()

    def _init_persistence_stores(self) -> None:
        """Initialize persistence stores based on configuration."""
        from src.config.settings import get_settings
        
        settings = get_settings()
        
        # Initialize PostgreSQL store if configured
        if settings.memory.database_url:
            try:
                from src.infrastructure.database.postgres_store import PostgreSQLConversationStore
                
                self._postgres_store = PostgreSQLConversationStore(
                    database_url=settings.memory.database_url
                )
                logger.info("PostgreSQL conversation store initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL store: {e}")
        
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
        persistence = workflow.persistence
        
        if persistence == "mongo_only":
            if self._mongo_store is None:
                raise ValueError(
                    f"Workflow {workflow.id} requires MongoDB but MONGODB_URL is not configured"
                )
            logger.debug(f"Using MongoDB store for workflow {workflow.id}")
            return self._mongo_store
        
        elif persistence == "postgres":
            if self._postgres_store is not None:
                logger.debug(f"Using PostgreSQL store for workflow {workflow.id}")
                return self._postgres_store
            else:
                logger.warning(
                    f"PostgreSQL not configured for workflow {workflow.id}, "
                    f"falling back to default store"
                )
                return self.default_conversation_store
        
        else:
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
    ) -> Dict[str, Any]:
        """
        Execute a workflow based on its pattern.

        Args:
            session_id: Session identifier
            workflow: Workflow configuration
            agents: Dictionary of agent instances
            message: User message
            max_turns: Optional override for max turns

        Returns:
            Dictionary containing response and metadata

        Raises:
            ValueError: If workflow execution fails
        """
        pattern = workflow.pattern

        if pattern == ConversationPattern.TWO_AGENT:
            return await self._execute_two_agent_workflow(
                workflow, agents, message, max_turns
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
        else:
            raise ValueError(f"Unsupported conversation pattern: {pattern}")

    async def _execute_two_agent_workflow(
        self,
        workflow: WorkflowConfig,
        agents: Dict[str, ConversableAgent],
        message: str,
        max_turns: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a two-agent workflow."""
        sender = agents.get(workflow.entry_agent_id)
        recipient = agents.get(workflow.recipient_agent_id)

        if sender is None or recipient is None:
            raise ValueError("Required agents not found for two-agent workflow")

        # Use workflow max_turns if not overridden
        turns = max_turns if max_turns is not None else workflow.max_turns

        logger.debug(
            "Executing two-agent workflow",
            sender=workflow.entry_agent_id,
            sender_name=sender.name,
            sender_has_llm=sender.llm_config is not False,
            recipient=workflow.recipient_agent_id,
            recipient_name=recipient.name,
            recipient_has_llm=recipient.llm_config is not False,
            max_turns=turns,
        )

        chat_result = self.pattern_engine.execute_two_agent_chat(
            sender=sender,
            recipient=recipient,
            message=message,
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

    def _extract_response_from_chat_result(
        self,
        chat_result: Any,
        recipient: ConversableAgent,
    ) -> str:
        """Extract response text from a chat result."""
        response_text = ""
        
        # Log what we got for debugging
        logger.debug(
            "Extracting response from chat result",
            has_summary=hasattr(chat_result, 'summary'),
            summary_value=getattr(chat_result, 'summary', None),
            has_chat_history=hasattr(chat_result, 'chat_history'),
            chat_history_len=len(getattr(chat_result, 'chat_history', [])),
        )
        
        # First try to get from chat_history - last message from recipient
        if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            for msg in reversed(chat_result.chat_history):
                # Check if message is from the recipient (by name or role)
                msg_name = msg.get('name', '')
                msg_role = msg.get('role', '')
                msg_content = msg.get('content', '')
                
                # Skip empty messages or tool calls
                if not msg_content or msg_content.strip() == '':
                    continue
                    
                # Get message from recipient or assistant role
                if msg_name == recipient.name or msg_role == 'assistant':
                    response_text = msg_content
                    break
        
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
