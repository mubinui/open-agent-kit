# Implementation Plan

## Global Requirements

### 1. Python Execution with `uv`
**MANDATORY: All Python execution in this project MUST use `uv` as the package manager and execution tool.**

- Use `uv run` for executing Python scripts
- Use `uv pip` for package management
- Use `uv sync` for dependency synchronization
- Use `uv venv` for virtual environment management

- [x] 1. Create context utilities module
  - Create `src/utils/context_utils.py` with sanitization functions
  - Implement `strip_context_wrappers()` to remove wrapper markers using regex
  - Implement `extract_actual_content()` to extract clean message content
  - Implement `has_context_wrapper()` to detect wrapper patterns
  - Implement `build_clean_context()` to build clean conversation context with limits
  - _Requirements: 1.1, 1.2, 1.4, 3.4_

- [x] 1.1 Write property test for context wrapper removal
  - **Property 1: Context Wrapper Removal**
  - **Validates: Requirements 1.1, 1.4**

- [x] 1.2 Write property test for context extraction consistency
  - **Property 4: Context Extraction Consistency**
  - **Validates: Requirements 1.2, 3.4**

- [x] 2. Add context configuration to settings
  - Add `ContextConfig` dataclass to `src/config/settings.py`
  - Add configuration fields for max_history_messages, max_context_exchanges, max_message_length
  - Add boolean flags for strip_wrappers_from_storage and strip_wrappers_from_response
  - Provide sensible defaults (10, 5, 500, True, True)
  - _Requirements: 3.1, 3.5_

- [x] 3. Enhance SessionManager with context sanitization
  - [x] 3.1 Add `_sanitize_response()` method to SessionManager
    - Import context_utils functions
    - Implement response sanitization using `strip_context_wrappers()`
    - Handle edge cases (empty responses, None values)
    - _Requirements: 1.1, 1.4_

  - [x] 3.2 Add `_build_context_message()` method to SessionManager
    - Implement context building with configurable limits
    - Support different context types (general, selector, domain)
    - Use `build_clean_context()` from context_utils
    - Prevent nested wrappers by checking existing messages
    - _Requirements: 1.2, 1.5, 3.1, 4.5_

  - [x] 3.3 Update `process_message()` to sanitize responses
    - Call `_sanitize_response()` on response_text before storing
    - Ensure stored messages are clean
    - _Requirements: 1.1, 1.3, 3.2_

  - [x] 3.4 Update `_execute_two_agent_workflow()` to use new context building
    - Replace inline context building with `_build_context_message()`
    - Use context_type="general"
    - Remove old context building code
    - _Requirements: 1.2, 1.5, 3.5_

  - [x] 3.5 Update `_execute_selector_workflow()` to use new context building
    - Use `_build_context_message()` with context_type="selector" for selector agent
    - Use `_build_context_message()` with context_type="domain" for domain agents
    - Remove old inline context building code
    - Ensure no nested wrappers are created
    - _Requirements: 1.2, 4.1, 4.2, 4.3, 4.5_

- [x] 3.6 Write property test for response sanitization
  - **Property 2: Response Sanitization**
  - **Validates: Requirements 1.1, 1.4**

- [x] 3.7 Write property test for message storage cleanliness
  - **Property 3: Message Storage Cleanliness**
  - **Validates: Requirements 1.3, 3.2**

- [x] 3.8 Write property test for nested wrapper prevention
  - **Property 7: Nested Wrapper Prevention**
  - **Validates: Requirements 1.2, 3.5**

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Add default workflow support to configuration
  - [x] 5.1 Update WorkflowConfig model
    - Add `default: bool = False` field to `src/config/workflow_models.py`
    - Update model validation if needed
    - _Requirements: 2.1_

  - [x] 5.2 Update workflows.json configuration
    - Add `"default": true` to procurement_chatbot workflow in `configs/workflows.json`
    - Ensure only one workflow has default=true
    - _Requirements: 2.1_

  - [x] 5.3 Enhance WorkflowRegistry with default workflow methods
    - Add `get_default_workflow()` method to return default WorkflowConfig
    - Add `get_default_workflow_id()` method to return default workflow ID
    - Handle case where no default is configured
    - Handle case where default workflow is disabled (fallback to first enabled)
    - _Requirements: 2.1, 2.4_

- [x] 5.4 Write property test for default workflow availability
  - **Property 5: Default Workflow Availability**
  - **Validates: Requirements 2.1, 2.4**

- [-] 6. Update API to use default workflow
  - [x] 6.1 Modify session creation endpoint
    - Update `POST /sessions` in `src/api/main.py`
    - Make workflow_id optional in CreateSessionRequest
    - Use `workflow_registry.get_default_workflow_id()` when workflow_id not provided
    - Return clear error if no workflow_id and no default configured
    - _Requirements: 2.2, 2.3_

  - [x] 6.2 Update API models
    - Make `workflow_id` optional in `CreateSessionRequest` in `src/api/models.py`
    - Update API documentation/docstrings
    - _Requirements: 2.2, 2.3_

  - [x] 6.3 Update workflow list endpoint
    - Modify `GET /workflows` to include default indicator
    - Add `is_default` field to workflow response
    - _Requirements: 2.4_

- [x] 6.4 Write unit tests for API default workflow handling
  - Test session creation without workflow_id
  - Test session creation with explicit workflow_id
  - Test error when no default configured
  - Test workflow list includes default indicator
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 7. Add property test for context window bounds
  - **Property 6: Context Window Bounds**
  - **Validates: Requirements 3.1, 3.5**

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update documentation
  - Update README.md with default workflow information
  - Document context sanitization behavior
  - Add examples of using default workflow
  - Document context configuration options
  - _Requirements: 2.1, 2.2, 3.1_
