"""Reasoning agent for intent interpretation and planning."""

import os
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.audit_logging.audit import AuditLogger
from src.config.registries import get_provider_registry
from src.config.settings import get_settings
from src.memory.models import AgentType, ConversationState


class ReasoningAgent(BaseAgent):
    """
    Reasoning agent interprets user intent and creates execution plans.

    This agent analyzes the conversation history to understand what the user
    wants and formulates a plan for how to satisfy the request.
    Uses Autogen's ConversableAgent with llm_config for LLM-powered reasoning.
    """

    def __init__(
        self,
        audit_logger: AuditLogger,
        provider_id: str = "openrouter",
        model: Optional[str] = None,
    ) -> None:
        """
        Initialize the reasoning agent with Autogen's llm_config.

        Args:
            audit_logger: Audit logger instance
            provider_id: ID of LLM provider to use
            model: Model name to use for reasoning (defaults to env var or gpt-oss-20b)
        """
        # Use model from environment variable if not specified
        if model is None:
            settings = get_settings()
            model = os.getenv("DEFAULT_LLM_MODEL") or settings.openrouter.model
        
        # Get provider configuration
        provider_registry = get_provider_registry()
        provider = provider_registry.get_provider(provider_id)
        
        # Build llm_config in Autogen format
        llm_config: Optional[Dict[str, Any]] = None
        if provider:
            # Get API key from environment variable specified in provider auth
            api_key = ""
            if provider.auth and provider.auth.env_var:
                api_key = os.getenv(provider.auth.env_var, "")
            base_url = provider.base_url
            
            llm_config = {
                "config_list": [
                    {
                        "model": model,
                        "api_key": api_key,
                        "base_url": base_url,
                    }
                ],
                "temperature": 0.7,
                "cache_seed": 42,  # Enable caching
            }
        
        # System message for intent detection and planning
        system_message = """You are a reasoning agent that analyzes user intent and creates execution plans.

Your responsibilities:
1. Detect the user's intent from their message
2. Determine if knowledge retrieval is needed
3. Create a clear plan for how to respond

Respond in JSON format with:
{
    "intent": "information_request|assistance_request|greeting|general_query",
    "requires_knowledge": true|false,
    "plan": "Brief description of how to handle this request"
}"""

        # Initialize BaseAgent (which inherits from ConversableAgent)
        super().__init__(
            name="ReasoningAgent",
            audit_logger=audit_logger,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="NEVER",
        )
        
        self.provider_id = provider_id
        self.model = model

    async def process(
        self, state: ConversationState, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze conversation and generate reasoning plan using Autogen's LLM.

        Args:
            state: Current conversation state
            context: Optional context from orchestrator

        Returns:
            Dictionary with intent analysis and plan
        """
        self.audit_logger.log_agent_execution(
            session_id=state.session_id,
            agent_type=AgentType.REASONING,
            action="started",
            details={"turn": state.turn_count},
        )

        # Get the latest user message
        if not state.messages:
            return {"error": "No messages in conversation state"}

        latest_message = state.messages[-1].content

        # Use Autogen's generate_reply for LLM-powered reasoning
        try:
            # Build message history for context
            messages = [{"role": "user", "content": latest_message}]
            
            # Generate reply using Autogen's LLM integration
            reply = self.generate_reply(messages=messages, sender=None)
            
            # Parse the JSON response (with fallback to simple parsing)
            import json
            try:
                result = json.loads(reply) if isinstance(reply, str) else reply
                intent = result.get("intent", "general_query")
                plan = result.get("plan", "Process query and generate appropriate response")
                requires_knowledge = result.get("requires_knowledge", False)
            except (json.JSONDecodeError, AttributeError):
                # Fallback to simple intent detection if LLM doesn't return JSON
                intent = self._detect_intent(latest_message)
                plan = self._generate_plan(intent, state)
                requires_knowledge = self._requires_knowledge(intent)
        
        except Exception as e:
            # Fallback to rule-based reasoning if LLM fails
            self.audit_logger.log_error(
                session_id=state.session_id,
                error_type="reasoning_llm_error",
                error_message=str(e),
            )
            intent = self._detect_intent(latest_message)
            plan = self._generate_plan(intent, state)
            requires_knowledge = self._requires_knowledge(intent)

        # Add reasoning note to conversation state
        state.add_agent_note(
            agent_type=AgentType.REASONING,
            note_type="intent",
            content=intent,
            confidence=0.8,
        )

        state.add_agent_note(
            agent_type=AgentType.REASONING,
            note_type="plan",
            content=plan,
        )

        self.audit_logger.log_agent_execution(
            session_id=state.session_id,
            agent_type=AgentType.REASONING,
            action="completed",
            details={"intent": intent, "plan": plan},
        )

        return {
            "intent": intent,
            "plan": plan,
            "requires_knowledge": requires_knowledge,
        }

    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message (fallback method)."""
        message_lower = message.lower()

        if any(word in message_lower for word in ["what", "explain", "tell me", "how"]):
            return "information_request"
        elif any(word in message_lower for word in ["help", "can you", "please"]):
            return "assistance_request"
        elif any(word in message_lower for word in ["hi", "hello", "hey"]):
            return "greeting"
        else:
            return "general_query"

    def _generate_plan(self, intent: str, state: ConversationState) -> str:
        """Generate execution plan based on intent (fallback method)."""
        plans = {
            "information_request": "Retrieve relevant information and provide detailed explanation",
            "assistance_request": "Identify specific help needed and provide step-by-step guidance",
            "greeting": "Respond with friendly greeting and offer assistance",
            "general_query": "Analyze query context and provide appropriate response",
        }
        return plans.get(intent, "Process query and generate appropriate response")

    def _requires_knowledge(self, intent: str) -> bool:
        """Determine if knowledge agent is needed (fallback method)."""
        return intent in ["information_request", "general_query"]
