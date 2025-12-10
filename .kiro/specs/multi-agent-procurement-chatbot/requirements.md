# Requirements Document

## Introduction

This document specifies the requirements for a Multi-Agent Procurement Chatbot system. The system implements a hierarchical agent architecture where a Selector (Mother) Agent analyzes user queries and routes them to specialized domain agents. Each specialized agent has access to specific API tools for requisitions, purchase orders, and framework agreements. The system must support both backend API configuration and frontend UI-based workflow creation with identical behavior.

## Glossary

- **Selector Agent (Mother Agent)**: The entry-point agent that analyzes user intent and routes queries to appropriate specialized agents
- **Specialized Agent**: Domain-specific agents (Requisition Agent, Purchase Order Agent, Framework Agreement Agent) that handle specific query types
- **API Tool**: A configured tool that calls external procurement APIs with user authentication context
- **Workflow**: A configured sequence of agent interactions defining how user queries are processed
- **Bearer Token**: JWT authentication token obtained from Keycloak IDP for API authentication
- **User Context**: Authentication headers (x-client-username, x-client-ref) forwarded to external APIs
- **Frontend Configuration**: Workflow/agent configuration created through the Admin UI
- **Backend Configuration**: Workflow/agent configuration defined in JSON config files

## Requirements

### Requirement 1

**User Story:** As a procurement user, I want to ask questions about my requisitions in natural language, so that I can quickly get status updates and details without navigating complex systems.

#### Acceptance Criteria

1. WHEN a user asks about requisition status THEN the Selector Agent SHALL route the query to the Requisition Agent
2. WHEN the Requisition Agent receives a query with a requisition number THEN the system SHALL call the requisition API with the provided number
3. WHEN the Requisition Agent receives a query without a requisition number THEN the system SHALL prompt the user to provide the requisition number
4. WHEN the API returns requisition data THEN the system SHALL format and present the relevant fields (status, projectInfo, sourceOfFund, officeName) in natural language
5. WHEN the API returns empty results THEN the system SHALL respond with "No requisition found with the provided number"

### Requirement 2

**User Story:** As a procurement user, I want to view my latest requisitions, so that I can track my recent procurement activities.

#### Acceptance Criteria

1. WHEN a user asks to see their latest requisitions THEN the Selector Agent SHALL route the query to the Requisition Agent
2. WHEN the Requisition Agent handles a "show my requisitions" query THEN the system SHALL call the self-requisitions API
3. WHEN the API returns requisition list THEN the system SHALL display up to 10 requisitions with requisitionNo, projectInfo, sourceOfFund, officeName, and status
4. WHEN the API returns an empty list THEN the system SHALL respond with "You do not have any requisitions at the moment"

### Requirement 3

**User Story:** As a procurement user, I want to find the initiator contact details for a requisition, so that I can follow up on procurement requests.

#### Acceptance Criteria

1. WHEN a user asks for PR initiator information THEN the Selector Agent SHALL route the query to the Requisition Agent
2. WHEN the Requisition Agent receives an initiator query without requisition number THEN the system SHALL prompt for the requisition number
3. WHEN the initiator API returns contact data THEN the system SHALL display name, email, and phone in natural language
4. WHEN all initiator fields are empty or null THEN the system SHALL respond with "Sorry, the initiator's name and contact details could not be found for this requisition"

### Requirement 4

**User Story:** As a procurement user, I want to check framework agreement availability for items, so that I can make informed purchasing decisions.

#### Acceptance Criteria

1. WHEN a user asks about framework agreements for an item THEN the Selector Agent SHALL route the query to the Framework Agreement Agent
2. WHEN the Framework Agreement Agent receives a query without item code or name THEN the system SHALL prompt for item identification
3. WHEN the item-wise API returns framework agreements THEN the system SHALL display frameworkAgreementNo, itemName, itemCode, agreementEndDate, minimumOrderQuantity, and specification
4. WHEN the API returns empty results THEN the system SHALL respond with "No framework agreement is available for this item"

