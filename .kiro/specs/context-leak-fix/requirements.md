# Requirements Document

## Introduction

This document specifies requirements for fixing the context leaking problem in the conversation system and setting the procurement-chatbot workflow as the default. The context leaking issue occurs when conversation history is repeatedly wrapped with context markers, causing the full chat history to be exposed to users and creating nested context wrappers that grow exponentially.

## Glossary

- **Context Leaking**: The unintended exposure of internal conversation history wrappers and markers to end users, or the exponential growth of nested context in messages
- **Session Manager**: The component responsible for managing conversation sessions and processing messages through configured agents
- **Selector Workflow**: A workflow pattern that routes user queries to specialized domain agents based on intent analysis
- **Context Wrapper**: Text markers like "[Previous conversation context]" and "[Current message]" used to provide conversation history to agents
- **Procurement Chatbot**: The multi-agent chatbot workflow for procurement queries that routes to specialized agents

## Requirements

### Requirement 1

**User Story:** As a user, I want to see only the assistant's actual response without internal context markers or conversation history, so that I receive clean, professional responses.

#### Acceptance Criteria

1. WHEN the system processes a message THEN the system SHALL strip all context wrapper markers from the final response before returning it to the user
2. WHEN the system adds conversation context to agent messages THEN the system SHALL prevent nested context wrappers by detecting and removing existing wrappers before adding new ones
3. WHEN the system builds conversation history THEN the system SHALL store only the actual message content without context wrappers in the session state
4. WHEN extracting responses from chat results THEN the system SHALL remove any context markers that may have leaked into the response
5. WHEN the system formats messages for agents THEN the system SHALL use a maximum context window of 5 recent exchanges to prevent unbounded growth

### Requirement 2

**User Story:** As a system administrator, I want the procurement-chatbot workflow to be the default workflow, so that users are automatically routed to the appropriate procurement agents.

#### Acceptance Criteria

1. WHEN the system loads workflow configurations THEN the system SHALL mark the procurement_chatbot workflow as the default workflow
2. WHEN a user creates a session without specifying a workflow THEN the system SHALL use the procurement_chatbot workflow
3. WHEN the API receives a request without a workflow_id THEN the system SHALL default to the procurement_chatbot workflow
4. WHEN the system lists available workflows THEN the system SHALL indicate which workflow is the default
5. WHEN the default workflow is changed THEN the system SHALL update the configuration file with the new default setting

### Requirement 3

**User Story:** As a developer, I want conversation context to be managed efficiently, so that the system scales well and doesn't accumulate unbounded message history.

#### Acceptance Criteria

1. WHEN building context for agents THEN the system SHALL limit conversation history to a configurable maximum number of recent messages
2. WHEN storing messages in session state THEN the system SHALL store the original user message and the clean assistant response without any context wrappers
3. WHEN retrieving conversation history THEN the system SHALL return only the stored messages without reconstructing context wrappers
4. WHEN the system detects context wrapper patterns THEN the system SHALL extract only the actual message content
5. WHEN processing multi-turn conversations THEN the system SHALL maintain consistent context handling across all workflow patterns

### Requirement 4

**User Story:** As a user interacting with the selector workflow, I want my conversation context to be preserved correctly, so that agents understand references to previous messages without seeing internal markers.

#### Acceptance Criteria

1. WHEN the selector agent analyzes a message THEN the system SHALL provide compact conversation context without exposing wrapper markers
2. WHEN routing to a domain agent THEN the system SHALL provide relevant conversation history in a clean format
3. WHEN a domain agent processes a message THEN the system SHALL include only necessary context from recent exchanges
4. WHEN extracting the final response THEN the system SHALL ensure no context markers are visible to the user
5. WHEN building context for different agents THEN the system SHALL use appropriate context strategies for selector vs domain agents
