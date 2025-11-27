"""Unit tests for agents."""

import pytest

from src.audit_logging import AuditLogger
from src.memory import AgentType, ConversationState, MessageRole
from src.agents import ReasoningAgent, KnowledgeAgent


@pytest.fixture
def audit_logger() -> AuditLogger:
    """Create an audit logger for testing."""
    return AuditLogger()


@pytest.fixture
def conversation_state() -> ConversationState:
    """Create a conversation state for testing."""
    state = ConversationState()
    state.add_message(MessageRole.USER, "What is Python?")
    return state


@pytest.mark.asyncio
async def test_reasoning_agent_process(
    audit_logger: AuditLogger, conversation_state: ConversationState
) -> None:
    """Test reasoning agent processing."""
    agent = ReasoningAgent(audit_logger)
    result = await agent.process(conversation_state)

    assert "intent" in result
    assert "plan" in result
    assert "requires_knowledge" in result
    assert result["intent"] == "information_request"


@pytest.mark.asyncio
async def test_reasoning_agent_greeting(
    audit_logger: AuditLogger
) -> None:
    """Test reasoning agent detects greeting intent."""
    state = ConversationState()
    state.add_message(MessageRole.USER, "Hello!")

    agent = ReasoningAgent(audit_logger)
    result = await agent.process(state)

    assert result["intent"] == "greeting"
    assert result["requires_knowledge"] is False


@pytest.mark.asyncio
async def test_knowledge_agent_process(
    audit_logger: AuditLogger, conversation_state: ConversationState
) -> None:
    """Test knowledge agent processing."""
    # First run reasoning agent to set context
    reasoning_agent = ReasoningAgent(audit_logger)
    reasoning_result = await reasoning_agent.process(conversation_state)

    # Then run knowledge agent
    knowledge_agent = KnowledgeAgent(audit_logger)
    result = await knowledge_agent.process(conversation_state, context=reasoning_result)

    assert "knowledge" in result
    assert "sources" in result
    assert result["knowledge"] is not None


@pytest.mark.asyncio
async def test_knowledge_agent_skip_when_not_needed(
    audit_logger: AuditLogger
) -> None:
    """Test knowledge agent skips when not needed."""
    state = ConversationState()
    state.add_message(MessageRole.USER, "Hello!")

    agent = KnowledgeAgent(audit_logger)
    result = await agent.process(state, context={"requires_knowledge": False})

    assert result["skipped"] is True
    assert result["knowledge"] is None


@pytest.mark.asyncio
async def test_agent_notes_added_to_state(
    audit_logger: AuditLogger, conversation_state: ConversationState
) -> None:
    """Test that agents add notes to conversation state."""
    agent = ReasoningAgent(audit_logger)
    await agent.process(conversation_state)

    reasoning_notes = conversation_state.get_notes_by_agent(AgentType.REASONING)
    assert len(reasoning_notes) >= 2  # Should have intent and plan notes

    intent_note = next(n for n in reasoning_notes if n.note_type == "intent")
    assert intent_note.content == "information_request"
