"""Unit tests for ConversationPatternEngine."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from autogen.agentchat import ConversableAgent, ChatResult

from src.patterns import ConversationPattern, ConversationPatternEngine


@pytest.fixture
def pattern_engine() -> ConversationPatternEngine:
    """Create a conversation pattern engine for testing."""
    return ConversationPatternEngine()


@pytest.fixture
def mock_agent() -> ConversableAgent:
    """Create a mock ConversableAgent for testing."""
    agent = Mock(spec=ConversableAgent)
    agent.name = "TestAgent"
    agent.llm_config = {"model": "gpt-4", "temperature": 0.7}
    return agent


@pytest.fixture
def mock_chat_result() -> ChatResult:
    """Create a mock ChatResult for testing."""
    result = Mock(spec=ChatResult)
    result.chat_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    result.summary = "Greeting exchange"
    result.cost = {"total_cost": 0.001}
    return result


def test_conversation_pattern_enum() -> None:
    """Test ConversationPattern enum values."""
    assert ConversationPattern.TWO_AGENT == "two_agent"
    assert ConversationPattern.SEQUENTIAL == "sequential"
    assert ConversationPattern.GROUP_CHAT == "group_chat"
    assert ConversationPattern.NESTED == "nested"


def test_pattern_engine_initialization(pattern_engine: ConversationPatternEngine) -> None:
    """Test ConversationPatternEngine initialization."""
    assert pattern_engine is not None
    assert isinstance(pattern_engine, ConversationPatternEngine)


def test_execute_two_agent_chat(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
    mock_chat_result: ChatResult,
) -> None:
    """Test two-agent chat execution."""
    sender = mock_agent
    recipient = Mock(spec=ConversableAgent)
    recipient.name = "RecipientAgent"
    
    # Mock initiate_chat to return our mock result
    sender.initiate_chat = MagicMock(return_value=mock_chat_result)
    
    # Execute two-agent chat
    result = pattern_engine.execute_two_agent_chat(
        sender=sender,
        recipient=recipient,
        message="Hello, how are you?",
        max_turns=5,
    )
    
    # Verify initiate_chat was called with correct arguments
    sender.initiate_chat.assert_called_once()
    call_kwargs = sender.initiate_chat.call_args.kwargs
    assert call_kwargs["recipient"] == recipient
    assert call_kwargs["message"] == "Hello, how are you?"
    assert call_kwargs["max_turns"] == 5
    assert call_kwargs["summary_method"] == "last_msg"
    
    # Verify result
    assert result == mock_chat_result


def test_execute_two_agent_chat_with_custom_summary(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
    mock_chat_result: ChatResult,
) -> None:
    """Test two-agent chat with custom summary method."""
    sender = mock_agent
    recipient = Mock(spec=ConversableAgent)
    
    sender.initiate_chat = MagicMock(return_value=mock_chat_result)
    
    result = pattern_engine.execute_two_agent_chat(
        sender=sender,
        recipient=recipient,
        message="Test message",
        summary_method="reflection_with_llm",
    )
    
    call_kwargs = sender.initiate_chat.call_args.kwargs
    assert call_kwargs["summary_method"] == "reflection_with_llm"


def test_execute_sequential_chat(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
    mock_chat_result: ChatResult,
) -> None:
    """Test sequential chat execution."""
    sender = mock_agent
    recipient1 = Mock(spec=ConversableAgent)
    recipient1.name = "Agent1"
    recipient2 = Mock(spec=ConversableAgent)
    recipient2.name = "Agent2"
    
    # Mock initiate_chats to return list of results
    mock_results = [mock_chat_result, mock_chat_result]
    sender.initiate_chats = MagicMock(return_value=mock_results)
    
    # Define chat sequence
    chat_sequence = [
        {
            "recipient": recipient1,
            "message": "First chat",
            "max_turns": 3,
            "summary_method": "last_msg",
        },
        {
            "recipient": recipient2,
            "message": "Second chat",
            "max_turns": 2,
            "summary_method": "reflection_with_llm",
        },
    ]
    
    # Execute sequential chat
    results = pattern_engine.execute_sequential_chat(
        sender=sender,
        chat_sequence=chat_sequence,
    )
    
    # Verify initiate_chats was called
    sender.initiate_chats.assert_called_once_with(chat_sequence)
    
    # Verify results
    assert len(results) == 2
    assert results == mock_results


def test_execute_group_chat(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
    mock_chat_result: ChatResult,
) -> None:
    """Test group chat execution."""
    agent1 = mock_agent
    agent2 = Mock(spec=ConversableAgent)
    agent2.name = "Agent2"
    agent2.llm_config = {"model": "gpt-4"}
    agent3 = Mock(spec=ConversableAgent)
    agent3.name = "Agent3"
    agent3.llm_config = None
    
    agents = [agent1, agent2, agent3]
    
    # Mock initiate_chat on first agent
    agent1.initiate_chat = MagicMock(return_value=mock_chat_result)
    
    # Execute group chat with manager_llm_config=False to avoid OpenAI client creation
    result = pattern_engine.execute_group_chat(
        agents=agents,
        initial_message="Let's discuss this topic",
        max_round=10,
        speaker_selection_method="auto",
        manager_llm_config=False,
    )
    
    # Verify initiate_chat was called
    agent1.initiate_chat.assert_called_once()
    call_kwargs = agent1.initiate_chat.call_args.kwargs
    assert call_kwargs["message"] == "Let's discuss this topic"
    
    # Verify result
    assert result == mock_chat_result


def test_execute_group_chat_with_round_robin(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
    mock_chat_result: ChatResult,
) -> None:
    """Test group chat with round_robin speaker selection."""
    agent1 = mock_agent
    agent2 = Mock(spec=ConversableAgent)
    agent2.name = "Agent2"
    agent2.llm_config = {"model": "gpt-4"}
    
    agents = [agent1, agent2]
    agent1.initiate_chat = MagicMock(return_value=mock_chat_result)
    
    result = pattern_engine.execute_group_chat(
        agents=agents,
        initial_message="Test",
        speaker_selection_method="round_robin",
        max_round=5,
        manager_llm_config=False,
    )
    
    assert result == mock_chat_result


def test_execute_group_chat_with_allowed_transitions(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
    mock_chat_result: ChatResult,
) -> None:
    """Test group chat with allowed transitions."""
    agent1 = mock_agent
    agent2 = Mock(spec=ConversableAgent)
    agent2.name = "Agent2"
    agent2.llm_config = {"model": "gpt-4"}
    
    agents = [agent1, agent2]
    agent1.initiate_chat = MagicMock(return_value=mock_chat_result)
    
    # Define allowed transitions
    allowed_transitions = {
        agent1: [agent2],
        agent2: [agent1],
    }
    
    result = pattern_engine.execute_group_chat(
        agents=agents,
        initial_message="Test",
        allowed_transitions=allowed_transitions,
        speaker_transitions_type="allowed",
        manager_llm_config=False,
    )
    
    assert result == mock_chat_result


def test_execute_group_chat_empty_agents_raises_error(
    pattern_engine: ConversationPatternEngine,
) -> None:
    """Test that group chat with empty agents list raises error."""
    with pytest.raises(ValueError, match="At least one agent is required"):
        pattern_engine.execute_group_chat(
            agents=[],
            initial_message="Test",
        )


def test_register_nested_chat(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
) -> None:
    """Test nested chat registration."""
    trigger_agent = mock_agent
    recipient = Mock(spec=ConversableAgent)
    recipient.name = "NestedAgent"
    
    # Mock register_nested_chats
    trigger_agent.register_nested_chats = MagicMock()
    
    # Define nested chats
    nested_chats = [
        {
            "recipient": recipient,
            "message": "Nested chat message",
            "max_turns": 2,
        }
    ]
    
    # Register nested chat
    pattern_engine.register_nested_chat(
        trigger_agent=trigger_agent,
        nested_chats=nested_chats,
        trigger="keyword",
        position=2,
    )
    
    # Verify register_nested_chats was called
    trigger_agent.register_nested_chats.assert_called_once()
    call_kwargs = trigger_agent.register_nested_chats.call_args.kwargs
    assert call_kwargs["trigger"] == "keyword"
    assert call_kwargs["chat_queue"] == nested_chats
    assert call_kwargs["position"] == 2


def test_register_nested_chat_with_callable_trigger(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
) -> None:
    """Test nested chat registration with callable trigger."""
    trigger_agent = mock_agent
    recipient = Mock(spec=ConversableAgent)
    
    trigger_agent.register_nested_chats = MagicMock()
    
    # Define trigger function
    def custom_trigger(message: str) -> bool:
        return "urgent" in message.lower()
    
    nested_chats = [
        {
            "recipient": recipient,
            "message": "Handle urgent request",
        }
    ]
    
    # Register with callable trigger
    pattern_engine.register_nested_chat(
        trigger_agent=trigger_agent,
        nested_chats=nested_chats,
        trigger=custom_trigger,
    )
    
    # Verify registration
    trigger_agent.register_nested_chats.assert_called_once()
    call_kwargs = trigger_agent.register_nested_chats.call_args.kwargs
    assert callable(call_kwargs["trigger"])


def test_register_nested_chat_no_trigger(
    pattern_engine: ConversationPatternEngine,
    mock_agent: ConversableAgent,
) -> None:
    """Test nested chat registration without trigger (always trigger)."""
    trigger_agent = mock_agent
    recipient = Mock(spec=ConversableAgent)
    
    trigger_agent.register_nested_chats = MagicMock()
    
    nested_chats = [
        {
            "recipient": recipient,
            "message": "Always execute",
        }
    ]
    
    # Register without trigger
    pattern_engine.register_nested_chat(
        trigger_agent=trigger_agent,
        nested_chats=nested_chats,
    )
    
    # Verify registration
    trigger_agent.register_nested_chats.assert_called_once()
    call_kwargs = trigger_agent.register_nested_chats.call_args.kwargs
    assert call_kwargs["trigger"] is None
