"""Unit tests for AgentFactory (CrewAI-backed)."""

import pytest

from src.config.agent_models import AgentConfig, AgentType, HumanInputMode
from src.factory.agent_factory import AgentFactory


@pytest.fixture
def agent_factory() -> AgentFactory:
    """Create an agent factory for testing."""
    return AgentFactory()


def _make_config(**overrides) -> AgentConfig:
    base = {
        "id": "test_agent",
        "type": AgentType.CONVERSABLE,
        "name": "TestAgent",
        "description": "A test agent for unit testing",
        "system_message": "You are a test agent.",
        "human_input_mode": HumanInputMode.NEVER,
        "tools": [],
    }
    base.update(overrides)
    return AgentConfig(**base)


def test_create_agent_from_config(agent_factory: AgentFactory) -> None:
    """A CrewAI agent is created with role/goal/backstory mapped from config."""
    config = _make_config()

    agent = agent_factory.create_agent_from_config(config)

    assert agent is not None
    assert agent.role == "TestAgent"
    assert agent.goal == "A test agent for unit testing"
    assert agent.backstory == "You are a test agent."


def test_create_agent_defaults_backstory(agent_factory: AgentFactory) -> None:
    """Agents without a system message get a sensible default backstory."""
    config = _make_config(system_message=None, description=None)

    agent = agent_factory.create_agent_from_config(config)

    assert agent.backstory  # non-empty default
    assert agent.goal  # non-empty default


def test_selector_agents_allow_delegation(agent_factory: AgentFactory) -> None:
    """Selector agents delegate to specialists; normal agents do not."""
    selector = agent_factory.create_agent_from_config(_make_config(is_selector=True))
    worker = agent_factory.create_agent_from_config(_make_config(id="worker", name="Worker"))

    assert selector.allow_delegation is True
    assert worker.allow_delegation is False


def test_agent_config_validation() -> None:
    """retrieve_user_proxy agents require retrieve_config or memory_config."""
    config = _make_config(type=AgentType.RETRIEVE_USER_PROXY)

    with pytest.raises(ValueError, match="required"):
        config.validate_config()
