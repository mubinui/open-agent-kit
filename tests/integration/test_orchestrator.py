"""Integration test for the full agent pipeline."""

import pytest

from src.agents import Orchestrator
from src.audit_logging import AuditLogger
from src.memory import InMemoryConversationStore


@pytest.mark.asyncio
async def test_full_conversation_flow() -> None:
    """Test a complete conversation flow through all agents."""
    store = InMemoryConversationStore()
    audit_logger = AuditLogger()
    orchestrator = Orchestrator(store, audit_logger)

    try:
        # Create session
        state = await orchestrator.create_session()
        session_id = state.session_id

        # Process first message
        result1 = await orchestrator.process_message(
            session_id,
            "What is artificial intelligence?"
        )

        assert "response" in result1
        assert result1["turn"] == 1
        assert result1.get("safety_passed", True) is True

        # Process second message
        result2 = await orchestrator.process_message(
            session_id,
            "Can you explain more?"
        )

        assert "response" in result2
        assert result2["turn"] == 2

        # Check history
        history = await orchestrator.get_session_history(session_id)
        assert len(history["messages"]) == 4  # 2 user + 2 assistant messages

    finally:
        await orchestrator.cleanup()


@pytest.mark.asyncio
async def test_session_turn_limit() -> None:
    """Test that sessions respect max turn limit."""
    store = InMemoryConversationStore()
    audit_logger = AuditLogger()
    orchestrator = Orchestrator(store, audit_logger)

    # Temporarily set a low limit for testing
    original_limit = orchestrator.settings.app.max_conversation_turns
    orchestrator.settings.app.max_conversation_turns = 2

    try:
        state = await orchestrator.create_session()
        session_id = state.session_id

        # First message (turn 1)
        result1 = await orchestrator.process_message(session_id, "Hello")
        assert "response" in result1

        # Second message (turn 2)
        result2 = await orchestrator.process_message(session_id, "How are you?")
        assert "response" in result2

        # Third message (should hit limit at turn 3)
        result3 = await orchestrator.process_message(session_id, "Tell me more")
        assert result3.get("session_ended") is True

    finally:
        orchestrator.settings.app.max_conversation_turns = original_limit
        await orchestrator.cleanup()


@pytest.mark.asyncio
async def test_multiple_sessions() -> None:
    """Test handling multiple concurrent sessions."""
    store = InMemoryConversationStore()
    audit_logger = AuditLogger()
    orchestrator = Orchestrator(store, audit_logger)

    try:
        # Create two sessions
        state1 = await orchestrator.create_session()
        state2 = await orchestrator.create_session()

        # Process messages in different sessions
        result1 = await orchestrator.process_message(state1.session_id, "Hi from session 1")
        result2 = await orchestrator.process_message(state2.session_id, "Hi from session 2")

        assert result1["session_id"] == str(state1.session_id)
        assert result2["session_id"] == str(state2.session_id)

        # Verify session histories are separate
        history1 = await orchestrator.get_session_history(state1.session_id)
        history2 = await orchestrator.get_session_history(state2.session_id)

        assert len(history1["messages"]) == 2
        assert len(history2["messages"]) == 2
        assert history1["messages"][0]["content"] != history2["messages"][0]["content"]

    finally:
        await orchestrator.cleanup()
