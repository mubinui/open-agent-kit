# Requirements Document

## Introduction

This document specifies the requirements for refactoring the message API endpoint in the orchestration service. The primary goal is to change the message sending endpoint from a path-parameter-based approach (`/api/v1/sessions/{session_id}/messages`) to a body-parameter-based approach (`/api/v1/sessions/query`) where the `sessionId` is included in the request body. Additionally, the system must preserve the bearer token in the authentication flow for frontend usage and maintain proper DTO structures throughout.

## Glossary

- **Orchestration_Service**: The backend service that manages conversation sessions and processes messages through AI agents
- **Session**: A conversation context that maintains state between user interactions
- **DTO (Data Transfer Object)**: A structured object used to transfer data between the API and clients
- **Bearer_Token**: A JWT authentication token used to authenticate API requests
- **Query_Endpoint**: The new unified endpoint for sending messages to sessions
- **Message_Request**: The request payload containing the message and session identifier
- **Message_Response**: The response payload containing the AI agent's response and metadata
- **Fallback_Response**: A user-friendly error message returned when the AI agent fails to generate a proper response
- **Workflow_Failure**: A condition where the AI agent or workflow execution fails to produce a valid response

## Requirements

### Requirement 1

**User Story:** As a frontend developer, I want to send messages using a single query endpoint with the session ID in the request body, so that I can simplify API integration and maintain consistent request patterns.

#### Acceptance Criteria

1. WHEN a user sends a POST request to `/api/v1/sessions/query` with a valid `sessionId` and `query` in the request body THEN the Orchestration_Service SHALL process the message and return a response
2. WHEN a user sends a request with an invalid or non-existent `sessionId` THEN the Orchestration_Service SHALL return a 404 error with a descriptive message
3. WHEN a user sends a request with an empty or whitespace-only `query` THEN the Orchestration_Service SHALL return a 400 error indicating invalid input
4. WHEN a user sends a request without authentication THEN the Orchestration_Service SHALL return a 401 error
5. THE Orchestration_Service SHALL maintain backward compatibility by keeping the existing `/api/v1/sessions/{session_id}/messages` endpoint functional

### Requirement 2

**User Story:** As a frontend developer, I want the bearer token to be preserved in the authentication response, so that I can use it for subsequent API calls without modification.

#### Acceptance Criteria

1. WHEN a user authenticates successfully THEN the Orchestration_Service SHALL return the complete bearer token without stripping any prefix
2. WHEN a user includes the bearer token in the Authorization header THEN the Orchestration_Service SHALL accept the token with or without the "Bearer " prefix
3. WHEN the raw token is extracted from the request THEN the Orchestration_Service SHALL store it in the CurrentUser context for forwarding to external services
4. THE Orchestration_Service SHALL preserve the raw JWT token throughout the request lifecycle for tool execution context

### Requirement 3

**User Story:** As a frontend developer, I want well-structured DTOs for the query endpoint, so that I can easily integrate with the API and handle responses consistently.

#### Acceptance Criteria

1. THE Orchestration_Service SHALL provide a `QueryRequest` DTO containing `sessionId` (string), `query` (string), and optional `metadata` (object) fields
2. THE Orchestration_Service SHALL provide a `QueryResponse` DTO containing `sessionId`, `response`, `turnCount`, `chatHistory`, `summary`, and `safetyPassed` fields
3. WHEN serializing response DTOs THEN the Orchestration_Service SHALL use camelCase field naming for frontend compatibility
4. THE Orchestration_Service SHALL validate all required fields in the `QueryRequest` DTO before processing
5. WHEN a request contains additional unknown fields THEN the Orchestration_Service SHALL ignore them without error (forward compatibility)

### Requirement 4

**User Story:** As a system administrator, I want the API changes to be documented, so that API consumers can understand the new endpoint structure.

#### Acceptance Criteria

1. WHEN the query endpoint is implemented THEN the Orchestration_Service SHALL expose OpenAPI documentation for the new endpoint
2. THE Orchestration_Service SHALL include request and response examples in the API documentation
3. THE Orchestration_Service SHALL update the API_ENDPOINTS.txt file to reflect the new query endpoint

### Requirement 5

**User Story:** As a developer, I want the query endpoint to support the same conversation patterns as the existing message endpoint, so that all workflow types continue to function correctly.

#### Acceptance Criteria

1. WHEN a query is processed THEN the Orchestration_Service SHALL support all existing conversation patterns (TWO_AGENT, SEQUENTIAL, GROUP_CHAT, NESTED, SELECTOR)
2. THE Orchestration_Service SHALL allow optional `pattern` and `maxTurns` parameters in the QueryRequest DTO
3. WHEN pattern or maxTurns are not specified THEN the Orchestration_Service SHALL use the workflow's default configuration

### Requirement 6

**User Story:** As a user, I want to receive a friendly error message when the chatbot fails to generate a response, so that I am not confused by seeing raw conversation history or internal context.

#### Acceptance Criteria

1. WHEN the workflow execution fails to produce a valid response THEN the Orchestration_Service SHALL return a user-friendly Fallback_Response instead of raw conversation data
2. WHEN the AI agent returns an empty or null response THEN the Orchestration_Service SHALL substitute it with a configurable fallback message
3. WHEN the response contains only internal context or chat history without an actual answer THEN the Orchestration_Service SHALL detect this condition and return a Fallback_Response
4. THE Orchestration_Service SHALL provide a default fallback message such as "I apologize, but I was unable to process your request. Please try again or rephrase your question."
5. THE Orchestration_Service SHALL log the original failed response for debugging purposes while returning the Fallback_Response to the user
6. WHEN a Fallback_Response is returned THEN the Orchestration_Service SHALL set a flag in the response metadata indicating the response is a fallback
