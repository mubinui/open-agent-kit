# Implementation Plan

## Global Requirements

### 1. Python Execution with `uv`
**MANDATORY: All Python execution in this project MUST use `uv` as the package manager and execution tool.**

- Use `uv run` for executing Python scripts
- Use `uv pip` for package management
- Use `uv sync` for dependency synchronization


- [x] 1. Create new DTOs for the query endpoint
  - [x] 1.1 Add QueryRequest DTO to src/api/models.py
    - Add `sessionId` (string, required), `query` (string, required, min_length=1), `pattern` (optional), `maxTurns` (optional), `metadata` (optional dict)
    - Configure Pydantic model with `populate_by_name = True` for camelCase support
    - Add validation to reject whitespace-only queries
    - _Requirements: 3.1, 3.4, 1.3_
  - [x] 1.2 Add QueryResponse DTO to src/api/models.py
    - Add `sessionId`, `response`, `turnCount`, `chatHistory`, `summary`, `safetyPassed`, `cost`, `metadata` fields
    - Configure camelCase serialization using Field aliases
    - _Requirements: 3.2, 3.3_
  - [x] 1.3 Write property test for QueryRequest validation
    - **Property 3: Whitespace Query Rejection**
    - **Validates: Requirements 1.3, 3.4**
  - [x] 1.4 Write property test for QueryResponse serialization
    - **Property 6: CamelCase Serialization**
    - **Validates: Requirements 3.3**

- [x] 2. Implement the query endpoint
  - [x] 2.1 Add query endpoint to src/api/routers/sessions.py
    - Create `POST /api/v1/sessions/query` route
    - Parse `sessionId` from request body and convert to UUID
    - Reuse existing `process_message` logic from SessionManager
    - Set tool execution context with raw token
    - _Requirements: 1.1, 1.4, 2.3, 2.4_
  - [x] 2.2 Add error handling for invalid session IDs
    - Return 404 for non-existent sessions
    - Return 400 for invalid UUID format
    - _Requirements: 1.2_
  - [x] 2.3 Write property test for valid query processing
    - **Property 1: Valid Query Processing**
    - **Validates: Requirements 1.1, 5.1**
  - [x] 2.4 Write property test for invalid session rejection
    - **Property 2: Invalid Session Rejection**
    - **Validates: Requirements 1.2**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Ensure token preservation in authentication flow
  - [x] 4.1 Verify raw token is preserved in CurrentUser
    - Confirm Keycloak middleware stores raw token in `CurrentUser.raw_token`
    - Ensure token is passed to tool execution context
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 4.2 Write property test for token preservation
    - **Property 5: Token Preservation**
    - **Validates: Requirements 2.3, 2.4**

- [x] 5. Implement forward compatibility and optional parameters
  - [x] 5.1 Configure QueryRequest to ignore unknown fields
    - Set Pydantic model config to allow extra fields
    - _Requirements: 3.5_
  - [x] 5.2 Implement default parameter handling
    - Use workflow defaults when `pattern` and `maxTurns` are not provided
    - _Requirements: 5.2, 5.3_
  - [x] 5.3 Write property test for forward compatibility
    - **Property 7: Forward Compatibility**
    - **Validates: Requirements 3.5**
  - [x] 5.4 Write property test for optional parameters
    - **Property 8: Optional Parameters Default Behavior**
    - **Validates: Requirements 5.2, 5.3**

- [x] 6. Implement graceful error handling with fallback responses
  - [x] 6.1 Create ResponseValidator utility class
    - Add `is_valid_response()` method to detect empty, null, or context-only responses
    - Add `get_fallback_response()` method to return user-friendly message
    - Define default fallback message: "I apologize, but I was unable to process your request. Please try again or rephrase your question."
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [x] 6.2 Integrate ResponseValidator into query endpoint
    - Validate response before returning to user
    - Set `isFallback: true` and `fallbackReason` in metadata when fallback is used
    - Log original failed response for debugging
    - _Requirements: 6.5, 6.6_
  - [x] 6.3 Apply fallback handling to existing messages endpoint
    - Ensure both endpoints have consistent fallback behavior
    - _Requirements: 6.1_
  - [x] 6.4 Write property test for fallback response
    - **Property 9: Fallback Response for Invalid Agent Output**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6**
  - [x] 6.5 Write property test for fallback logging
    - **Property 10: Fallback Response Logging**
    - **Validates: Requirements 6.5**

- [x] 7. Verify backward compatibility
  - [x] 7.1 Ensure existing endpoint remains functional
    - Verify `/api/v1/sessions/{session_id}/messages` still works
    - _Requirements: 1.5_
  - [x] 7.2 Write property test for endpoint equivalence
    - **Property 4: Endpoint Equivalence**
    - **Validates: Requirements 1.5**

- [x] 8. Update documentation
  - [x] 8.1 Update API_ENDPOINTS.txt
    - Add new `/api/v1/sessions/query` endpoint documentation
    - Add usage examples
    - _Requirements: 4.1, 4.3_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
