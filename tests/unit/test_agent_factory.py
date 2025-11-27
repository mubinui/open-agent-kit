"""Unit tests for AgentFactory."""

import pytest
from unittest.mock import Mock

from src.config.agent_models import (
    AgentConfig,
    AgentType,
    HumanInputMode,
    LLMConfig,
    RetrieveConfig,
)
from src.config.dynamic_models import (
    AuthConfig,
    AuthScheme,
    ModelConfig,
    ProviderConfig,
    ProviderType,
)
from src.config.registries import PromptRegistry, ProviderRegistry
from src.factory.agent_factory import AgentFactory


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    """Create a provider registry with test providers."""
    registry = ProviderRegistry()
    
    # Add OpenRouter provider
    provider = ProviderConfig(
        id="openrouter",
        name="OpenRouter",
        type=ProviderType.LLM,
        description="Test LLM provider",
        base_url="https://openrouter.ai/api/v1",
        auth=AuthConfig(
            scheme=AuthScheme.BEARER,
            env_var="OPENROUTER_API_KEY",
        ),
        models=[
            ModelConfig(
                name="openai/gpt-4",
                default=True,
                capabilities=[],
                temperature=0.7,
                max_tokens=1000,
            )
        ],
        enabled=True,
    )
    registry.register(provider)
    
    return registry


@pytest.fixture
def prompt_registry() -> PromptRegistry:
    """Create a prompt registry for testing."""
    return PromptRegistry()


@pytest.fixture
def agent_factory(
    provider_registry: ProviderRegistry,
    prompt_registry: PromptRegistry,
) -> AgentFactory:
    """Create an agent factory for testing."""
    return AgentFactory(
        provider_registry=provider_registry,
        prompt_registry=prompt_registry,
        tool_registry=None,
    )


def test_create_conversable_agent(agent_factory: AgentFactory) -> None:
    """Test creating a ConversableAgent from configuration."""
    config = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="TestAgent",
        system_message="You are a test agent.",
        llm_config=LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-4",
            temperature=0.7,
            max_tokens=500,
            cache_seed=42,
            timeout=120,
        ),
        human_input_mode=HumanInputMode.NEVER,
        code_execution_config=False,
        tools=[],
        max_consecutive_auto_reply=10,
    )
    
    agent = agent_factory.create_agent(config)
    
    assert agent is not None
    assert agent.name == "TestAgent"
    assert agent.system_message == "You are a test agent."
    assert agent.human_input_mode == "NEVER"


def test_create_agent_without_llm_config(agent_factory: AgentFactory) -> None:
    """Test creating an agent without LLM config raises error."""
    config = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="TestAgent",
        system_message="You are a test agent.",
        llm_config=None,  # Missing required llm_config
        human_input_mode=HumanInputMode.NEVER,
    )
    
    with pytest.raises(ValueError, match="conversable agents require llm_config"):
        agent_factory.create_agent(config)


def test_build_llm_config(agent_factory: AgentFactory) -> None:
    """Test building llm_config from agent configuration."""
    config = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="TestAgent",
        llm_config=LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-4",
            temperature=0.8,
            max_tokens=1000,
            cache_seed=42,
            timeout=120,
        ),
    )
    
    llm_config = agent_factory._build_llm_config(config)
    
    assert isinstance(llm_config, dict)
    assert "config_list" in llm_config
    assert len(llm_config["config_list"]) == 1
    assert llm_config["config_list"][0]["model"] == "openai/gpt-4"
    assert llm_config["config_list"][0]["base_url"] == "https://openrouter.ai/api/v1"
    assert llm_config["temperature"] == 0.8
    assert llm_config["max_tokens"] == 1000
    assert llm_config["cache_seed"] == 42
    assert llm_config["timeout"] == 120


def test_build_llm_config_with_invalid_provider(agent_factory: AgentFactory) -> None:
    """Test building llm_config with invalid provider raises error."""
    config = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="TestAgent",
        llm_config=LLMConfig(
            provider_id="invalid_provider",
            model="openai/gpt-4",
        ),
    )
    
    with pytest.raises(ValueError, match="Provider not found"):
        agent_factory._build_llm_config(config)


def test_agent_config_validation() -> None:
    """Test agent configuration validation."""
    # Valid conversable agent
    config = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="TestAgent",
        llm_config=LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-4",
        ),
    )
    config.validate_config()  # Should not raise
    
    # Invalid conversable agent (missing llm_config)
    config_invalid = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="TestAgent",
        llm_config=None,
    )
    with pytest.raises(ValueError, match="conversable agents require llm_config"):
        config_invalid.validate_config()


def test_retrieve_agent_config_validation() -> None:
    """Test retrieve agent configuration validation."""
    # Valid retrieve agent
    config = AgentConfig(
        id="knowledge_agent",
        type=AgentType.RETRIEVE_USER_PROXY,
        name="KnowledgeAgent",
        retrieve_config=RetrieveConfig(
            task="qa",
            docs_path=["./docs"],
            collection_name="test_collection",
        ),
    )
    config.validate_config()  # Should not raise
    
    # Invalid retrieve agent (missing retrieve_config)
    config_invalid = AgentConfig(
        id="knowledge_agent",
        type=AgentType.RETRIEVE_USER_PROXY,
        name="KnowledgeAgent",
        retrieve_config=None,
    )
    with pytest.raises(ValueError, match="retrieve_user_proxy agents require retrieve_config"):
        config_invalid.validate_config()


def test_llm_config_temperature_validation() -> None:
    """Test LLM config temperature validation."""
    # Valid temperature
    config = LLMConfig(
        provider_id="openrouter",
        model="openai/gpt-4",
        temperature=0.7,
    )
    assert config.temperature == 0.7
    
    # Invalid temperature (too high)
    with pytest.raises(ValueError):
        LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-4",
            temperature=3.0,
        )
    
    # Invalid temperature (negative)
    with pytest.raises(ValueError):
        LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-4",
            temperature=-0.5,
        )
