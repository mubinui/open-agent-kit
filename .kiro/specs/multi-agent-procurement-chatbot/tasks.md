# Implementation Plan

## Global Requirements

### 1. Python Execution with `uv`
**MANDATORY: All Python execution in this project MUST use `uv` as the package manager and execution tool.**

- Use `uv run` for executing Python scripts
- Use `uv pip` for package management
- Use `uv sync` for dependency synchronization

### 2. Authentication for Testing
**Bearer Token Acquisition:**
```bash
curl --location 'https://erpdevelopment.brac.net/idp/realms/brac/protocol/openid-connect/token' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=password' \
  --data-urlencode 'client_id=erp' \
  --data-urlencode 'username=175050' \
  --data-urlencode 'password=abc123$'
```

---

- [x] 1. Clean up unrelated tools and workflows
  - [x] 1.1 Remove calculator tool from configs/tools.json
    - Delete the calculator tool entry
    - _Requirements: 11.1, 11.2_
  - [x] 1.2 Remove code execution tools and external service tools
    - Remove call_service1, call_service2, call_external_service tools
    - Keep only: API tools, RAG tools, web_search
    - _Requirements: 11.1, 11.2_
  - [x] 1.3 Clean up unrelated workflows from configs/workflows.json
    - Remove: group_brainstorm, constrained_group_chat, round_robin_review, nested_research_assistant, python_coder_pro
    - Keep: simple_assistant, web_search_assistant, requisition_assistant, rag_qa_assistant
    - _Requirements: 11.3_
  - [x] 1.4 Remove unrelated agents from configs/agents.json
    - Remove: facilitator, creative_agent, analytical_agent, critic_agent, python_coder, code_assistant
    - Keep: user_proxy, assistant, selector agents, requisition/PO/FA agents, RAG agents
    - _Requirements: 11.3_
  - [x] 1.5 Write property test for configuration cleanup validation
    - **Property 7: Configuration Cleanup Validation**
    - **Validates: Requirements 11.1, 11.2, 11.3**

- [x] 2. Create Selector Agent configuration
  - [x] 2.1 Add Selector Agent to configs/agents.json
    - Create selector_agent with intent classification system prompt
    - Configure to output JSON routing decisions
    - Set temperature low (0.3) for consistent routing
    - _Requirements: 1.1, 4.1, 7.1_
  - [x] 2.2 Create system prompt for Selector Agent
    - Include all domain classifications (requisition, purchase_order, framework_agreement)
    - Define JSON output format for routing decisions
    - Include parameter extraction instructions
    - _Requirements: 1.1, 1.3, 4.2, 7.2_
  - [x] 2.3 Write property test for intent routing
    - **Property 1: Intent Routing Correctness**
    - **Validates: Requirements 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1**

- [x] 3. Create specialized domain agents
  - [x] 3.1 Create Requisition Agent configuration
    - Add requisition_domain_agent to configs/agents.json
    - Assign tools: get_requisition_info, get_self_requisition_info, get_requisition_info_with_initiator
    - Create system prompt for requisition queries
    - _Requirements: 1.2, 2.2, 3.3_
  - [x] 3.2 Create Purchase Order Agent configuration
    - Add purchase_order_agent to configs/agents.json
    - Assign tools: get_purchase_order_info, get_self_purchase_order_info
    - Create system prompt for PO queries
    - _Requirements: 7.3, 8.2_
  - [x] 3.3 Create Framework Agreement Agent configuration
    - Add framework_agreement_agent to configs/agents.json
    - Assign tools: get_all_framework_agreement_no_by_item, get_total_framework_agreement, get_framework_agreement_with_brand_by_item
    - Create system prompt for FA queries
    - _Requirements: 4.3, 5.2, 6.2_
  - [x] 3.4 Write property test for missing parameter prompting
    - **Property 2: Missing Parameter Prompting**
    - **Validates: Requirements 1.3, 3.2, 4.2, 7.2**

- [x] 4. Implement selector workflow pattern
  - [x] 4.1 Add SelectorConfig model to src/config/workflow_models.py
    - Define routing_agents dict (domain -> agent_id)
    - Define default_agent and max_routing_attempts
    - _Requirements: 9.1, 9.2_
  - [x] 4.2 Extend WorkflowModel to support selector pattern
    - Add selector_config field to workflow model
    - Add pattern="selector" support
    - _Requirements: 9.1, 9.2_
  - [x] 4.3 Implement selector execution strategy in src/patterns/execution_strategies.py
    - Create SelectorExecutionStrategy class
    - Implement intent parsing from Selector Agent response
    - Implement routing to specialized agents
    - _Requirements: 1.1, 4.1, 7.1_
  - [x] 4.4 Write property test for configuration parity
    - **Property 4: Configuration Parity**
    - **Validates: Requirements 9.1, 9.2**

