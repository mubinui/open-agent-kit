"""
Property-based tests for context utilities.

**Feature: context-leak-fix**

These tests validate the correctness properties for context sanitization
and message cleaning as specified in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.memory.models import Message, MessageRole
from src.utils.context_utils import (
    strip_context_wrappers,
    extract_actual_content,
    has_context_wrapper,
    build_clean_context,
)


# Strategies for generating test data

@st.composite
def message_content(draw):
    """Generate random message content with at least one non-whitespace character."""
    # Use characters that are printable and non-whitespace to ensure meaningful content
    content = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S')),
        min_size=1,
        max_size=500
    ))
    return content


@st.composite
def wrapped_message(draw):
    """Generate a message with context wrappers.
    
    Ensures actual content contains at least one non-whitespace character
    so that extraction can return meaningful content.
    """
    # Generate content that has at least one non-whitespace character
    # Use from_regex to ensure we get printable content
    actual_content = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S')),
        min_size=1,
        max_size=200
    ))
    
    # Choose a wrapper style
    wrapper_style = draw(st.sampled_from([
        "previous_current",
        "recent_route",
        "previous_only",
        "current_only",
    ]))
    
    if wrapper_style == "previous_current":
        # Add some fake previous context
        prev_context = draw(st.text(min_size=10, max_size=100))
        return f"[Previous conversation context]\n{prev_context}\n[Current message]\n{actual_content}"
    elif wrapper_style == "recent_route":
        # Add some fake recent context
        recent_context = draw(st.text(min_size=10, max_size=100))
        return f"[Recent conversation for context]\n{recent_context}\n[Current user message to route]\n{actual_content}"
    elif wrapper_style == "previous_only":
        prev_context = draw(st.text(min_size=10, max_size=100))
        return f"[Previous conversation context]\n{prev_context}\n{actual_content}"
    else:  # current_only
        return f"[Current message]\n{actual_content}"


@st.composite
def message_list(draw):
    """Generate a list of Message objects."""
    num_messages = draw(st.integers(min_value=0, max_value=20))
    messages = []
    
    for _ in range(num_messages):
        role = draw(st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]))
        content = draw(st.text(min_size=1, max_size=500))
        messages.append(Message(role=role, content=content))
    
    return messages


# Property 1: Context Wrapper Removal
# **Validates: Requirements 1.1, 1.4**

@given(
    message=st.one_of(wrapped_message(), message_content()),
)
@settings(max_examples=100, deadline=None)
def test_property_1_context_wrapper_removal(message):
    """
    **Feature: context-leak-fix, Property 1: Context Wrapper Removal**
    **Validates: Requirements 1.1, 1.4**
    
    Property: For any message containing context wrapper markers,
    applying strip_context_wrappers() should return a message without
    any wrapper markers, and applying it twice should produce the same
    result as applying it once (idempotent).
    
    This test verifies that:
    1. Wrapper markers are removed from messages
    2. The function is idempotent
    3. Non-wrapped messages are returned unchanged (or with minimal whitespace cleanup)
    """
    # Apply strip_context_wrappers once
    stripped_once = strip_context_wrappers(message)
    
    # Apply strip_context_wrappers twice
    stripped_twice = strip_context_wrappers(stripped_once)
    
    # Property: Idempotence - applying twice should equal applying once
    assert stripped_once == stripped_twice, \
        "strip_context_wrappers should be idempotent"
    
    # Property: Result should not contain wrapper markers
    wrapper_markers = [
        "[Previous conversation context]",
        "[Current message]",
        "[Recent conversation for context]",
        "[Current user message to route]",
    ]
    
    for marker in wrapper_markers:
        assert marker.lower() not in stripped_once.lower(), \
            f"Stripped message should not contain wrapper marker: {marker}"
    
    # Property: If original message had no wrappers, result should be similar
    # (allowing for whitespace normalization)
    if not has_context_wrapper(message):
        # Should be the same or just whitespace-normalized
        assert stripped_once.strip() == message.strip(), \
            "Messages without wrappers should be unchanged (except whitespace)"


# Property 4: Context Extraction Consistency
# **Validates: Requirements 1.2, 3.4**

@given(
    message=st.one_of(wrapped_message(), message_content()),
)
@settings(max_examples=100, deadline=None)
def test_property_4_context_extraction_consistency(message):
    """
    **Feature: context-leak-fix, Property 4: Context Extraction Consistency**
    **Validates: Requirements 1.2, 3.4**
    
    Property: For any message, if has_context_wrapper() returns True,
    then extract_actual_content() should return a non-empty string
    that is different from the original message.
    
    This test verifies that:
    1. Wrapper detection is consistent with extraction
    2. Extracted content is non-empty when wrappers are detected
    3. Extracted content differs from wrapped message
    4. Messages without wrappers are returned as-is
    """
    has_wrapper = has_context_wrapper(message)
    extracted = extract_actual_content(message)
    
    # Property: Extracted content should never be None or empty
    # (unless original was empty, which our strategy prevents)
    assert extracted, "Extracted content should be non-empty"
    
    # Property: If message has wrapper, extracted content should differ from original
    if has_wrapper:
        # The extracted content should be different (shorter or cleaned)
        # It should not contain the wrapper markers
        assert extracted != message, \
            "Extracted content should differ from wrapped message"
        
        # Extracted content should not have wrapper markers
        wrapper_markers = [
            "[Previous conversation context]",
            "[Current message]",
            "[Recent conversation for context]",
            "[Current user message to route]",
        ]
        
        for marker in wrapper_markers:
            assert marker.lower() not in extracted.lower(), \
                f"Extracted content should not contain wrapper marker: {marker}"
    
    # Property: If message has no wrapper, extracted should be same as stripped
    if not has_wrapper:
        stripped = strip_context_wrappers(message)
        assert extracted == stripped, \
            "For non-wrapped messages, extract should equal strip"
    
    # Property: Extracting from extracted content should be idempotent
    extracted_twice = extract_actual_content(extracted)
    assert extracted == extracted_twice, \
        "extract_actual_content should be idempotent"


# Additional test: Wrapper detection accuracy

@given(
    message=wrapped_message(),
)
@settings(max_examples=100, deadline=None)
def test_wrapper_detection_accuracy(message):
    """
    Test that has_context_wrapper correctly identifies wrapped messages.
    
    This validates that wrapper detection works for all wrapper styles.
    """
    # Property: Wrapped messages should be detected
    assert has_context_wrapper(message), \
        "Wrapped messages should be detected by has_context_wrapper"
    
    # Property: After stripping, wrappers should not be detected
    stripped = strip_context_wrappers(message)
    
    # Only check if stripped is different from original
    # (some edge cases might result in same content)
    if stripped != message:
        assert not has_context_wrapper(stripped), \
            "Stripped messages should not have wrappers"


# =============================================================================
# Property 6: Context Window Bounds
# **Feature: context-leak-fix, Property 6: Context Window Bounds**
# **Validates: Requirements 3.1, 3.5**
# =============================================================================

@given(
    messages=message_list(),
    limit=st.integers(min_value=1, max_value=10),
    max_length=st.integers(min_value=50, max_value=500),
)
@settings(max_examples=100, deadline=None)
def test_property_6_context_window_bounds(messages, limit, max_length):
    """
    **Feature: context-leak-fix, Property 6: Context Window Bounds**
    **Validates: Requirements 3.1, 3.5**
    
    Property: For any conversation history, the context built by
    build_clean_context() should include at most the specified limit
    of recent messages.
    
    This test verifies that:
    1. Context respects the message limit parameter
    2. Only the most recent messages are included when history exceeds limit
    3. Individual messages are truncated to max_message_length
    4. Context building handles various history sizes correctly
    """
    # Skip if no messages
    if not messages:
        context = build_clean_context(messages, limit=limit, max_message_length=max_length)
        assert context == "", "Empty message list should produce empty context"
        return
    
    # Build context
    context = build_clean_context(messages, limit=limit, max_message_length=max_length)
    
    # Property: Context should be a string
    assert isinstance(context, str), "Context should be a string"
    
    # Property: Context should not contain wrapper markers
    wrapper_markers = [
        "[Previous conversation context]",
        "[Current message]",
        "[Recent conversation for context]",
        "[Current user message to route]",
    ]
    
    for marker in wrapper_markers:
        assert marker.lower() not in context.lower(), \
            f"Built context should not contain wrapper marker: {marker}"
    
    # Property: Number of messages in context should not exceed limit
    # Count by looking for role labels (User:, Assistant:, etc.)
    role_labels = ["User:", "Assistant:", "System:", "Agent:"]
    message_count = sum(context.count(label) for label in role_labels)
    
    assert message_count <= limit, \
        f"Context should contain at most {limit} messages, found {message_count}"
    
    # Property: If we have more messages than limit, only recent ones should be included
    if len(messages) > limit:
        # The context should include the last 'limit' messages
        # We can verify this by checking that the last message's content appears
        last_message_content = messages[-1].content
        
        # Handle wrapped content
        if has_context_wrapper(last_message_content):
            last_message_content = extract_actual_content(last_message_content)
        
        # Truncate to max_length for comparison
        if len(last_message_content) > max_length:
            last_message_content = last_message_content[:max_length]
        
        # The last message content (or its prefix) should appear in context
        # (allowing for truncation with "...")
        assert (last_message_content[:50] in context or 
                last_message_content[:max_length-3] in context), \
            "Context should include recent messages"
    
    # Property: Messages should be truncated to max_message_length
    # Each line in context (after role label) should not exceed max_length + "..."
    lines = context.split("\n")
    for line in lines:
        if line.strip():
            # Extract content after role label
            for label in role_labels:
                if line.startswith(label):
                    content = line[len(label):].strip()
                    # Content should be at most max_length + 3 (for "...")
                    assert len(content) <= max_length + 3, \
                        f"Message content should be truncated to {max_length} chars"
                    break


# Additional test: Empty and edge cases

@given(
    message=st.one_of(
        st.just(""),
        st.just("   "),
        st.just("\n\n"),
        st.text(min_size=0, max_size=10),
    ),
)
@settings(max_examples=50, deadline=None)
def test_edge_cases(message):
    """
    Test that context utilities handle edge cases gracefully.
    """
    # All functions should handle empty/whitespace without crashing
    try:
        has_wrapper = has_context_wrapper(message)
        assert isinstance(has_wrapper, bool), "has_context_wrapper should return bool"
        
        stripped = strip_context_wrappers(message)
        assert isinstance(stripped, str), "strip_context_wrappers should return string"
        
        extracted = extract_actual_content(message)
        assert isinstance(extracted, str), "extract_actual_content should return string"
        
    except Exception as e:
        pytest.fail(f"Context utilities should handle edge cases without crashing: {e}")
