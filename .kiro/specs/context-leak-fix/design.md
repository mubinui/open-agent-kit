# Design Document

## Overview

This design addresses the context leaking problem in the conversation system and implements a default workflow configuration. The solution involves:

1. **Context Sanitization**: Implementing utility functions to detect and remove context wrapper markers from messages
2. **Clean Message Storage**: Ensuring only actual message content is stored in session state
3. **Response Extraction**: Adding post-processing to strip context markers from final responses
4. **Default Workflow Configuration**: Adding a default workflow field to the workflow configuration system
5. **Context Window Management**: Implementing configurable limits on conversation history size

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     SessionManager                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  process_message()                                     │  │
│  │    ↓                                                   │  │
│  │  _execute_workflow()                                   │  │
│  │    ↓                                                   │  │
│  │  _execute_selector_workflow() / _execute_two_agent()  │  │
│  │    ↓                                                   │  │
│  │  _build_context_message() [NEW]                       │  │
│  │    ↓                                                   │  │
│  │  pattern_engine.execute_two_agent_chat()              │  │
│  │    ↓                                                   │  │
│  │  _extract_response_from_chat_result()                 │  │
│  │    ↓                                                   │  │
│  │  _sanitize_response() [NEW]                           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Context Utilities Module [NEW]                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  strip_context_wrappers(message: str) -> str          │  │
│  │  extract_actual_content(message: str) -> str          │  │
│  │  has_context_wrapper(message: str) -> bool            │  │
│  │  build_clean_context(messages: List, limit: int)     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Workflow Registry                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  get_default_workflow() -> WorkflowConfig [NEW]       │  │
│  │  set_default_workflow(workflow_id: str) [NEW]         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Context Utilities Module

A new utility module for handling conversation context sanitization.

**Location**: `src/utils/context_utils.py`

**Functions**:

```python
def strip_context_wrappers(message: str) -> str:
    """
    Remove context wrapper markers from a message.
    
    Removes patterns like:
    - [Previous conversation context]
    - [Current message]
    - [Recent conversation for context]
    - [Current user message to route]
    
    Args:
        message: Message potentially containing context wrappers
        
    Returns:
        Message with context wrappers removed
    """

def extract_actual_content(message: str) -> str:
    """
    Extract the actual message content from a wrapped message.
    
    If message contains context wrappers, extracts only the current
    message portion. Otherwise returns the message as-is.
    
    Args:
        message: Message potentially containing context wrappers
        
    Returns:
        Actual message content without wrappers
    """

def has_context_wrapper(message: str) -> bool:
    """
    Check if a message contains context wrapper markers.
    
    Args:
        message: Message to check
        
    Returns:
        True if message contains context wrappers
    """

def build_clean_context(
    messages: List[Message],
    limit: int = 5,
    max_message_length: int = 500
) -> str:
    """
    Build clean conversation context from message history.
    
    Args:
        messages: List of conversation messages
        limit: Maximum number of recent messages to include
        max_message_length: Maximum length for individual messages
        
    Returns:
        Formatted conversation context string
    """
```

### 2. SessionManager Enhancements

**Modified Methods**:

- `process_message()`: Add response sanitization before storing
- `_execute_two_agent_workflow()`: Use context utilities for building context
- `_execute_selector_workflow()`: Use context utilities for both selector and domain agent contexts
- `_sanitize_response()`: New method to clean responses before returning to user
- `_build_context_message()`: New method to centralize context building logic

**New Method Signatures**:

```python
def _sanitize_response(self, response: str) -> str:
    """
    Sanitize response by removing context wrappers and markers.
    
    Args:
        response: Raw response from agent
        
    Returns:
        Cleaned response suitable for user display
    """

def _build_context_message(
    self,
    current_message: str,
    session: Optional[ConversationState],
    context_type: str = "general",
    max_exchanges: int = 5
) -> str:
    """
    Build a message with conversation context.
    
    Args:
        current_message: The current user message
        session: Conversation session with history
        context_type: Type of context ("general", "selector", "domain")
        max_exchanges: Maximum number of recent exchanges to include
        
    Returns:
        Message with appropriate context formatting
    """
```

