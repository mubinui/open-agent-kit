"""Orchestrator for managing agent coordination and conversation flow."""

from typing import Any, Dict, Optional

from autogen.agentchat import ChatResult

from src.agents.knowledge import KnowledgeAgent
from src.agents.reasoning import ReasoningAgent
from src.agents.response import ResponseAgent
from src.config import get_settings
from src.audit_logging.audit import AuditLogger
from src.memory.models import AgentType, ConversationState, MessageRole
from src.memory.store import ConversationStore


class Orchestrator:
    """
    Orchestrator manages the sequential flow between agents using Autogen's initiate_chat.

    This is the main entry point for processing user messages through
    the multi-agent pipeline. It uses Autogen's conversation patterns
    for agent coordination.
    """

    def __init__(
        self,
        conversation_store: ConversationStore,
        audit_logger: AuditLogger,
    ) -> None:
        """Initialize the orchestrator with dependencies."""
        self.store = conversation_store
        self.audit_logger = audit_logger
        self.settings = get_settings()

        # Initialize agents with Autogen's ConvertibleAgent pattern
        self.reasoning_agent = ReasoningAgent(audit_logger)
        self.knowledge_agent = KnowledgeAgent(audit_logger)
        self.response_agent = ResponseAgent(audit_logger)

    async def create_session(self) -> ConversationState:
        """Create a new conversation session."""
        state = await self.store.create_session()
        self.audit_logger.log_session_lifecycle(
            session_id=state.session_id,
            event="created",
        )
        return state

    async def process_message(
        self, session_id: Any, user_message: str
    ) -> Dict[str, Any]:
        """
        Process a user message through the agent pipeline using Autogen's patterns.

        This method now uses a hybrid approach:
        1. Uses our custom process() methods for agents that need conversation state
        2. Prepares for future migration to pure Autogen initiate_chat pattern

        Args:
            session_id: Conversation session ID
            user_message: User's input message

        Returns:
            Dictionary with response and metadata (compatible with ChatResult)
        """
        # Get conversation state
        state = await self.store.get_session(session_id)
        if not state:
            return {"error": "Session not found"}

        if not state.active:
            return {"error": "Session is no longer active"}

        # Log user input
        self.audit_logger.log_user_input(
            session_id=state.session_id,
            content=user_message,
        )

        # Add user message to state
        state.add_message(MessageRole.USER, user_message)
        state.increment_turn()

        # Check turn limit
        if state.turn_count > self.settings.app.max_conversation_turns:
            state.active = False
            await self.store.update_session(state)
            return {
                "response": "We've reached the maximum conversation length. Please start a new session.",
                "session_ended": True,
            }

        # Execute sequential agent pipeline
        # Note: This uses our custom process() methods which internally use
        # Autogen's generate_reply(). In future tasks, this will be refactored
        # to use initiate_chat() for pure Autogen conversation patterns.
        try:
            # Step 1: Reasoning Agent (uses Autogen's LLM integration)
            reasoning_result = await self.reasoning_agent.process(state)

            # Step 2: Knowledge Agent (if needed)
            knowledge_result = await self.knowledge_agent.process(
                state, context=reasoning_result
            )

            # Step 3: Response Agent (uses Autogen's LLM integration)
            response_result = await self.response_agent.process(
                state,
                context={
                    "reasoning": reasoning_result,
                    "knowledge": knowledge_result,
                },
            )

            # Add an assistant message to state
            response_text = response_result.get(
                "response", 
                "I apologize, but I couldn't generate a proper response."
            )
            state.add_message(MessageRole.ASSISTANT, response_text)

            # Save an updated state
            await self.store.update_session(state)

            # Log response
            self.audit_logger.log_assistant_response(
                session_id=state.session_id,
                content=response_text,
                metadata={
                    "safety_passed": response_result.get("safety_passed", True),
                    "turn": state.turn_count,
                },
            )

            # Return result in a format compatible with ChatResult
            return {
                "response": response_text,
                "session_id": str(state.session_id),
                "turn": state.turn_count,
                "safety_passed": response_result.get("safety_passed", True),
                "chat_history": [
                    {"role": msg.role.value, "content": msg.content}
                    for msg in state.messages
                ],
            }

        except Exception as e:
            self.audit_logger.log_error(
                session_id=state.session_id,
                error_type="orchestration_error",
                error_message=str(e),
            )
            return {
                "response": "An error occurred while processing your message. Please try again.",
                "error": str(e),
            }

    async def end_session(self, session_id: Any) -> bool:
        """End a conversation session."""
        state = await self.store.get_session(session_id)
        if not state:
            return False

        state.active = False
        await self.store.update_session(state)

        self.audit_logger.log_session_lifecycle(
            session_id=state.session_id,
            event="ended",
            metadata={"turns": state.turn_count},
        )

        return True

    async def get_session_history(self, session_id: Any) -> Dict[str, Any]:
        """Get conversation history for a session."""
        state = await self.store.get_session(session_id)
        if not state:
            return {"error": "Session not found"}

        return {
            "session_id": str(state.session_id),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                for msg in state.messages
            ],
            "turn_count": state.turn_count,
            "active": state.active,
        }

    async def cleanup(self) -> None:
        """Clean up resources."""
        # No cleanup needed for Autogen agents
        pass
