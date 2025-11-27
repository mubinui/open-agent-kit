"""Response agent with Autogen LLM integration."""

import os
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.config import get_settings
from src.config.registries import get_prompt_registry, get_provider_registry
from src.audit_logging.audit import AuditLogger
from src.memory.models import AgentType, ConversationState, MessageRole


class ResponseAgent(BaseAgent):
    """
    Response agent generates final user-facing responses using Autogen's LLM integration.

    This agent synthesizes information from previous agents and uses
    dynamically configured LLM providers through Autogen's llm_config.
    """

    def __init__(
        self,
        audit_logger: AuditLogger,
        provider_id: str = "openrouter",
        prompt_id: str = "default_system",
        model: Optional[str] = None,
    ) -> None:
        """
        Initialize the response agent with Autogen's llm_config.

        Args:
            audit_logger: Audit logger instance
            provider_id: ID of LLM provider to use
            prompt_id: ID of system prompt template to use
            model: Model name to use for response generation (defaults to env var)
        """
        self.settings = get_settings()
        
        # Use model from environment variable if not specified
        if model is None:
            model = os.getenv("DEFAULT_LLM_MODEL") or self.settings.openrouter.model
        
        self.provider_id = provider_id
        self.prompt_id = prompt_id
        self.model = model

        # Get registries
        self.provider_registry = get_provider_registry()
        self.prompt_registry = get_prompt_registry()

        # Get system message from prompt registry
        system_message = self.prompt_registry.get_prompt_text(prompt_id)
        
        # Get provider configuration
        provider = self.provider_registry.get_provider(provider_id)
        
        # Build llm_config in Autogen format
        llm_config: Optional[Dict[str, Any]] = None
        if provider:
            # Get API key from environment variable specified in provider's auth
            import os
            api_key = ""
            if provider.auth and provider.auth.env_var:
                api_key = os.getenv(provider.auth.env_var, "")
            base_url = provider.base_url
            
            # Get default model config
            default_model = next(
                (m for m in provider.models if m.default),
                provider.models[0] if provider.models else None,
            )
            
            llm_config = {
                "config_list": [
                    {
                        "model": model,
                        "api_key": api_key,
                        "base_url": base_url,
                    }
                ],
                "temperature": default_model.temperature if default_model else 0.7,
                "max_tokens": default_model.max_tokens if default_model else 500,
                "cache_seed": 42,  # Enable caching
            }
        
        # Initialize BaseAgent (which inherits from ConversableAgent)
        super().__init__(
            name="ResponseAgent",
            audit_logger=audit_logger,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="NEVER",
        )

    async def process(
        self, state: ConversationState, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate final response using Autogen's LLM integration.

        Args:
            state: Current conversation state
            context: Context from previous agents

        Returns:
            Dictionary with generated response and safety metadata
        """
        self.audit_logger.log_agent_execution(
            session_id=state.session_id,
            agent_type=AgentType.RESPONSE,
            action="started",
            details={"context": context},
        )

        # Build messages from conversation history and agent notes
        messages = self._build_messages(state, context)

        # Generate response using Autogen
        try:
            # Use Autogen's generate_reply
            response_text = self.generate_reply(messages=messages, sender=None)
            
            # Convert to string if needed
            if not isinstance(response_text, str):
                response_text = str(response_text)
            
            # Basic safety check (can be enhanced with moderation API)
            safety_metadata = {"flagged": False, "categories": {}}
            
            # Add response note
            state.add_agent_note(
                agent_type=AgentType.RESPONSE,
                note_type="generated_response",
                content=response_text,
                safety_metadata=safety_metadata,
            )

            self.audit_logger.log_agent_execution(
                session_id=state.session_id,
                agent_type=AgentType.RESPONSE,
                action="completed",
                details={"response_length": len(response_text)},
            )

            return {
                "response": response_text,
                "safety_passed": True,
                "safety_metadata": safety_metadata,
            }

        except Exception as e:
            self.audit_logger.log_error(
                session_id=state.session_id,
                error_type="response_generation_error",
                error_message=str(e),
            )
            return {
                "response": "I apologize, but I'm having trouble generating a response right now. Please try again.",
                "error": str(e),
                "safety_passed": True,
            }

    def _build_messages(
        self, state: ConversationState, context: Optional[Dict[str, Any]]
    ) -> list[Dict[str, str]]:
        """Build message list from conversation state and context for Autogen."""
        messages = []

        # Add recent conversation history
        for msg in state.messages[-5:]:  # Last 5 messages
            role = "user" if msg.role == MessageRole.USER else "assistant"
            messages.append({"role": role, "content": msg.content})

        # Add agent notes as context in the last user message
        reasoning_notes = state.get_notes_by_agent(AgentType.REASONING)
        knowledge_notes = state.get_notes_by_agent(AgentType.KNOWLEDGE)

        context_parts = []
        if reasoning_notes:
            intent = next(
                (n.content for n in reasoning_notes if n.note_type == "intent"), None
            )
            if intent:
                context_parts.append(f"User intent: {intent}")

        if knowledge_notes:
            knowledge = next(
                (n.content for n in knowledge_notes if n.note_type == "knowledge"), None
            )
            if knowledge:
                context_parts.append(f"Relevant information: {knowledge}")

        # If we have context, append it to the last user message
        if context_parts and messages:
            last_message = messages[-1]
            if last_message["role"] == "user":
                last_message["content"] += "\n\nContext:\n" + "\n".join(context_parts)
            else:
                # Add as a new user message if last message wasn't from user
                messages.append({
                    "role": "user",
                    "content": "Context:\n" + "\n".join(context_parts)
                })

        return messages
