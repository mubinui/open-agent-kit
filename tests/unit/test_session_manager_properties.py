"""
Property-based tests for SessionManager context sanitization.

**Feature: context-leak-fix**

These tests validate the correctness properties for response sanitization
and message storage as specified in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4

from src.api.session_manager import SessionManager
from src.memory.models import ConversationState, Message, MessageRole
from src.memory.inmemory import InMemoryConversationStore


# Strategies for generating test data

@st.composite
def response_with_wrappers(draw):
    """Generate a response that may contain context wrappers."""
    actual_response = draw(st.text(min_size=10, max_size=200))
    
    # Sometimes add wrappers
    add_wrapper = draw(st.booleans())
    
    if add_wrapper:
        wrapper_style = draw(st.sampled_from([
            "previous_current",
            "recent_route",
            "mixed",
        ]))
        
        if wrapper_style == "previous_current":
            fake_context = draw(st.text(min_size=10, max_size=100))
            return f"[Previous conversation context]\n{fake_context}\n[Current message]\n{actual_response}"
        elif wrapper_style == "recent_route":
            fake_context = draw(st.text(min_size=10, max_size=100))
            return f"[Recent conversation for context]\n{fake_context}\n[Current user message to route]\n{actual_response}"
        else:  # mixed
            return f"[Previous conversation context]\nSome context\n{actual_response}"
    
    return actual_response


@st.composite
def conversation_state_with_messages(draw):
    """Generate a ConversationState with message history."""
    session_id = uuid4()
    num_messages = draw(st.integers(min_value=0, max_value=10))
    
    state = ConversationState(session_id=session_id)
    
    for _ in range(num_messages):
        role = draw(st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]))
        content = draw(st.text(min_size=1, max_size=200))
        
        # Sometimes add wrappers to existing messages
        if draw(st.booleans()):
            content = f"[Previous conversation context]\nContext\n[Current message]\n{content}"
        
        state.add_message(role, content)
    
    return state


# Property 2: Response Sanitization
# **Validates: Requirements 1.1, 1.4**

@given(
    response=response_with_wrappers(),
)
@settings(max_examples=100, deadline=None)
def test_property_2_response_sanitization(response):
    """
    **Feature: context-leak-fix, Property 2: Response Sanitization**
    **Validates: Requirements 1.1, 1.4**
    
    Property: For any response returned to the user through process_message(),
    the response should not contain any context wrapper markers like
    "[Previous conversation context]" or "[Current message]".
    
    This test verifies that:
    1. _sanitize_response() removes all wrapper markers
    2. The sanitized response is suitable for user display
    3. The function handles edge cases gracefully
    """
    # Create a SessionManager instance
    session_manager = SessionManager()
    
    # Sanitize the response
    sanitized = session_manager._sanitize_response(response)
    
    # Property: Sanitized response should not contain wrapper markers
    wrapper_markers = [
        "[Previous conversation context]",
        "[Current message]",
        "[Recent conversation for context]",
        "[Current user message to route]",
    ]
    
    for marker in wrapper_markers:
        assert marker.lower() not in sanitized.lower(), \
            f"Sanitized response should not contain wrapper marker: {marker}"
    
    # Property: Sanitized response should be non-empty if original was non-empty
    if response.strip():
        assert sanitized.strip(), \
            "Sanitized response should be non-empty if original was non-empty"
    
    # Property: Sanitizing twice should produce same result (idempotent)
    sanitized_twice = session_manager._sanitize_response(sanitized)
    assert sanitized == sanitized_twice, \
        "_sanitize_response should be idempotent"


# Property 3: Message Storage Cleanliness
# **Validates: Requirements 1.3, 3.2**

@given(
    response=response_with_wrappers(),
)
@settings(max_examples=100, deadline=None)
def test_property_3_message_storage_cleanliness(response):
    """
    **Feature: context-leak-fix, Property 3: Message Storage Cleanliness**
    **Validates: Requirements 1.3, 3.2**
    
    Property: For any message stored in session state, the message content
    should not contain context wrapper markers.
    
    This test verifies that:
    1. Messages stored via _sanitize_response() are clean
    2. No wrapper markers leak into storage
    3. The stored content is suitable for retrieval
    """
    # Create a SessionManager instance
    session_manager = SessionManager()
    
    # Sanitize the response (simulating what happens before storage)
    sanitized = session_manager._sanitize_response(response)
    
    # Create a mock session and store the message
    session = ConversationState(session_id=uuid4())
    session.add_message(MessageRole.ASSISTANT, sanitized)
    
    # Property: Stored message should not contain wrapper markers
    stored_message = session.messages[-1]
    
    wrapper_markers = [
        "[Previous conversation context]",
        "[Current message]",
        "[Recent conversation for context]",
        "[Current user message to route]",
    ]
    
    for marker in wrapper_markers:
        assert marker.lower() not in stored_message.content.lower(), \
            f"Stored message should not contain wrapper marker: {marker}"
    
    # Property: Stored content should match sanitized content
    assert stored_message.content == sanitized, \
        "Stored message content should match sanitized response"


# Property 7: Nested Wrapper Prevention
# **Validates: Requirements 1.2, 3.5**

@given(
    current_message=st.text(min_size=1, max_size=100),
    session_state=conversation_state_with_messages(),
)
@settings(max_examples=100, deadline=None)
def test_property_7_nested_wrapper_prevention(current_message, session_state):
    """
    **Feature: context-leak-fix, Property 7: Nested Wrapper Prevention**
    **Validates: Requirements 1.2, 3.5**
    
    Property: For any message that already contains context wrappers,
    building context with that message should not create nested wrappers
    (wrappers within wrappers).
    
    This test verifies that:
    1. _build_context_message() doesn't create nested wrappers
    2. Existing wrappers are stripped before adding new context
    3. The resulting message has at most one level of wrappers
    """
    # Create a SessionManager instance
    session_manager = SessionManager()
    
    # Build context message
    context_message = session_manager._build_context_message(
        current_message=current_message,
        session=session_state,
        context_type="general",
        max_exchanges=5
    )
    
    # Property: Should not have nested wrappers
    # Count occurrences of wrapper markers
    wrapper_markers = [
        "[Previous conversation context]",
        "[Current message]",
        "[Recent conversation for context]",
        "[Current user message to route]",
    ]
    
    for marker in wrapper_markers:
        # Count how many times this marker appears
        count = context_message.lower().count(marker.lower())
        
        # Should appear at most once (for the outer wrapper)
        assert count <= 1, \
            f"Wrapper marker '{marker}' should appear at most once, found {count} times"
    
    # Property: If context was added, it should be properly formatted
    if "[Previous conversation context]" in context_message or "[Recent conversation for context]" in context_message:
        # Should have both opening and closing markers
        if "[Previous conversation context]" in context_message:
            assert "[Current message]" in context_message, \
                "If context wrapper is present, current message marker should also be present"
        
        if "[Recent conversation for context]" in context_message:
            assert "[Current user message to route]" in context_message, \
                "If recent context wrapper is present, route marker should also be present"
    
    # Property: The current message should appear in the result
    # (either wrapped or as-is if no history)
    assert current_message in context_message or len(session_state.messages) == 0, \
        "Current message should appear in the context message"


# Additional test: Context type handling

@given(
    current_message=st.text(min_size=1, max_size=100),
    context_type=st.sampled_from(["general", "selector", "domain"]),
)
@settings(max_examples=50, deadline=None)
def test_context_type_handling(current_message, context_type):
    """
    Test that _build_context_message handles different context types correctly.
    """
    # Create a SessionManager instance
    session_manager = SessionManager()
    
    # Create a session with some history
    session = ConversationState(session_id=uuid4())
    session.add_message(MessageRole.USER, "Previous user message")
    session.add_message(MessageRole.ASSISTANT, "Previous assistant response")
    
    # Build context message
    context_message = session_manager._build_context_message(
        current_message=current_message,
        session=session,
        context_type=context_type,
        max_exchanges=5
    )
    
    # Property: Result should be a string
    assert isinstance(context_message, str), \
        "Context message should be a string"
    
    # Property: Current message should be included
    assert current_message in context_message, \
        "Current message should be included in context message"
    
    # Property: For selector type, should use selector-specific markers
    if context_type == "selector":
        if len(session.messages) > 1:  # If there's history to add
            assert "[Recent conversation for context]" in context_message or \
                   context_message == current_message, \
                "Selector context should use selector-specific markers or return message as-is"
    
    # Property: For general/domain types, should use general markers
    if context_type in ["general", "domain"]:
        if len(session.messages) > 1:  # If there's history to add
            assert "[Previous conversation context]" in context_message or \
                   context_message == current_message, \
                "General/domain context should use general markers or return message as-is"


# Edge case test: Empty session

def test_empty_session_handling():
    """
    Test that _build_context_message handles empty sessions correctly.
    """
    session_manager = SessionManager()
    
    # Test with None session
    result = session_manager._build_context_message(
        current_message="Test message",
        session=None,
        context_type="general",
        max_exchanges=5
    )
    
    assert result == "Test message", \
        "Should return message as-is when session is None"
    
    # Test with empty session
    empty_session = ConversationState(session_id=uuid4())
    result = session_manager._build_context_message(
        current_message="Test message",
        session=empty_session,
        context_type="general",
        max_exchanges=5
    )
    
    assert result == "Test message", \
        "Should return message as-is when session has no messages"


# Edge case test: Sanitize edge cases

@given(
    response=st.one_of(
        st.just(""),
        st.just("   "),
        st.just("\n\n"),
        st.just(None),
    ),
)
@settings(max_examples=20, deadline=None)
def test_sanitize_edge_cases(response):
    """
    Test that _sanitize_response handles edge cases gracefully.
    """
    session_manager = SessionManager()
    
    # Should not crash on edge cases
    try:
        result = session_manager._sanitize_response(response)
        
        # Result should be the same as input for these edge cases
        assert result == response, \
            "Edge case inputs should be returned as-is"
        
    except Exception as e:
        pytest.fail(f"_sanitize_response should handle edge cases without crashing: {e}")
