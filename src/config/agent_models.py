"""Pydantic models for agent configuration validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.config.behavior_models import AgentBehaviorConfig


class AgentType(str, Enum):
    """Type of agent."""

    CONVERSABLE = "conversable"
    RETRIEVE_USER_PROXY = "retrieve_user_proxy"
    GROUP_CHAT_MANAGER = "group_chat_manager"


class HumanInputMode(str, Enum):
    """Human input mode for agents."""

    ALWAYS = "ALWAYS"
    NEVER = "NEVER"
    TERMINATE = "TERMINATE"


class LLMConfig(BaseModel):
    """LLM configuration for an agent."""

    provider_id: str = Field(description="ID of the LLM provider from provider registry")
    model: str = Field(description="Model name to use (e.g., 'openai/gpt-4')")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens in response")
    cache_seed: Optional[int] = Field(default=42, description="Seed for caching (None to disable)")
    timeout: int = Field(default=120, ge=1, description="Request timeout in seconds")


class RetrieveConfig(BaseModel):
    """Configuration for RetrieveUserProxyAgent."""

    task: str = Field(default="qa", description="Task type: 'qa', 'code', or 'default'")
    docs_path: list[str] = Field(description="List of document paths or URLs to index")
    chunk_token_size: int = Field(default=2000, ge=100, description="Token size for document chunks")
    vector_db: str = Field(default="chromadb", description="Vector database type")
    collection_name: str = Field(description="Name of the vector database collection")
    embedding_model: str = Field(
        default="all-mpnet-base-v2",
        description="Sentence transformer model for embeddings"
    )
    get_or_create: bool = Field(
        default=True,
        description="Whether to create collection if it doesn't exist"
    )
    db_config: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional database-specific configuration"
    )


class AgentConfig(BaseModel):
    """Configuration for creating an agent."""

    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Unique agent identifier")
    type: AgentType = Field(description="Type of agent to create")
    name: str = Field(description="Display name for the agent")
    system_message: Optional[str] = Field(
        default=None,
        description="System message defining agent behavior"
    )
    llm_config: Optional[LLMConfig | bool] = Field(
        default=None,
        description="LLM configuration, None for default, or False to disable LLM"
    )
    human_input_mode: HumanInputMode = Field(
        default=HumanInputMode.NEVER,
        description="When to request human input"
    )
    code_execution_config: Optional[dict[str, Any] | bool] = Field(
        default=False,
        description="Code execution configuration or False to disable"
    )
    tools: list[str] = Field(
        default_factory=list,
        description="List of tool IDs to register with this agent"
    )
    max_consecutive_auto_reply: int = Field(
        default=10,
        ge=0,
        description="Maximum consecutive auto-replies (0 means agent won't auto-reply)"
    )
    retrieve_config: Optional[RetrieveConfig] = Field(
        default=None,
        description="Retrieval configuration (required for retrieve_user_proxy agents)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Agent description for GroupChat speaker selection"
    )
    behavior: Optional[AgentBehaviorConfig] = Field(
        default=None,
        description="Behavior configuration for output format, constraints, and validation"
    )
    
    # Versioning and metadata fields
    version: int = Field(
        default=1,
        ge=1,
        description="Configuration version number"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last configuration update"
    )

    def validate_config(self) -> None:
        """Validate agent configuration based on type."""
        if self.type == AgentType.CONVERSABLE:
            if self.llm_config is None:
                raise ValueError(f"Agent {self.id}: conversable agents require llm_config")
        
        if self.type == AgentType.RETRIEVE_USER_PROXY:
            if self.retrieve_config is None:
                raise ValueError(f"Agent {self.id}: retrieve_user_proxy agents require retrieve_config")
        
        if self.type == AgentType.GROUP_CHAT_MANAGER:
            if self.llm_config is None:
                raise ValueError(f"Agent {self.id}: group_chat_manager agents require llm_config")


class AgentsConfig(BaseModel):
    """Root configuration for agents."""

    version: str = Field(description="Configuration version")
    agents: list[AgentConfig] = Field(description="List of agent configurations")

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration by ID."""
        return next((a for a in self.agents if a.id == agent_id), None)

    def validate_all(self) -> None:
        """Validate all agent configurations."""
        for agent in self.agents:
            agent.validate_config()
