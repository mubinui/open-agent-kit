"""Agent factory for creating Autogen ConversableAgent instances from configurations."""

from typing import Any, Optional

from autogen.agentchat import ConversableAgent

from src.audit_logging import get_logger
from src.config.agent_models import AgentConfig, AgentType, RetrieveConfig
from src.config.registries import PromptRegistry, ProviderRegistry
from src.config.tool_registry import ToolRegistry
from src.infrastructure.providers import ProviderAdapter

logger = get_logger(__name__)


class AgentFactory:
    """
    Factory for creating Autogen ConversableAgent instances from JSON configurations.
    
    This factory maps provider configurations to Autogen's llm_config format
    and supports creating different types of agents including RetrieveUserProxyAgent.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        prompt_registry: PromptRegistry,
        tool_registry: Optional[ToolRegistry] = None,
        provider_adapter: Optional[ProviderAdapter] = None,
    ) -> None:
        """
        Initialize the agent factory.

        Args:
            provider_registry: Registry for LLM providers (legacy, for backward compatibility)
            prompt_registry: Registry for prompt templates
            tool_registry: Optional registry for tools
            provider_adapter: Optional provider adapter for unified client management
        """
        self.provider_registry = provider_registry
        self.prompt_registry = prompt_registry
        self.tool_registry = tool_registry
        self.provider_adapter = provider_adapter

    def create_agent(self, agent_config: AgentConfig) -> ConversableAgent:
        """
        Create a ConversableAgent from configuration.

        Args:
            agent_config: Agent configuration

        Returns:
            Configured ConversableAgent instance

        Raises:
            ValueError: If configuration is invalid or agent type not supported
        """
        # Validate configuration
        agent_config.validate_config()

        # Route to appropriate creation method based on type
        if agent_config.type == AgentType.CONVERSABLE:
            return self._create_conversable_agent(agent_config)
        elif agent_config.type == AgentType.RETRIEVE_USER_PROXY:
            return self._create_retrieve_user_proxy_agent(agent_config)
        elif agent_config.type == AgentType.GROUP_CHAT_MANAGER:
            # GroupChatManager will be created separately with GroupChat instance
            raise ValueError(
                "GroupChatManager should be created using GroupChat, not directly"
            )
        else:
            raise ValueError(f"Unsupported agent type: {agent_config.type}")

    def create_retrieve_agent(
        self,
        agent_config: AgentConfig,
    ) -> "RetrieveUserProxyAgent":
        """
        Create a RetrieveUserProxyAgent for RAG.

        Note: Local vector DB clients have been removed. Use the external
        RAG pipeline service (src.tools.rag_pipeline) for document retrieval.

        Args:
            agent_config: Agent configuration with retrieve_config

        Returns:
            Configured RetrieveUserProxyAgent instance

        Raises:
            ValueError: If retrieve_config is missing or invalid
        """
        if agent_config.type != AgentType.RETRIEVE_USER_PROXY:
            raise ValueError(
                f"Agent {agent_config.id} is not a retrieve_user_proxy agent"
            )

        if agent_config.retrieve_config is None:
            raise ValueError(
                f"Agent {agent_config.id} requires retrieve_config"
            )

        return self._create_retrieve_user_proxy_agent(agent_config)

    def register_tools_for_agent(
        self,
        agent: ConversableAgent,
        tool_ids: list[str],
    ) -> None:
        """
        Register tools with an agent using Autogen's pattern.

        This method registers tools with a single agent (both for LLM and execution).
        For more complex scenarios where different agents call and execute tools,
        use the ToolRegistry directly.

        Args:
            agent: Agent to register tools with
            tool_ids: List of tool IDs to register

        Raises:
            ValueError: If tool_registry is not configured or tool not found
        """
        if self.tool_registry is None:
            raise ValueError("Tool registry not configured")

        if not tool_ids:
            return

        for tool_id in tool_ids:
            try:
                # Register tool with agent (both LLM and execution)
                self.tool_registry.register_tool_with_agent(tool_id, agent)
                logger.info(
                    "Registered tool with agent",
                    tool_id=tool_id,
                    agent_name=agent.name,
                )
            except Exception as e:
                logger.error(
                    "Failed to register tool",
                    tool_id=tool_id,
                    agent_name=agent.name,
                    error=str(e),
                )
                # Log error but continue with other tools
                # This allows partial tool registration rather than failing completely
                logger.warning(
                    "Continuing with remaining tools after error",
                    tool_id=tool_id,
                )

    def _create_conversable_agent(
        self, agent_config: AgentConfig
    ) -> ConversableAgent:
        """
        Create a standard ConversableAgent.

        Args:
            agent_config: Agent configuration

        Returns:
            ConversableAgent instance
        """
        # Build llm_config from provider configuration
        llm_config = self._build_llm_config(agent_config)

        # Get system message (from config or prompt registry)
        system_message = agent_config.system_message
        if system_message is None and agent_config.id:
            # Try to get from prompt registry
            system_message = self.prompt_registry.get_prompt_text(
                f"{agent_config.id}_system",
                default="You are a helpful AI assistant.",
            )

        # Create the agent
        agent = ConversableAgent(
            name=agent_config.name,
            system_message=system_message or "You are a helpful AI assistant.",
            llm_config=llm_config,
            human_input_mode=agent_config.human_input_mode.value,
            code_execution_config=agent_config.code_execution_config,
            max_consecutive_auto_reply=agent_config.max_consecutive_auto_reply,
            description=agent_config.description,
        )

        # Register tools if specified
        if agent_config.tools:
            if self.tool_registry:
                try:
                    self.register_tools_for_agent(agent, agent_config.tools)
                except Exception as e:
                    logger.error(
                        "Failed to register tools with agent",
                        agent_id=agent_config.id,
                        tools=agent_config.tools,
                        error=str(e),
                    )
                    # Don't fail agent creation, just log the error
            else:
                logger.warning(
                    "Tool registry not configured, skipping tool registration",
                    agent_id=agent_config.id,
                    tools=agent_config.tools,
                )

        logger.info(
            "Created ConversableAgent",
            agent_id=agent_config.id,
            agent_name=agent_config.name,
            has_llm=llm_config is not False,
            tools_count=len(agent_config.tools) if agent_config.tools else 0,
        )

        return agent

    def _create_retrieve_user_proxy_agent(
        self,
        agent_config: AgentConfig,
    ) -> "RetrieveUserProxyAgent":
        """
        Create a RetrieveUserProxyAgent for RAG.

        Note: Local vector DB clients (chromadb, pgvector, qdrant) have been removed.
        Use the external RAG pipeline service (src.tools.rag_pipeline) for document
        retrieval instead of this agent type.

        Args:
            agent_config: Agent configuration

        Returns:
            RetrieveUserProxyAgent instance
        """
        # Import here to avoid circular dependency
        try:
            from autogen.agentchat.contrib.retrieve_user_proxy_agent import (
                RetrieveUserProxyAgent,
            )
        except ImportError as e:
            raise ImportError(
                "RetrieveUserProxyAgent requires autogen[retrievechat] extras. "
                "Install with: pip install 'pyautogen[retrievechat]'"
            ) from e

        if agent_config.retrieve_config is None:
            raise ValueError(
                f"Agent {agent_config.id} requires retrieve_config"
            )

        retrieve_config = agent_config.retrieve_config

        # Build retrieve_config dict for Autogen
        autogen_retrieve_config = {
            "task": retrieve_config.task,
            "docs_path": retrieve_config.docs_path,
            "chunk_token_size": retrieve_config.chunk_token_size,
            "model": retrieve_config.embedding_model,
            "collection_name": retrieve_config.collection_name,
            "get_or_create": retrieve_config.get_or_create,
        }

        # Use legacy configuration from retrieve_config if provided
        if retrieve_config.db_config:
            autogen_retrieve_config.update(retrieve_config.db_config)

        # Create the agent
        agent = RetrieveUserProxyAgent(
            name=agent_config.name,
            human_input_mode=agent_config.human_input_mode.value,
            max_consecutive_auto_reply=agent_config.max_consecutive_auto_reply,
            retrieve_config=autogen_retrieve_config,
            code_execution_config=agent_config.code_execution_config,
            description=agent_config.description,
        )

        logger.info(
            "Created RetrieveUserProxyAgent",
            agent_id=agent_config.id,
            agent_name=agent_config.name,
            collection=retrieve_config.collection_name,
        )

        return agent

    def _build_llm_config(
        self, agent_config: AgentConfig
    ) -> dict[str, Any] | bool:
        """
        Build Autogen llm_config from agent configuration.

        Args:
            agent_config: Agent configuration

        Returns:
            llm_config dict or False to disable LLM

        Raises:
            ValueError: If provider not found or configuration invalid
        """
        # Handle None or False - both disable LLM
        if agent_config.llm_config is None or agent_config.llm_config is False:
            return False

        llm_cfg = agent_config.llm_config

        # Get provider configuration
        provider = self.provider_registry.get_provider(llm_cfg.provider_id)
        if provider is None:
            raise ValueError(
                f"Provider not found: {llm_cfg.provider_id}"
            )

        if not provider.enabled:
            raise ValueError(
                f"Provider disabled: {llm_cfg.provider_id}"
            )

        # Get API key using provider adapter if available, otherwise use environment
        api_key = None
        if provider.auth and provider.auth.env_var:
            if self.provider_adapter:
                api_key = self.provider_adapter.get_credentials(
                    llm_cfg.provider_id, provider.auth.env_var
                )
            else:
                import os
                api_key = os.getenv(provider.auth.env_var)
            
            if not api_key:
                logger.warning(
                    "API key not found",
                    provider_id=llm_cfg.provider_id,
                    env_var=provider.auth.env_var,
                )

        # Build config_list entry
        config_entry = {
            "model": llm_cfg.model,
        }

        if api_key:
            config_entry["api_key"] = api_key

        if provider.base_url:
            config_entry["base_url"] = provider.base_url

        # Build full llm_config
        llm_config_dict: dict[str, Any] = {
            "config_list": [config_entry],
            "temperature": llm_cfg.temperature,
            "timeout": llm_cfg.timeout,
        }

        if llm_cfg.max_tokens is not None:
            llm_config_dict["max_tokens"] = llm_cfg.max_tokens

        if llm_cfg.cache_seed is not None:
            llm_config_dict["cache_seed"] = llm_cfg.cache_seed

        logger.debug(
            "Built llm_config",
            agent_id=agent_config.id,
            provider_id=llm_cfg.provider_id,
            model=llm_cfg.model,
        )

        return llm_config_dict