### 3. Workflow Configuration Enhancement

**Modified Files**:
- `configs/workflows.json`: Add `"default": true` field to procurement_chatbot
- `src/config/workflow_models.py`: Add `default` field to WorkflowConfig model
- `src/config/workflow_registry.py`: Add methods for default workflow management

**New WorkflowConfig Field**:

```python
class WorkflowConfig(BaseModel):
    # ... existing fields ...
    default: bool = False  # NEW: Indicates if this is the default workflow
```

**New WorkflowRegistry Methods**:

```python
def get_default_workflow(self) -> Optional[WorkflowConfig]:
    """
    Get the default workflow configuration.
    
    Returns:
        Default workflow config or None if no default is set
    """

def get_default_workflow_id(self) -> Optional[str]:
    """
    Get the ID of the default workflow.
    
    Returns:
        Default workflow ID or None if no default is set
    """
```

### 4. API Endpoint Enhancement

**Modified File**: `src/api/main.py`

**Modified Endpoint**: `POST /sessions`

```python
@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Create a new conversation session.
    
    If workflow_id is not provided, uses the default workflow.
    """
    workflow_id = request.workflow_id
    
    # Use default workflow if not specified
    if not workflow_id:
        workflow_registry = get_workflow_registry()
        workflow_id = workflow_registry.get_default_workflow_id()
        if not workflow_id:
            raise HTTPException(
                status_code=400,
                detail="No workflow_id provided and no default workflow configured"
            )
    
    # ... rest of implementation
```

## Data Models

### Context Configuration

```python
@dataclass
class ContextConfig:
    """Configuration for conversation context management."""
    
    max_history_messages: int = 10  # Maximum messages to keep in history
    max_context_exchanges: int = 5  # Maximum exchanges to include in context
    max_message_length: int = 500  # Maximum length for individual messages in context
    strip_wrappers_from_storage: bool = True  # Strip wrappers before storing
    strip_wrappers_from_response: bool = True  # Strip wrappers from final response
```

This configuration can be added to the settings system for flexibility.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Context Wrapper Removal

*For any* message containing context wrapper markers, applying `strip_context_wrappers()` should return a message without any wrapper markers, and applying it twice should produce the same result as applying it once (idempotent).

**Validates: Requirements 1.1, 1.4**

### Property 2: Response Sanitization

*For any* response returned to the user through `process_message()`, the response should not contain any context wrapper markers like "[Previous conversation context]" or "[Current message]".

**Validates: Requirements 1.1, 1.4**

### Property 3: Message Storage Cleanliness

*For any* message stored in session state, the message content should not contain context wrapper markers.

**Validates: Requirements 1.3, 3.2**

### Property 4: Context Extraction Consistency

*For any* message, if `has_context_wrapper()` returns True, then `extract_actual_content()` should return a non-empty string that is different from the original message.

**Validates: Requirements 1.2, 3.4**

### Property 5: Default Workflow Availability

*For any* workflow registry with at least one workflow marked as default, `get_default_workflow()` should return a non-null WorkflowConfig.

**Validates: Requirements 2.1, 2.4**

### Property 6: Context Window Bounds

*For any* conversation history, the context built by `build_clean_context()` should include at most the specified limit of recent messages.

**Validates: Requirements 3.1, 3.5**

### Property 7: Nested Wrapper Prevention

*For any* message that already contains context wrappers, building context with that message should not create nested wrappers (wrappers within wrappers).

**Validates: Requirements 1.2, 3.5**

## Error Handling

### Context Sanitization Errors

- **Malformed Context Markers**: If context markers are incomplete or malformed, extract as much clean content as possible
- **Empty Content After Stripping**: If stripping wrappers results in empty content, return the original message
- **Regex Errors**: Use defensive regex patterns with fallbacks to simple string operations