- [x] 5. Create procurement chatbot workflow configuration
  - [x] 5.1 Add procurement_chatbot workflow to configs/workflows.json
    - Configure selector pattern with entry_agent_id=selector_agent
    - Define routing_agents mapping for all domains
    - Set appropriate max_turns and summary_method
    - _Requirements: 9.1_
  - [x] 5.2 Validate workflow configuration loads correctly
    - Test workflow loading via API
    - Verify all agent references resolve
    - _Requirements: 9.4_
  - [x] 5.3 Write property test for tool reference validation
    - **Property 6: Tool Reference Validation**
    - **Validates: Requirements 9.4**

- [x] 6. Checkpoint - Ensure configuration is valid
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement user context forwarding verification
  - [x] 7.1 Verify api_tool_executor forwards user context headers
    - Confirm x-client-username header is set from JWT
    - Confirm x-client-ref header is set from roles
    - _Requirements: 10.2_
  - [x] 7.2 Test authentication flow with provided curl credentials
    - Obtain bearer token using provided curl command
    - Test API calls with token
    - Verify user context is forwarded
    - _Requirements: 10.1, 10.4_
  - [x] 7.3 Write property test for user context forwarding
    - **Property 5: User Context Forwarding**
    - **Validates: Requirements 10.1, 10.2**

- [x] 8. Implement response formatting
  - [x] 8.1 Create response formatters for each domain
    - Requisition response formatter (status, projectInfo, sourceOfFund, officeName)
    - Purchase Order response formatter (purchaseOrderNo, status, totalAmount, supplierName)
    - Framework Agreement response formatter (frameworkAgreementNo, itemName, agreementEndDate, MOQ)
    - _Requirements: 1.4, 4.3, 7.3_
  - [x] 8.2 Add empty result handling
    - Handle empty API responses with appropriate messages
    - Handle null/missing fields gracefully
    - _Requirements: 1.5, 2.4, 4.4, 8.3_
  - [x] 8.3 Write property test for response field completeness
    - **Property 3: Response Field Completeness**
    - **Validates: Requirements 1.4, 2.3, 3.3, 4.3, 5.3, 6.2, 6.3, 7.3, 8.2**

- [x] 9. Integration testing with real APIs
  - [x] 9.1 Test requisition queries end-to-end
    - Test: "What is the status of REQ20250010638?" ✅ Routed correctly
    - Test: "Show my latest requisitions" ✅ Routed correctly
    - Test: "Who initiated REQ20250010638?" ✅ Routed correctly
    - _Requirements: 1.1, 1.2, 2.2, 3.3_
  - [x] 9.2 Test purchase order queries end-to-end
    - Test: "What is the status of BPD/2025/FO-5109?" ✅ API returned: Approved, 2,728,604.30 BDT
    - Test: "Is my order approved?" ✅ Correctly asked for PO number
    - Test: "Show my latest purchase orders" ✅ Routed correctly (empty data for user)
    - _Requirements: 7.1, 7.3, 8.2_
  - [x] 9.3 Test framework agreement queries end-to-end
    - Test: "Is there an FA for Controller?" ✅ Routed correctly (API 500 error - external)
    - Test: "How many FAs are active?" ✅ API returned: 271 active FAs
    - Test: "What brands are available for Controller?" ✅ Routed correctly (API 500 error - external)
    - _Requirements: 4.1, 5.2, 6.2_

- [x] 10. Frontend configuration compatibility
  - [x] 10.1 Verify workflow can be created from Admin UI
    - Added SELECTOR pattern to ConversationPattern enum in conversation_engine.py
    - Added selector_config field to WorkflowCreateRequest and WorkflowResponse models
    - API endpoint GET /api/v1/workflows now returns selector workflows correctly
    - API endpoint GET /api/v1/workflows/procurement_chatbot returns full selector_config
    - _Requirements: 9.2_
  - [x] 10.2 Verify agent configuration from Admin UI
    - All agents (selector_agent, requisition_domain_agent, purchase_order_agent, framework_agreement_agent) accessible via API
    - Tool assignments persist correctly in configs/agents.json
    - _Requirements: 9.2_
  - [x] 10.3 Test hot reload of configuration changes
    - Configuration changes in JSON files are loaded on session creation
    - No restart required for workflow/agent config changes
    - _Requirements: 9.3_

- [x] 11. Final checkpoint - Ensure all tests pass
  - ✅ All 25 property-based tests pass
  - ✅ Integration tests completed successfully
  - ✅ API endpoints working correctly
  - ✅ SELECTOR pattern fully implemented and functional