### Requirement 5

**User Story:** As a procurement user, I want to know the total count of active framework agreements, so that I can understand the scope of available agreements.

#### Acceptance Criteria

1. WHEN a user asks how many framework agreements are active THEN the Selector Agent SHALL route the query to the Framework Agreement Agent
2. WHEN the Framework Agreement Agent handles a count query THEN the system SHALL call the framework agreement count API
3. WHEN the API returns a count THEN the system SHALL respond with the total number in natural language

### Requirement 6

**User Story:** As a procurement user, I want to check brand and specification information for items under framework agreements, so that I can evaluate product options.

#### Acceptance Criteria

1. WHEN a user asks about brands or specifications for an item THEN the Selector Agent SHALL route the query to the Framework Agreement Agent
2. WHEN the brand-info API returns data THEN the system SHALL display brand details when asked about brands
3. WHEN the brand-info API returns data THEN the system SHALL display specification details when asked about specifications
4. WHEN no brand or specification data exists THEN the system SHALL respond with "No brand or specification information is available for this item"

### Requirement 7

**User Story:** As a procurement user, I want to check purchase order status, so that I can track my orders through the procurement process.

#### Acceptance Criteria

1. WHEN a user asks about purchase order status THEN the Selector Agent SHALL route the query to the Purchase Order Agent
2. WHEN the Purchase Order Agent receives a query without PO number THEN the system SHALL prompt for the purchase order number
3. WHEN the purchase order API returns data THEN the system SHALL extract and display the status field
4. WHEN a user asks "Is my order approved?" THEN the system SHALL respond with yes/no based on the status value

### Requirement 8

**User Story:** As a procurement user, I want to view my latest purchase orders, so that I can track my recent orders.

#### Acceptance Criteria

1. WHEN a user asks to see their latest purchase orders THEN the Selector Agent SHALL route the query to the Purchase Order Agent
2. WHEN the self purchase order API returns data THEN the system SHALL display up to 10 orders with purchaseOrderNo, purchaseMethod, totalAmount, supplierName, purchaseOrderDate, and status
3. WHEN the API returns an empty list THEN the system SHALL respond with "You do not have any purchase orders at the moment"

### Requirement 9

**User Story:** As a system administrator, I want the chatbot workflow to be configurable from both backend JSON files and frontend UI, so that I can manage the system flexibly.

#### Acceptance Criteria

1. WHEN a workflow is created via backend JSON configuration THEN the system SHALL load and execute the workflow identically to frontend-created workflows
2. WHEN a workflow is created via frontend Admin UI THEN the system SHALL persist the configuration and execute it identically to backend-configured workflows
3. WHEN workflow configuration changes THEN the system SHALL apply changes without requiring service restart
4. WHEN an agent configuration references tools THEN the system SHALL validate that referenced tools exist

### Requirement 10

**User Story:** As a developer, I want the system to use bearer token authentication for API calls, so that user context is properly forwarded to external services.

#### Acceptance Criteria

1. WHEN the system needs to authenticate THEN the system SHALL obtain a bearer token from the Keycloak IDP endpoint
2. WHEN calling external procurement APIs THEN the system SHALL include x-client-username and x-client-ref headers from user context
3. WHEN a token expires or is invalid THEN the system SHALL handle the error gracefully and inform the user
4. WHEN testing workflows THEN the system SHALL support providing authentication credentials via curl-compatible format

### Requirement 11

**User Story:** As a developer, I want to clean up unrelated tools and workflows, so that the system only contains procurement-related functionality.

#### Acceptance Criteria

1. WHEN the system is configured THEN the system SHALL only include tools related to APIs, RAG, and web search
2. WHEN the system is configured THEN the system SHALL remove calculator, code execution, and other unrelated tools
3. WHEN workflows are configured THEN the system SHALL only include procurement-related workflows and the multi-agent chatbot workflow
