"""Base agent interface for all chatbot agents."""

from typing import Any, Callable, Dict, List, Optional, Union

from autogen.agentchat import ConversableAgent

from src.audit_logging.audit import AuditLogger
from src.memory.models import ConversationState


class BaseAgent(ConversableAgent):
    """
    Base class for all agents, inheriting from Autogen's ConversableAgent.
    
    This class extends ConversableAgent to integrate with our existing
    conversation state management and audit logging infrastructure.
    """

    def __init__(
        self,
        name: str,
        audit_logger: AuditLogger,
        system_message: Optional[str] = None,
        llm_config: Optional[Union[Dict, bool]] = None,
        human_input_mode: str = "NEVER",
        code_execution_config: Union[Dict, bool] = False,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the agent with Autogen's ConversableAgent.

        Args:
            name: Agent name
            audit_logger: Audit logger instance
            system_message: System message for the agent
            llm_config: LLM configuration dict or False to disable
            human_input_mode: "ALWAYS", "NEVER", or "TERMINATE"
            code_execution_config: Code execution configuration or False
            **kwargs: Additional arguments for ConversableAgent
        """
        # Initialize ConversableAgent
        super().__init__(
            name=name,
            system_message=system_message or "You are a helpful AI assistant.",
            llm_config=llm_config,
            human_input_mode=human_input_mode,
            code_execution_config=code_execution_config,
            **kwargs,
        )
        
        self.audit_logger = audit_logger

    async def process(
        self, state: ConversationState, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process the conversation state and return results.
        
        This method provides a bridge between our existing conversation state
        management and Autogen's message-based system. Subclasses should
        override this to implement specific agent logic.

        Args:
            state: Current conversation state
            context: Optional context from previous agent

        Returns:
            Dictionary containing processing results and metadata
        """
        # Get the latest user message
        if not state.messages:
            return {"error": "No messages in conversation state"}
        
        latest_message = state.messages[-1].content
        
        # Use Autogen's generate_reply to process the message
        reply = self.generate_reply(
            messages=[{"role": "user", "content": latest_message}],
            sender=None,
        )
        
        return {
            "response": reply,
            "agent_name": self.name,
        }

    @property
    def agent_name(self) -> str:
        """Return the agent's name for logging."""
        return self.name
