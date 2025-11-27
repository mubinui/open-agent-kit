"""Knowledge agent for information retrieval."""

from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.config.registries import get_provider_registry
from src.audit_logging.audit import AuditLogger
from src.memory.models import AgentType, ConversationState


class KnowledgeAgent(BaseAgent):
    """
    Knowledge agent retrieves relevant information from external sources.

    This agent can query APIs, databases, or other knowledge sources to
    gather facts and context needed to answer user questions.
    
    Note: This will be migrated to use RetrieveUserProxyAgent for RAG in future tasks.
    For now, it uses simple web search through configured providers.
    """

    def __init__(
        self,
        audit_logger: AuditLogger,
        search_provider_id: str = "duckduckgo",
    ) -> None:
        """
        Initialize the knowledge agent.

        Args:
            audit_logger: Audit logger instance
            search_provider_id: ID of search provider to use
        """
        # Initialize BaseAgent (ConversableAgent) without LLM config
        # This agent doesn't need LLM - it just retrieves information
        super().__init__(
            name="KnowledgeAgent",
            audit_logger=audit_logger,
            system_message="You are a knowledge retrieval agent.",
            llm_config=False,  # No LLM needed for this agent
            human_input_mode="NEVER",
        )
        
        self.search_provider_id = search_provider_id
        self.provider_registry = get_provider_registry()
        self._connectors: Dict[str, Any] = {}

    async def process(
        self, state: ConversationState, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant knowledge based on conversation context.

        Args:
            state: Current conversation state
            context: Context from reasoning agent (intent, plan)

        Returns:
            Dictionary with retrieved knowledge
        """
        self.audit_logger.log_agent_execution(
            session_id=state.session_id,
            agent_type=AgentType.KNOWLEDGE,
            action="started",
            details={"context": context},
        )

        # Check if knowledge retrieval is needed
        if context and not context.get("requires_knowledge", False):
            return {"knowledge": None, "skipped": True}

        # Get the latest user message to use as search query
        user_messages = state.get_messages_by_role(state.messages[-1].role)
        if user_messages and len(state.messages) > 0:
            # Use the latest user message as search query
            latest_message = state.messages[-1].content
            
            # Try to get search provider and perform web search
            try:
                search_connector = self.provider_registry.get_instance(
                    self.search_provider_id
                )
                knowledge = await self._retrieve_knowledge_from_web(
                    latest_message, search_connector
                )
                source = self.search_provider_id
            except Exception as e:
                knowledge = f"Knowledge retrieval unavailable: {str(e)}"
                source = "error"
        else:
            knowledge = "No user query found to search for."
            source = "none"

        # Add knowledge note to conversation state
        state.add_agent_note(
            agent_type=AgentType.KNOWLEDGE,
            note_type="knowledge",
            content=knowledge,
            source=source,
        )

        self.audit_logger.log_agent_execution(
            session_id=state.session_id,
            agent_type=AgentType.KNOWLEDGE,
            action="completed",
            details={"knowledge_length": len(knowledge), "source": source},
        )

        return {
            "knowledge": knowledge,
            "sources": [source],
        }

    async def _retrieve_knowledge_from_web(
        self, query: str, search_connector: Any
    ) -> str:
        """
        Retrieve knowledge from the web using configured search provider.

        Args:
            query: Search query extracted from user message
            search_connector: Search provider instance

        Returns:
            Formatted search results or error message
        """
        try:
            # Perform search using the connector
            search_results = search_connector.search_and_format(query)
            
            if search_results and search_results != "No search results found.":
                return f"Web search results for '{query}':\n\n{search_results}"
            else:
                return f"No relevant web results found for '{query}'."
                
        except Exception as e:
            return f"Error performing web search: {str(e)}"

    def register_connector(self, name: str, connector: Any) -> None:
        """Register a knowledge connector (API, DB, etc.)."""
        self._connectors[name] = connector

    def list_connectors(self) -> list[str]:
        """List available knowledge connectors."""
        return list(self._connectors.keys())
