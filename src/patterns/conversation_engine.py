"""Conversation Pattern Engine for executing different Autogen conversation patterns."""

import asyncio
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4

from autogen.agentchat import ConversableAgent, GroupChat, GroupChatManager, ChatResult


class ConversationPattern(str, Enum):
    """Enumeration of supported conversation patterns."""
    
    TWO_AGENT = "two_agent"
    SEQUENTIAL = "sequential"
    GROUP_CHAT = "group_chat"
    NESTED = "nested"


class ConversationPatternEngine:
    """
    Engine for executing different Autogen conversation patterns.
    
    This class provides a unified interface for executing various conversation
    patterns supported by Autogen 0.2, including two-agent chats, sequential
    chats, group chats, and nested chats. It also supports async execution
    via RabbitMQ message queues.
    """

    def __init__(
        self,
        task_publisher: Optional[Any] = None,
        enable_async: bool = False,
    ) -> None:
        """
        Initialize the conversation pattern engine.
        
        Args:
            task_publisher: Optional AgentTaskPublisher for async execution
            enable_async: Whether to enable async execution via message queues
        """
        self.task_publisher = task_publisher
        self.enable_async = enable_async
        self._pending_results: Dict[UUID, asyncio.Future] = {}

    def execute_two_agent_chat(
        self,
        sender: ConversableAgent,
        recipient: ConversableAgent,
        message: str,
        max_turns: Optional[int] = None,
        summary_method: str = "last_msg",
        **kwargs: Any,
    ) -> ChatResult:
        """
        Execute a two-agent chat using Autogen's initiate_chat.
        
        This pattern involves a conversation between two agents where the sender
        initiates the conversation with a message, and the agents exchange messages
        until a termination condition is met.
        
        Args:
            sender: The agent that initiates the conversation
            recipient: The agent that receives the initial message
            message: The initial message to start the conversation
            max_turns: Maximum number of conversation turns (None for unlimited)
            summary_method: Method for generating conversation summary
                          ("last_msg", "reflection_with_llm")
            **kwargs: Additional arguments passed to initiate_chat
            
        Returns:
            ChatResult containing the conversation history, summary, and cost
            
        Requirements: 1.1, 1.2
        """
        # Prepare initiate_chat arguments
        chat_kwargs: Dict[str, Any] = {
            "message": message,
            "summary_method": summary_method,
        }
        
        # Add max_turns if specified
        if max_turns is not None:
            chat_kwargs["max_turns"] = max_turns
        
        # Merge additional kwargs
        chat_kwargs.update(kwargs)
        
        # Execute the two-agent chat
        chat_result = sender.initiate_chat(
            recipient=recipient,
            **chat_kwargs,
        )
        
        return chat_result

    def execute_sequential_chat(
        self,
        sender: ConversableAgent,
        chat_sequence: List[Dict[str, Any]],
    ) -> List[ChatResult]:
        """
        Execute sequential chats using Autogen's initiate_chats.
        
        This pattern chains multiple two-agent conversations where the summary
        or context from one chat can be carried over to the next chat in the
        sequence.
        
        Args:
            sender: The agent that initiates all chats in the sequence
            chat_sequence: List of chat configurations, each containing:
                - recipient: The recipient agent for this chat
                - message: The initial message (optional if using carryover)
                - max_turns: Maximum turns for this chat (optional)
                - summary_method: Summary method for this chat (optional)
                - carryover: Whether to carry over context from previous chat
                - Additional kwargs for initiate_chat
                
        Returns:
            List of ChatResult objects, one for each chat in the sequence
            
        Requirements: 1.1, 1.2
        """
        # Execute the sequential chats
        chat_results = sender.initiate_chats(chat_sequence)
        
        return chat_results

    def execute_group_chat(
        self,
        agents: List[ConversableAgent],
        initial_message: str,
        max_round: int = 10,
        speaker_selection_method: str = "auto",
        allowed_transitions: Optional[Dict[ConversableAgent, List[ConversableAgent]]] = None,
        speaker_transitions_type: Optional[str] = None,
        send_introductions: bool = False,
        admin_name: str = "GroupChatManager",
        manager_llm_config: Optional[Union[Dict, bool]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Execute a group chat using Autogen's GroupChat and GroupChatManager.
        
        This pattern enables multi-agent conversations where a GroupChatManager
        orchestrates which agent speaks next based on the configured selection
        method.
        
        Args:
            agents: List of agents participating in the group chat
            initial_message: The message that starts the group conversation
            max_round: Maximum number of conversation rounds
            speaker_selection_method: Method for selecting next speaker:
                - "auto": LLM-based selection
                - "round_robin": Sequential rotation through agents
                - "random": Random selection
                - "manual": Manual selection (requires human input)
            allowed_transitions: Dictionary mapping agents to lists of agents
                                they can transition to (for constrained selection)
            speaker_transitions_type: Type of transitions ("allowed" or "disallowed")
                                     Required if allowed_transitions is provided
            send_introductions: Whether agents should introduce themselves
            admin_name: Name for the GroupChatManager
            manager_llm_config: LLM config for the manager (if None, extracted from agents)
            **kwargs: Additional arguments for GroupChat or GroupChatManager
            
        Returns:
            ChatResult containing the group conversation history and summary
            
        Requirements: 1.1, 1.2
        """
        # Validate inputs
        if not agents:
            raise ValueError("At least one agent is required for group chat")
        
        # If allowed_transitions is provided, speaker_transitions_type must be set
        if allowed_transitions is not None and speaker_transitions_type is None:
            speaker_transitions_type = "allowed"  # Default to allowed
        
        # Create GroupChat configuration
        group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=max_round,
            speaker_selection_method=speaker_selection_method,
            allowed_or_disallowed_speaker_transitions=allowed_transitions,
            speaker_transitions_type=speaker_transitions_type,
            send_introductions=send_introductions,
        )
        
        # Create GroupChatManager
        # If manager_llm_config not provided, extract from first agent that has one
        if manager_llm_config is None:
            for agent in agents:
                if hasattr(agent, 'llm_config') and agent.llm_config:
                    manager_llm_config = agent.llm_config
                    break
        
        # If still None, set to False to avoid OpenAI client creation
        if manager_llm_config is None:
            manager_llm_config = False
        
        manager = GroupChatManager(
            groupchat=group_chat,
            name=admin_name,
            llm_config=manager_llm_config,
        )
        
        # Initiate the group chat from the first agent
        chat_result = agents[0].initiate_chat(
            recipient=manager,
            message=initial_message,
            **kwargs,
        )
        
        return chat_result

    def register_nested_chat(
        self,
        trigger_agent: ConversableAgent,
        nested_chats: List[Dict[str, Any]],
        trigger: Optional[Union[str, Callable]] = None,
        position: int = 2,
        **kwargs: Any,
    ) -> None:
        """
        Register nested chats for an agent using Autogen's register_nested_chats.
        
        Nested chats allow packaging complex workflows into a single agent by
        triggering internal conversation sequences based on conditions. When
        the trigger condition is met, the nested chat sequence executes before
        the agent generates its final response.
        
        Args:
            trigger_agent: The agent that will trigger nested chats
            nested_chats: List of nested chat configurations, each containing:
                - recipient: The recipient agent for the nested chat
                - message: Message or callable that generates the message
                - max_turns: Maximum turns for the nested chat (optional)
                - summary_method: Summary method (optional)
                - Additional kwargs for the nested chat
            trigger: Condition for triggering nested chats:
                - String: Trigger when message contains this string
                - Callable: Custom function that returns True to trigger
                - None: Always trigger
            position: Position in the reply sequence where nested chat executes
                     (default: 2, after generate_reply)
            **kwargs: Additional arguments for register_nested_chats
            
        Requirements: 1.1, 1.2
        """
        # Prepare trigger condition
        trigger_condition: Optional[Union[str, Callable]] = trigger
        
        # Register the nested chats with the trigger agent
        trigger_agent.register_nested_chats(
            trigger=trigger_condition,
            chat_queue=nested_chats,
            position=position,
            **kwargs,
        )


    async def execute_two_agent_chat_async(
        self,
        session_id: UUID,
        sender_agent_id: str,
        recipient_agent_id: str,
        message: str,
        context: Dict[str, Any],
        timeout: float = 300.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute a two-agent chat asynchronously via message queue.
        
        This method publishes the conversation task to RabbitMQ and waits
        for the result to be published back to the result queue.
        
        Args:
            session_id: Session ID for tracking the conversation
            sender_agent_id: ID of the sender agent
            recipient_agent_id: ID of the recipient agent
            message: The initial message
            context: Additional context for the conversation
            timeout: Maximum time to wait for result (seconds)
            **kwargs: Additional arguments for the conversation
            
        Returns:
            Dictionary containing the conversation result
            
        Raises:
            RuntimeError: If async execution is not enabled
            TimeoutError: If the conversation exceeds the timeout
            
        Requirements: 8.1, 8.2, 8.5
        """
        if not self.enable_async or self.task_publisher is None:
            raise RuntimeError(
                "Async execution not enabled. Initialize with task_publisher and enable_async=True"
            )
        
        # Import here to avoid circular dependency
        from src.infrastructure.message_broker import AgentTask
        from datetime import datetime
        
        # Create a task for the sender agent
        task_id = uuid4()
        task = AgentTask(
            task_id=task_id,
            session_id=session_id,
            agent_id=sender_agent_id,
            message=message,
            context={
                'recipient_agent_id': recipient_agent_id,
                'pattern': 'two_agent',
                'kwargs': kwargs,
                **context,
            },
            created_at=datetime.utcnow(),
            priority=context.get('priority', 0),
        )
        
        # Create a future for the result
        result_future: asyncio.Future[Dict[str, Any]] = asyncio.Future()
        self._pending_results[task_id] = result_future
        
        try:
            # Publish the task
            await self.task_publisher.publish_task(task)
            
            # Wait for the result with timeout
            result = await asyncio.wait_for(result_future, timeout=timeout)
            
            return result
            
        except asyncio.TimeoutError:
            # Clean up the pending result
            self._pending_results.pop(task_id, None)
            raise TimeoutError(
                f"Conversation timed out after {timeout} seconds "
                f"(task_id={task_id}, session_id={session_id})"
            )
        except Exception as e:
            # Clean up the pending result
            self._pending_results.pop(task_id, None)
            raise
    
    async def handle_task_result(
        self,
        task_id: UUID,
        result: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        """
        Handle a task result from the message queue.
        
        This method is called when a result is received from the result queue,
        completing the corresponding future.
        
        Args:
            task_id: ID of the completed task
            result: Result data from the task
            error: Optional error message if the task failed
            
        Requirements: 8.1, 8.2, 8.5
        """
        future = self._pending_results.pop(task_id, None)
        
        if future is None:
            # No pending future for this task (might have timed out)
            return
        
        if error:
            # Set exception on the future
            future.set_exception(RuntimeError(f"Task failed: {error}"))
        else:
            # Set result on the future
            future.set_result(result)
    
    async def execute_sequential_chat_async(
        self,
        session_id: UUID,
        chat_sequence: List[Dict[str, Any]],
        context: Dict[str, Any],
        timeout: float = 600.0,
    ) -> List[Dict[str, Any]]:
        """
        Execute sequential chats asynchronously via message queue.
        
        This method executes a sequence of two-agent chats asynchronously,
        carrying over context between chats.
        
        Args:
            session_id: Session ID for tracking the conversation
            chat_sequence: List of chat configurations
            context: Additional context for the conversations
            timeout: Maximum time to wait for all chats (seconds)
            
        Returns:
            List of conversation results
            
        Requirements: 8.1, 8.2, 8.5
        """
        results = []
        accumulated_context = context.copy()
        
        for chat_config in chat_sequence:
            # Execute each chat in sequence
            result = await self.execute_two_agent_chat_async(
                session_id=session_id,
                sender_agent_id=chat_config['sender_id'],
                recipient_agent_id=chat_config['recipient_id'],
                message=chat_config.get('message', ''),
                context=accumulated_context,
                timeout=timeout / len(chat_sequence),  # Divide timeout among chats
                **chat_config.get('kwargs', {}),
            )
            
            results.append(result)
            
            # Carry over summary to next chat
            if 'summary' in result:
                accumulated_context['carryover'] = result['summary']
        
        return results
    
    async def execute_group_chat_async(
        self,
        session_id: UUID,
        agent_ids: List[str],
        initial_message: str,
        context: Dict[str, Any],
        timeout: float = 600.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute a group chat asynchronously via message queue.
        
        Args:
            session_id: Session ID for tracking the conversation
            agent_ids: List of agent IDs participating in the group chat
            initial_message: The initial message
            context: Additional context for the conversation
            timeout: Maximum time to wait for result (seconds)
            **kwargs: Additional arguments for the group chat
            
        Returns:
            Dictionary containing the conversation result
            
        Requirements: 8.1, 8.2, 8.5
        """
        if not self.enable_async or self.task_publisher is None:
            raise RuntimeError(
                "Async execution not enabled. Initialize with task_publisher and enable_async=True"
            )
        
        # Import here to avoid circular dependency
        from src.infrastructure.message_broker import AgentTask
        from datetime import datetime
        
        # Create a task for the group chat orchestrator
        task_id = uuid4()
        task = AgentTask(
            task_id=task_id,
            session_id=session_id,
            agent_id='group_chat_manager',  # Special agent for group chats
            message=initial_message,
            context={
                'agent_ids': agent_ids,
                'pattern': 'group_chat',
                'kwargs': kwargs,
                **context,
            },
            created_at=datetime.utcnow(),
            priority=context.get('priority', 0),
        )
        
        # Create a future for the result
        result_future: asyncio.Future[Dict[str, Any]] = asyncio.Future()
        self._pending_results[task_id] = result_future
        
        try:
            # Publish the task
            await self.task_publisher.publish_task(task)
            
            # Wait for the result with timeout
            result = await asyncio.wait_for(result_future, timeout=timeout)
            
            return result
            
        except asyncio.TimeoutError:
            # Clean up the pending result
            self._pending_results.pop(task_id, None)
            raise TimeoutError(
                f"Group chat timed out after {timeout} seconds "
                f"(task_id={task_id}, session_id={session_id})"
            )
        except Exception as e:
            # Clean up the pending result
            self._pending_results.pop(task_id, None)
            raise