### Default Workflow Errors

- **No Default Configured**: Return clear error message indicating no default workflow is set
- **Default Workflow Disabled**: If default workflow is disabled, fall back to first enabled workflow
- **Default Workflow Not Found**: Log error and return None, allowing calling code to handle

### Context Building Errors

- **Empty Message History**: Return the current message without context
- **Invalid Message Objects**: Skip invalid messages and continue with valid ones
- **Encoding Issues**: Handle unicode and special characters gracefully

## Testing Strategy

### Unit Tests

1. **Context Utilities Tests**:
   - Test `strip_context_wrappers()` with various wrapper patterns
   - Test `extract_actual_content()` with nested and single wrappers
   - Test `has_context_wrapper()` with edge cases
   - Test `build_clean_context()` with different message counts

2. **SessionManager Tests**:
   - Test `_sanitize_response()` with various response formats
   - Test `_build_context_message()` with different context types
   - Test message storage without wrappers
   - Test response extraction and sanitization

3. **Workflow Registry Tests**:
   - Test `get_default_workflow()` with and without defaults
   - Test handling of multiple default workflows (should use first)
   - Test default workflow with disabled workflows

4. **API Tests**:
   - Test session creation without workflow_id (should use default)
   - Test session creation with explicit workflow_id
   - Test error handling when no default is configured

### Property-Based Tests

Property-based testing will use the `hypothesis` library for Python to generate random test cases.

1. **Property Test for Context Wrapper Idempotence**:
   - Generate random messages with and without wrappers
   - Verify that applying `strip_context_wrappers()` twice produces same result as once

2. **Property Test for Response Cleanliness**:
   - Generate random responses with various wrapper patterns
   - Verify that sanitized responses never contain wrapper markers

3. **Property Test for Context Window Limits**:
   - Generate random message histories of various lengths
   - Verify that built context never exceeds specified limits

4. **Property Test for Nested Wrapper Prevention**:
   - Generate messages with existing wrappers
   - Build context and verify no nested wrappers are created

### Integration Tests

1. **End-to-End Context Flow**:
   - Create session, send multiple messages
   - Verify responses are clean at each step
   - Verify stored messages don't contain wrappers

2. **Selector Workflow Context**:
   - Test selector workflow with conversation history
   - Verify context is provided to agents but not leaked to user
   - Verify routing works correctly with context

3. **Default Workflow Integration**:
   - Test session creation without workflow_id
   - Verify procurement_chatbot is used by default
   - Test routing to domain agents

## Implementation Notes

### Context Wrapper Patterns

The following patterns should be detected and removed:

```
[Previous conversation context]
...
[Current message]
...

[Recent conversation for context]
...
[Current user message to route]
...
```

Use regex patterns like:
```python
CONTEXT_WRAPPER_PATTERN = r'\[Previous conversation context\].*?\[Current message\]'
SELECTOR_WRAPPER_PATTERN = r'\[Recent conversation for context\].*?\[Current user message to route\]'
```

### Context Building Strategy

Different context strategies for different use cases:

1. **General Context** (two-agent workflow):
   - Include last 5 exchanges (10 messages)
   - Truncate long messages to 500 chars
   - Simple format: "User: ...\nAssistant: ...\n"

2. **Selector Context**:
   - Include last 3 exchanges (6 messages)
   - Truncate to 200 chars per message
   - Skip messages that are themselves context wrappers
   - Focus on helping selector understand references

3. **Domain Agent Context**:
   - Include last 5 exchanges (10 messages)
   - Truncate to 500 chars per message
   - Provide full context for domain-specific processing

### Performance Considerations

- Context sanitization should be O(n) where n is message length
- Use compiled regex patterns for better performance
- Cache cleaned messages to avoid repeated sanitization
- Limit context window to prevent unbounded growth

### Backward Compatibility

- Existing sessions will continue to work
- Old messages with wrappers will be cleaned on read
- No database migration required
- Configuration changes are additive (default field is optional)
