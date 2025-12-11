"""Utilities for managing conversation context and sanitizing messages.

This module provides functions to:
- Detect and remove context wrapper markers from messages
- Extract actual message content from wrapped messages
- Build clean conversation context with configurable limits
"""

import re
from typing import List, Optional

from src.memory.models import Message


# Individual wrapper markers to detect and remove
WRAPPER_MARKERS = [
    r'\[Previous conversation context\]',
    r'\[Current message\]',
    r'\[Recent conversation for context\]',
    r'\[Current user message to route\]',
]

# Compiled patterns for marker detection (case-insensitive)
MARKER_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in WRAPPER_MARKERS]


def strip_context_wrappers(message: str) -> str:
    """
    Remove context wrapper markers from a message.
    
    Removes patterns like:
    - [Previous conversation context]
    - [Current message]
    - [Recent conversation for context]
    - [Current user message to route]
    
    This function is idempotent - applying it multiple times produces
    the same result as applying it once.
    
    Args:
        message: Message potentially containing context wrappers
        
    Returns:
        Message with context wrappers removed
    """
    if not message:
        return message
    
    result = message
    
    # Remove all wrapper markers
    for pattern in MARKER_PATTERNS:
        result = pattern.sub('', result)
    
    # Clean up extra whitespace (multiple newlines, leading/trailing whitespace)
    # Normalize multiple newlines to single newlines
    result = re.sub(r'\n\s*\n', '\n', result)
    result = result.strip()
    
    # If we ended up with empty string, return original stripped
    if not result:
        return message.strip()
    
    return result


def has_context_wrapper(message: str) -> bool:
    """
    Check if a message contains context wrapper markers.
    
    Args:
        message: Message to check
        
    Returns:
        True if message contains context wrappers
    """
    if not message:
        return False
    
    # Check for any of the wrapper patterns
    for pattern in MARKER_PATTERNS:
        if pattern.search(message):
            return True
    
    return False


def extract_actual_content(message: str) -> str:
    """
    Extract the actual message content from a wrapped message.
    
    If message contains context wrappers, extracts only the current
    message portion. Otherwise returns the message as-is.
    
    This function looks for content after markers like "[Current message]"
    or "[Current user message to route]" and returns that content.
    
    Args:
        message: Message potentially containing context wrappers
        
    Returns:
        Actual message content without wrappers
    """
    if not message:
        return message
    
    # Try to extract content after "Current message" markers
    # These patterns capture everything after the marker
    current_message_patterns = [
        r'\[Current message\]\s*(.*)',
        r'\[Current user message to route\]\s*(.*)',
    ]
    
    for pattern_str in current_message_patterns:
        pattern = re.compile(pattern_str, re.DOTALL | re.IGNORECASE)
        match = pattern.search(message)
        if match:
            content = match.group(1).strip()
            if content:
                # Recursively strip any remaining wrappers from the content
                return strip_context_wrappers(content)
            else:
                # Content after marker is empty/whitespace - return empty string
                # This is the actual content (nothing)
                return ""
    
    # If no specific current message marker found, just strip all wrappers
    return strip_context_wrappers(message)


def build_clean_context(
    messages: List[Message],
    limit: int = 5,
    max_message_length: int = 500
) -> str:
    """
    Build clean conversation context from message history.
    
    Creates a formatted string containing recent conversation history
    without any context wrapper markers. Messages are truncated if they
    exceed the maximum length.
    
    Args:
        messages: List of conversation messages
        limit: Maximum number of recent messages to include
        max_message_length: Maximum length for individual messages
        
    Returns:
        Formatted conversation context string
    """
    if not messages:
        return ""
    
    # Take only the most recent messages up to the limit
    recent_messages = messages[-limit:] if len(messages) > limit else messages
    
    # Build context string
    context_parts = []
    
    for msg in recent_messages:
        # Skip messages that are themselves context wrappers
        if has_context_wrapper(msg.content):
            # Extract actual content if it's wrapped
            content = extract_actual_content(msg.content)
        else:
            content = msg.content
        
        # Truncate if too long
        if len(content) > max_message_length:
            content = content[:max_message_length] + "..."
        
        # Format based on role
        role_label = msg.role.value.capitalize()
        context_parts.append(f"{role_label}: {content}")
    
    return "\n".join(context_parts)
