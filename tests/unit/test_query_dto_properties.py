"""Property-based tests for Query DTOs and Query Endpoint.

Tests for QueryRequest and QueryResponse DTOs used by the /api/v1/sessions/query endpoint.
"""

import pytest
from typing import Any
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import ValidationError
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from src.api.models import QueryRequest, QueryResponse
from src.api.main import app
from src.api.auth import CurrentUser, require_user
from src.patterns.conversation_engine import ConversationPattern
from src.infrastructure.database.mongo_auth_store import UserRole


# **Feature: message-api-refactor, Property 3: Whitespace Query Rejection**
# **Validates: Requirements 1.3, 3.4**
@given(
    whitespace_query=st.text(
        alphabet=" \t\n\r\f\v",
        min_size=0,
        max_size=100,
    ),
    session_id=st.uuids().map(str),
)
@settings(max_examples=100)
def test_whitespace_query_rejection(whitespace_query: str, session_id: str):
    """
    Test that whitespace-only queries are rejected.
    
    For any string composed entirely of whitespace characters (spaces, tabs, newlines),
    sending it as the `query` field should result in a validation error.
    
    **Feature: message-api-refactor, Property 3: Whitespace Query Rejection**
    **Validates: Requirements 1.3, 3.4**
    """
    with pytest.raises(ValidationError) as exc_info:
        QueryRequest(
            sessionId=session_id,
            query=whitespace_query,
        )
    
    # Verify the error is related to the query field
    errors = exc_info.value.errors()
    query_errors = [e for e in errors if "query" in str(e.get("loc", []))]
    assert len(query_errors) > 0, "Should have validation error for query field"


# **Feature: message-api-refactor, Property 6: CamelCase Serialization**
# **Validates: Requirements 3.3**
@given(
    session_id=st.uuids().map(str),
    response_text=st.text(min_size=1, max_size=500),
    turn_count=st.integers(min_value=0, max_value=1000),
    summary=st.text(max_size=200),
    safety_passed=st.booleans(),
)
@settings(max_examples=100)
def test_query_response_camelcase_serialization(
    session_id: str,
    response_text: str,
    turn_count: int,
    summary: str,
    safety_passed: bool,
):
    """
    Test that QueryResponse serializes to camelCase field names.
    
    For any valid QueryResponse object, when serialized to JSON, all field names
    should be in camelCase format (e.g., sessionId, turnCount, chatHistory, safetyPassed).
    
    **Feature: message-api-refactor, Property 6: CamelCase Serialization**
    **Validates: Requirements 3.3**
    """
    response = QueryResponse(
        session_id=session_id,
        response=response_text,
        turn_count=turn_count,
        chat_history=[],
        summary=summary,
        safety_passed=safety_passed,
        cost={},
        metadata={},
    )
    
    # Serialize to dict with aliases (camelCase)
    serialized = response.model_dump(by_alias=True)
    
    # Check that camelCase keys are present
    assert "sessionId" in serialized, "sessionId should be in camelCase"
    assert "turnCount" in serialized, "turnCount should be in camelCase"
    assert "chatHistory" in serialized, "chatHistory should be in camelCase"
    assert "safetyPassed" in serialized, "safetyPassed should be in camelCase"
    
    # Check that snake_case keys are NOT present
    assert "session_id" not in serialized, "session_id should not be present"
    assert "turn_count" not in serialized, "turn_count should not be present"
    assert "chat_history" not in serialized, "chat_history should not be present"
    assert "safety_passed" not in serialized, "safety_passed should not be present"
    
    # Verify values are correct
    assert serialized["sessionId"] == session_id
    assert serialized["turnCount"] == turn_count
    assert serialized["safetyPassed"] == safety_passed


def test_query_request_accepts_valid_query():
    """Test that QueryRequest accepts valid non-whitespace queries."""
    request = QueryRequest(
        sessionId="123e4567-e89b-12d3-a456-426614174000",
        query="Hello, how are you?",
    )
    assert request.query == "Hello, how are you?"
    assert request.session_id == "123e4567-e89b-12d3-a456-426614174000"


def test_query_request_accepts_camelcase_input():
    """Test that QueryRequest accepts camelCase field names."""
    request = QueryRequest(
        sessionId="123e4567-e89b-12d3-a456-426614174000",
        query="Test query",
        maxTurns=5,
    )
    assert request.max_turns == 5


# **Feature: message-api-refactor, Property 7: Forward Compatibility**
# **Validates: Requirements 3.5**
@given(
    session_id=st.uuids().map(str),
    query_text=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    unknown_field_name=st.text(
        min_size=1, 
        max_size=30, 
        alphabet=st.characters(whitelist_categories=('L',))
    ).filter(lambda x: x not in ['sessionId', 'query', 'pattern', 'maxTurns', 'metadata', 'session_id', 'max_turns']),
    unknown_field_value=st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.lists(st.text(max_size=20), max_size=5),
        st.dictionaries(st.text(max_size=10), st.text(max_size=20), max_size=3),
    ),
)
@settings(max_examples=100)
def test_forward_compatibility_ignores_unknown_fields(
    session_id: str,
    query_text: str,
    unknown_field_name: str,
    unknown_field_value: Any,
):
    """
    Test that QueryRequest ignores unknown fields for forward compatibility.
    
    For any valid QueryRequest with additional unknown fields, the request should
    be processed successfully, ignoring the extra fields.
    
    **Feature: message-api-refactor, Property 7: Forward Compatibility**
    **Validates: Requirements 3.5**
    """
    assume(query_text.strip())
    assume(unknown_field_name.strip())
    
    # Create request with unknown field
    request_data = {
        "sessionId": session_id,
        "query": query_text,
        unknown_field_name: unknown_field_value,
    }
    
    # Should not raise an error
    request = QueryRequest(**request_data)
    
    # Verify known fields are preserved
    assert request.session_id == session_id, "session_id should be preserved"
    assert request.query == query_text, "query should be preserved"
    
    # Verify unknown field is not accessible as an attribute
    assert not hasattr(request, unknown_field_name), \
        f"Unknown field '{unknown_field_name}' should not be accessible as attribute"


def test_query_request_ignores_unknown_fields():
    """Test forward compatibility - unknown fields are ignored."""
    request = QueryRequest(
        sessionId="123e4567-e89b-12d3-a456-426614174000",
        query="Test query",
        unknownField="should be ignored",
        anotherUnknown=123,
    )
    assert request.query == "Test query"
    # Unknown fields should not raise an error


def test_query_request_optional_pattern():
    """Test that pattern is optional and defaults to None."""
    request = QueryRequest(
        sessionId="123e4567-e89b-12d3-a456-426614174000",
        query="Test query",
    )
    assert request.pattern is None


def test_query_request_with_pattern():
    """Test that pattern can be set."""
    request = QueryRequest(
        sessionId="123e4567-e89b-12d3-a456-426614174000",
        query="Test query",
        pattern=ConversationPattern.TWO_AGENT,
    )
    assert request.pattern == ConversationPattern.TWO_AGENT


# **Feature: message-api-refactor, Property 8: Optional Parameters Default Behavior**
# **Validates: Requirements 5.2, 5.3**
@given(
    session_id=st.uuids().map(str),
    query_text=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    workflow_max_turns=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100)
def test_optional_parameters_default_behavior(
    session_id: str,
    query_text: str,
    workflow_max_turns: int,
):
    """
    Test that when pattern and maxTurns are not specified, workflow defaults are used.
    
    For any query request where `pattern` and `maxTurns` are not specified, the system
    should use the workflow's default configuration values for these parameters.
    
    **Feature: message-api-refactor, Property 8: Optional Parameters Default Behavior**
    **Validates: Requirements 5.2, 5.3**
    """
    assume(query_text.strip())
    
    # Create request without optional parameters
    request = QueryRequest(
        sessionId=session_id,
        query=query_text,
    )
    
    # Verify optional parameters default to None (meaning workflow defaults will be used)
    assert request.pattern is None, "pattern should default to None"
    assert request.max_turns is None, "max_turns should default to None"
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    # Mock the session manager to verify workflow defaults are used
    captured_max_turns = []
    
    async def capture_process_message(*args, **kwargs):
        # Capture the max_turns parameter passed to process_message
        captured_max_turns.append(kwargs.get("max_turns"))
        return {
            "session_id": UUID(session_id),
            "response": "Test response",
            "turn_count": 1,
            "chat_history": [],
            "summary": "",
            "safety_passed": True,
            "cost": {},
            "metadata": {},
        }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(side_effect=capture_process_message)
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id,
                    "query": query_text,
                    # Note: pattern and maxTurns are NOT provided
                },
            )
            
            # Verify the request was processed
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Verify that max_turns was passed as None to process_message
            # (meaning the session manager will use workflow defaults)
            assert len(captured_max_turns) == 1, "process_message should have been called once"
            assert captured_max_turns[0] is None, \
                f"max_turns should be None (to use workflow default), got {captured_max_turns[0]}"
            
        finally:
            app.dependency_overrides.clear()


# Fixtures for API endpoint tests
@pytest.fixture
def mock_current_user():
    """Create a mock authenticated user."""
    return CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )


@pytest.fixture
def client(mock_current_user):
    """Create test client with mocked authentication."""
    from src.api.auth import require_user, get_current_user
    
    # Override authentication dependencies
    app.dependency_overrides[require_user] = lambda: mock_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


# **Feature: message-api-refactor, Property 1: Valid Query Processing**
# **Validates: Requirements 1.1, 5.1**
@given(
    query_text=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    turn_count=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100)
def test_valid_query_processing(query_text: str, turn_count: int):
    """
    Test that valid queries are processed and return proper response structure.
    
    For any valid session ID and non-empty query string, sending a POST request
    to `/api/v1/sessions/query` should return a response with status 200 and a body
    containing `sessionId`, `response`, `turnCount`, `chatHistory`, `summary`, and
    `safetyPassed` fields.
    
    **Feature: message-api-refactor, Property 1: Valid Query Processing**
    **Validates: Requirements 1.1, 5.1**
    """
    # Skip queries that are only whitespace after filtering
    assume(query_text.strip())
    
    session_id = str(uuid4())
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    # Mock the session manager's process_message method
    mock_result = {
        "session_id": UUID(session_id),
        "response": f"Response to: {query_text[:50]}",
        "turn_count": turn_count,
        "chat_history": [
            {"role": "user", "content": query_text},
            {"role": "assistant", "content": f"Response to: {query_text[:50]}"},
        ],
        "summary": "Test summary",
        "safety_passed": True,
        "cost": {"tokens": 100},
        "metadata": {},
    }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(return_value=mock_result)
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id,
                    "query": query_text,
                },
            )
            
            # Verify response status
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Verify response structure (camelCase)
            data = response.json()
            assert "sessionId" in data, "Response should contain sessionId"
            assert "response" in data, "Response should contain response"
            assert "turnCount" in data, "Response should contain turnCount"
            assert "chatHistory" in data, "Response should contain chatHistory"
            assert "summary" in data, "Response should contain summary"
            assert "safetyPassed" in data, "Response should contain safetyPassed"
            
            # Verify values
            assert data["sessionId"] == session_id
            assert data["turnCount"] == turn_count
            assert data["safetyPassed"] is True
            
        finally:
            app.dependency_overrides.clear()


# **Feature: message-api-refactor, Property 2: Invalid Session Rejection**
# **Validates: Requirements 1.2**
@given(
    session_id=st.uuids().map(str),
    query_text=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
)
@settings(max_examples=100)
def test_invalid_session_rejection(session_id: str, query_text: str):
    """
    Test that queries with non-existent session IDs are rejected with 404.
    
    For any session ID that does not exist in the system, sending a query request
    should return a 404 status code with an error message.
    
    **Feature: message-api-refactor, Property 2: Invalid Session Rejection**
    **Validates: Requirements 1.2**
    """
    assume(query_text.strip())
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        # Simulate session not found error
        mock_session_manager.process_message = AsyncMock(
            side_effect=ValueError(f"Session not found: {session_id}")
        )
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id,
                    "query": query_text,
                },
            )
            
            # Verify 404 response for non-existent session
            assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
            
            # Verify error structure
            data = response.json()
            assert "detail" in data, "Response should contain error detail"
            detail = data["detail"]
            assert "error_code" in detail, "Error should have error_code"
            assert detail["error_code"] == "SESSION_NOT_FOUND"
            assert "error_message" in detail, "Error should have error_message"
            assert session_id in detail.get("session_id", ""), "Error should reference the session ID"
            
        finally:
            app.dependency_overrides.clear()


def test_invalid_uuid_format_returns_400():
    """Test that invalid UUID format returns 400 error."""
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    with patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": "not-a-valid-uuid",
                    "query": "Test query",
                },
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert data["detail"]["error_code"] == "INVALID_SESSION_ID"
            
        finally:
            app.dependency_overrides.clear()


def test_query_endpoint_requires_authentication():
    """Test that query endpoint requires authentication."""
    # Clear any overrides to test real auth behavior
    app.dependency_overrides.clear()
    
    with patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False), \
         patch("src.config.settings.get_settings") as mock_settings:
        # Set environment to production to require authentication
        mock_settings_obj = Mock()
        mock_settings_obj.app.environment = "production"
        mock_settings_obj.security.requests_per_minute = 60
        mock_settings_obj.security.requests_per_hour = 1000
        mock_settings.return_value = mock_settings_obj
        
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/sessions/query",
            json={
                "sessionId": str(uuid4()),
                "query": "Test query",
            },
        )
        
        # Should return 401 without authentication (or 500 if auth service unavailable)
        # In test environment, it may return 500 due to missing MongoDB
        assert response.status_code in [401, 500], f"Expected 401 or 500, got {response.status_code}"


# **Feature: message-api-refactor, Property 5: Token Preservation**
# **Validates: Requirements 2.3, 2.4**
@given(
    raw_token=st.text(min_size=10, max_size=500).filter(lambda x: x.strip() and not x.isspace()),
    username=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd'))).filter(lambda x: x.strip()),
    query_text=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
)
@settings(max_examples=100)
def test_token_preservation_in_tool_context(raw_token: str, username: str, query_text: str):
    """
    Test that raw JWT token is preserved and available in tool execution context.
    
    For any authenticated request, the `raw_token` field in the `CurrentUser` context
    should contain the complete JWT token as provided in the Authorization header,
    and this token should be available in the tool execution context.
    
    **Feature: message-api-refactor, Property 5: Token Preservation**
    **Validates: Requirements 2.3, 2.4**
    """
    from src.tools.context_utils import set_tool_execution_context, get_user_context_info, clear_tool_execution_context
    
    assume(raw_token.strip())
    assume(username.strip())
    assume(query_text.strip())
    
    session_id = str(uuid4())
    
    # Create mock user with the raw token
    mock_user = CurrentUser(
        user_id=uuid4(),
        username=username,
        role=UserRole.USER,
        roles=["user"],
        auth_method="keycloak",
        raw_token=raw_token,
    )
    
    # Verify CurrentUser stores the raw token correctly
    assert mock_user.raw_token == raw_token, "CurrentUser should store raw_token"
    
    # Simulate what the endpoint does: set tool execution context
    set_tool_execution_context(
        username=mock_user.username,
        roles=mock_user.roles,
        raw_token=mock_user.raw_token,
    )
    
    try:
        # Verify the token is retrievable from tool context
        context_info = get_user_context_info()
        
        assert context_info["raw_token"] == raw_token, \
            f"Tool context should preserve raw_token. Expected: {raw_token[:20]}..., Got: {context_info['raw_token'][:20] if context_info['raw_token'] else None}..."
        assert context_info["username"] == username, \
            f"Tool context should preserve username. Expected: {username}, Got: {context_info['username']}"
        assert context_info["roles"] == ["user"], \
            f"Tool context should preserve roles. Expected: ['user'], Got: {context_info['roles']}"
    finally:
        # Clean up
        clear_tool_execution_context()


def test_token_preservation_through_query_endpoint():
    """
    Test that raw token is passed through the query endpoint to tool execution context.
    
    This test verifies the complete flow: CurrentUser.raw_token -> set_tool_execution_context -> get_user_context_info
    
    **Feature: message-api-refactor, Property 5: Token Preservation**
    **Validates: Requirements 2.3, 2.4**
    """
    from src.tools.context_utils import get_user_context_info
    
    test_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test_payload.signature"
    session_id = str(uuid4())
    captured_context = {}
    
    # Create mock user with the raw token
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user", "admin"],
        auth_method="keycloak",
        raw_token=test_token,
    )
    
    # Mock the session manager to capture the context during execution
    async def capture_context_process_message(*args, **kwargs):
        # Capture the tool context at the time of processing
        captured_context.update(get_user_context_info())
        return {
            "session_id": UUID(session_id),
            "response": "Test response",
            "turn_count": 1,
            "chat_history": [],
            "summary": "",
            "safety_passed": True,
            "cost": {},
            "metadata": {},
        }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(side_effect=capture_context_process_message)
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id,
                    "query": "Test query",
                },
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Verify the token was available in the tool context during processing
            assert captured_context.get("raw_token") == test_token, \
                f"Raw token should be preserved in tool context. Expected: {test_token[:30]}..., Got: {captured_context.get('raw_token', 'None')[:30] if captured_context.get('raw_token') else 'None'}..."
            assert captured_context.get("username") == "test_user", \
                f"Username should be preserved. Expected: test_user, Got: {captured_context.get('username')}"
            assert captured_context.get("roles") == ["user", "admin"], \
                f"Roles should be preserved. Expected: ['user', 'admin'], Got: {captured_context.get('roles')}"
            
        finally:
            app.dependency_overrides.clear()


def test_token_preservation_in_messages_endpoint():
    """
    Test that raw token is also preserved in the existing messages endpoint.
    
    This ensures backward compatibility - both endpoints should preserve the token.
    
    **Feature: message-api-refactor, Property 5: Token Preservation**
    **Validates: Requirements 2.3, 2.4**
    """
    from src.tools.context_utils import get_user_context_info
    
    test_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.messages_endpoint_test.signature"
    session_id = uuid4()
    captured_context = {}
    
    # Create mock user with the raw token
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="messages_test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="keycloak",
        raw_token=test_token,
    )
    
    # Mock the session manager to capture the context during execution
    async def capture_context_process_message(*args, **kwargs):
        captured_context.update(get_user_context_info())
        return {
            "session_id": session_id,
            "response": "Test response",
            "turn_count": 1,
            "chat_history": [],
            "summary": "",
            "safety_passed": True,
            "cost": {},
            "metadata": {},
        }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(side_effect=capture_context_process_message)
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "message": "Test message",
                },
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Verify the token was available in the tool context during processing
            assert captured_context.get("raw_token") == test_token, \
                f"Raw token should be preserved in messages endpoint. Expected: {test_token[:30]}..., Got: {captured_context.get('raw_token', 'None')[:30] if captured_context.get('raw_token') else 'None'}..."
            
        finally:
            app.dependency_overrides.clear()



# **Feature: message-api-refactor, Property 9: Fallback Response for Invalid Agent Output**
# **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6**
@given(
    invalid_response=st.one_of(
        st.just(""),  # Empty response
        st.just(None),  # Null response
        st.text(alphabet=" \t\n\r", min_size=1, max_size=50),  # Whitespace only
        st.just("Previous conversation context: some context here"),  # Context-only
        st.just("[Current message] User asked something"),  # Raw context pattern
        st.just("User: Hello\nAssistant: Hi"),  # Chat history pattern
        st.just("System: Internal processing"),  # System pattern
        st.just("[Context] Some internal context"),  # Context pattern
        st.just("[History] Previous messages"),  # History pattern
        st.just("Chat history: message1, message2"),  # Chat history prefix
        st.just("Conversation history: ..."),  # Conversation history prefix
    ),
    session_id=st.uuids().map(str),
    query_text=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
)
@settings(max_examples=100)
def test_fallback_response_for_invalid_agent_output(
    invalid_response: str,
    session_id: str,
    query_text: str,
):
    """
    Test that invalid agent outputs trigger fallback responses.
    
    For any workflow execution that produces an empty, null, or context-only response,
    the system should return a user-friendly fallback message and set `isFallback: true`
    in the response metadata.
    
    **Feature: message-api-refactor, Property 9: Fallback Response for Invalid Agent Output**
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6**
    """
    assume(query_text.strip())
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    # Mock the session manager to return invalid response
    mock_result = {
        "session_id": UUID(session_id),
        "response": invalid_response,
        "turn_count": 1,
        "chat_history": [],
        "summary": "",
        "safety_passed": True,
        "cost": {},
        "metadata": {},
    }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(return_value=mock_result)
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id,
                    "query": query_text,
                },
            )
            
            # Verify response status is still 200 (graceful handling)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            
            # Verify fallback response is returned
            expected_fallback = (
                "I apologize, but I was unable to process your request. "
                "Please try again or rephrase your question."
            )
            assert data["response"] == expected_fallback, \
                f"Expected fallback message, got: {data['response'][:100]}"
            
            # Verify metadata contains fallback flag
            assert data.get("metadata", {}).get("isFallback") is True, \
                f"Expected isFallback=True in metadata, got: {data.get('metadata')}"
            
            # Verify fallback reason is set
            assert "fallbackReason" in data.get("metadata", {}), \
                f"Expected fallbackReason in metadata, got: {data.get('metadata')}"
            
        finally:
            app.dependency_overrides.clear()


def test_valid_response_not_marked_as_fallback():
    """
    Test that valid responses are NOT marked as fallback.
    
    **Feature: message-api-refactor, Property 9: Fallback Response for Invalid Agent Output**
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6**
    """
    session_id = str(uuid4())
    valid_response = "Here is a helpful answer to your question about Python programming."
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    # Mock the session manager to return valid response
    mock_result = {
        "session_id": UUID(session_id),
        "response": valid_response,
        "turn_count": 1,
        "chat_history": [],
        "summary": "",
        "safety_passed": True,
        "cost": {},
        "metadata": {},
    }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(return_value=mock_result)
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id,
                    "query": "Tell me about Python",
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify original response is returned
            assert data["response"] == valid_response
            
            # Verify NOT marked as fallback
            assert data.get("metadata", {}).get("isFallback") is not True, \
                "Valid response should not be marked as fallback"
            
        finally:
            app.dependency_overrides.clear()


def test_fallback_in_messages_endpoint():
    """
    Test that fallback handling also works in the messages endpoint.
    
    **Feature: message-api-refactor, Property 9: Fallback Response for Invalid Agent Output**
    **Validates: Requirements 6.1**
    """
    session_id = uuid4()
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    # Mock the session manager to return empty response
    mock_result = {
        "session_id": session_id,
        "response": "",  # Empty response should trigger fallback
        "turn_count": 1,
        "chat_history": [],
        "summary": "",
        "safety_passed": True,
        "cost": {},
        "metadata": {},
    }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(return_value=mock_result)
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "message": "Test message",
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify fallback response is returned
            expected_fallback = (
                "I apologize, but I was unable to process your request. "
                "Please try again or rephrase your question."
            )
            assert data["response"] == expected_fallback
            
            # Verify metadata contains fallback flag
            assert data.get("metadata", {}).get("isFallback") is True
            
        finally:
            app.dependency_overrides.clear()



# **Feature: message-api-refactor, Property 10: Fallback Response Logging**
# **Validates: Requirements 6.5**
@given(
    invalid_response=st.one_of(
        st.just(""),  # Empty response
        st.text(alphabet=" \t\n\r", min_size=1, max_size=50),  # Whitespace only
        st.just("Previous conversation context: some context here"),  # Context-only
    ),
)
@settings(max_examples=100)
def test_fallback_response_logging(invalid_response: str):
    """
    Test that fallback responses are logged for debugging.
    
    For any response that triggers a fallback, the original failed response should
    be logged for debugging purposes while the user receives only the friendly
    fallback message.
    
    **Feature: message-api-refactor, Property 10: Fallback Response Logging**
    **Validates: Requirements 6.5**
    """
    from src.api.response_validator import ResponseValidator
    
    # Capture log calls
    with patch("src.api.response_validator.logger") as mock_logger:
        # Call get_fallback_response which should log
        result = ResponseValidator.get_fallback_response(
            original_response=invalid_response,
            reason="test_reason",
        )
        
        # Verify fallback message is returned
        assert result == ResponseValidator.DEFAULT_FALLBACK
        
        # Verify logging was called with warning level
        mock_logger.warning.assert_called_once()
        
        # Verify log contains original response info for debugging
        call_args = mock_logger.warning.call_args
        assert "Using fallback response" in call_args[0][0]
        
        # Verify log kwargs contain debugging info
        log_kwargs = call_args[1]
        assert "reason" in log_kwargs
        assert log_kwargs["reason"] == "test_reason"
        assert "original_response_length" in log_kwargs
        expected_length = len(invalid_response) if invalid_response else 0
        assert log_kwargs["original_response_length"] == expected_length
        
        # Verify original response preview is logged (for debugging)
        if invalid_response:
            assert "original_preview" in log_kwargs
            assert log_kwargs["original_preview"] == invalid_response[:100]


def test_fallback_logging_with_long_response():
    """
    Test that long responses are truncated in logs.
    
    **Feature: message-api-refactor, Property 10: Fallback Response Logging**
    **Validates: Requirements 6.5**
    """
    from src.api.response_validator import ResponseValidator
    
    # Create a long invalid response
    long_response = "Previous conversation context: " + "x" * 200
    
    with patch("src.api.response_validator.logger") as mock_logger:
        ResponseValidator.get_fallback_response(
            original_response=long_response,
            reason="long_response_test",
        )
        
        # Verify logging was called
        mock_logger.warning.assert_called_once()
        
        # Verify original_preview is truncated to 100 chars
        log_kwargs = mock_logger.warning.call_args[1]
        assert len(log_kwargs["original_preview"]) == 100


def test_fallback_logging_with_null_response():
    """
    Test that null responses are handled in logging.
    
    **Feature: message-api-refactor, Property 10: Fallback Response Logging**
    **Validates: Requirements 6.5**
    """
    from src.api.response_validator import ResponseValidator
    
    with patch("src.api.response_validator.logger") as mock_logger:
        ResponseValidator.get_fallback_response(
            original_response=None,
            reason="null_response",
        )
        
        # Verify logging was called
        mock_logger.warning.assert_called_once()
        
        # Verify null handling in log kwargs
        log_kwargs = mock_logger.warning.call_args[1]
        assert log_kwargs["original_response_length"] == 0
        assert log_kwargs["original_preview"] is None


def test_validate_and_get_response_logs_on_fallback():
    """
    Test that validate_and_get_response logs when fallback is used.
    
    **Feature: message-api-refactor, Property 10: Fallback Response Logging**
    **Validates: Requirements 6.5**
    """
    from src.api.response_validator import ResponseValidator
    
    with patch("src.api.response_validator.logger") as mock_logger:
        response, is_fallback, reason = ResponseValidator.validate_and_get_response(
            response="",  # Empty response triggers fallback
        )
        
        # Verify fallback was used
        assert is_fallback is True
        assert reason == "empty_response"
        
        # Verify logging was called
        mock_logger.warning.assert_called_once()


def test_validate_and_get_response_no_log_for_valid():
    """
    Test that validate_and_get_response does NOT log for valid responses.
    
    **Feature: message-api-refactor, Property 10: Fallback Response Logging**
    **Validates: Requirements 6.5**
    """
    from src.api.response_validator import ResponseValidator
    
    with patch("src.api.response_validator.logger") as mock_logger:
        response, is_fallback, reason = ResponseValidator.validate_and_get_response(
            response="This is a valid response to the user's question.",
        )
        
        # Verify no fallback was used
        assert is_fallback is False
        assert reason is None
        
        # Verify logging was NOT called
        mock_logger.warning.assert_not_called()


# **Feature: message-api-refactor, Property 4: Endpoint Equivalence**
# **Validates: Requirements 1.5**
@given(
    query_text=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    turn_count=st.integers(min_value=0, max_value=100),
    response_text=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
)
@settings(max_examples=100)
def test_endpoint_equivalence(query_text: str, turn_count: int, response_text: str):
    """
    Test that both endpoints produce equivalent responses for the same input.
    
    For any valid session ID and query, the response from `/api/v1/sessions/query`
    with `sessionId` in the body should be equivalent to the response from
    `/api/v1/sessions/{session_id}/messages` with the same parameters.
    
    **Feature: message-api-refactor, Property 4: Endpoint Equivalence**
    **Validates: Requirements 1.5**
    """
    assume(query_text.strip())
    assume(response_text.strip())
    
    session_id = uuid4()
    session_id_str = str(session_id)
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    # Create a consistent mock result that both endpoints will return
    mock_result = {
        "session_id": session_id,
        "response": response_text,
        "turn_count": turn_count,
        "chat_history": [
            {"role": "user", "content": query_text},
            {"role": "assistant", "content": response_text},
        ],
        "summary": "Test summary",
        "safety_passed": True,
        "cost": {"tokens": 100},
        "metadata": {},
    }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(return_value=mock_result.copy())
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            
            # Call the new query endpoint
            query_response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id_str,
                    "query": query_text,
                },
            )
            
            # Reset mock to ensure fresh call
            mock_session_manager.process_message = AsyncMock(return_value=mock_result.copy())
            
            # Call the existing messages endpoint
            messages_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "message": query_text,
                },
            )
            
            # Both should succeed
            assert query_response.status_code == 200, \
                f"Query endpoint failed: {query_response.status_code}: {query_response.text}"
            assert messages_response.status_code == 200, \
                f"Messages endpoint failed: {messages_response.status_code}: {messages_response.text}"
            
            query_data = query_response.json()
            messages_data = messages_response.json()
            
            # Verify equivalent response content
            assert query_data["response"] == messages_data["response"], \
                f"Response mismatch: query={query_data['response'][:50]}, messages={messages_data['response'][:50]}"
            
            assert query_data["turnCount"] == messages_data["turn_count"], \
                f"Turn count mismatch: query={query_data['turnCount']}, messages={messages_data['turn_count']}"
            
            assert query_data["safetyPassed"] == messages_data["safety_passed"], \
                f"Safety passed mismatch: query={query_data['safetyPassed']}, messages={messages_data['safety_passed']}"
            
            assert query_data["summary"] == messages_data["summary"], \
                f"Summary mismatch: query={query_data['summary']}, messages={messages_data['summary']}"
            
            # Verify chat history equivalence (content should match)
            assert len(query_data["chatHistory"]) == len(messages_data["chat_history"]), \
                f"Chat history length mismatch: query={len(query_data['chatHistory'])}, messages={len(messages_data['chat_history'])}"
            
        finally:
            app.dependency_overrides.clear()


def test_endpoint_equivalence_with_error_handling():
    """
    Test that both endpoints handle errors equivalently.
    
    When a session is not found, both endpoints should return appropriate error responses.
    
    **Feature: message-api-refactor, Property 4: Endpoint Equivalence**
    **Validates: Requirements 1.5**
    """
    session_id = uuid4()
    session_id_str = str(session_id)
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        # Simulate session not found error
        mock_session_manager.process_message = AsyncMock(
            side_effect=ValueError(f"Session not found: {session_id}")
        )
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            
            # Call the new query endpoint
            query_response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id_str,
                    "query": "Test query",
                },
            )
            
            # Call the existing messages endpoint
            messages_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "message": "Test query",
                },
            )
            
            # Both should return 404 for non-existent session
            assert query_response.status_code == 404, \
                f"Query endpoint should return 404, got {query_response.status_code}"
            assert messages_response.status_code == 404, \
                f"Messages endpoint should return 404, got {messages_response.status_code}"
            
        finally:
            app.dependency_overrides.clear()


def test_endpoint_equivalence_with_fallback():
    """
    Test that both endpoints apply fallback handling equivalently.
    
    When the agent returns an invalid response, both endpoints should return
    the same fallback message.
    
    **Feature: message-api-refactor, Property 4: Endpoint Equivalence**
    **Validates: Requirements 1.5**
    """
    session_id = uuid4()
    session_id_str = str(session_id)
    
    # Create mock user
    mock_user = CurrentUser(
        user_id=uuid4(),
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test_token_123",
    )
    
    # Mock result with empty response (should trigger fallback)
    mock_result = {
        "session_id": session_id,
        "response": "",  # Empty response triggers fallback
        "turn_count": 1,
        "chat_history": [],
        "summary": "",
        "safety_passed": True,
        "cost": {},
        "metadata": {},
    }
    
    with patch("src.api.routers.sessions.get_session_manager") as mock_get_sm, \
         patch("src.api.rate_limiting.RateLimitingMiddleware._is_rate_limited", return_value=False):
        mock_session_manager = Mock()
        mock_session_manager.process_message = AsyncMock(return_value=mock_result.copy())
        mock_get_sm.return_value = mock_session_manager
        
        # Override auth
        app.dependency_overrides[require_user] = lambda: mock_user
        
        try:
            client = TestClient(app)
            
            # Call the new query endpoint
            query_response = client.post(
                "/api/v1/sessions/query",
                json={
                    "sessionId": session_id_str,
                    "query": "Test query",
                },
            )
            
            # Reset mock
            mock_session_manager.process_message = AsyncMock(return_value=mock_result.copy())
            
            # Call the existing messages endpoint
            messages_response = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={
                    "message": "Test query",
                },
            )
            
            # Both should succeed with fallback
            assert query_response.status_code == 200
            assert messages_response.status_code == 200
            
            query_data = query_response.json()
            messages_data = messages_response.json()
            
            # Both should have the same fallback response
            expected_fallback = (
                "I apologize, but I was unable to process your request. "
                "Please try again or rephrase your question."
            )
            assert query_data["response"] == expected_fallback
            assert messages_data["response"] == expected_fallback
            
            # Both should have fallback flag in metadata
            assert query_data.get("metadata", {}).get("isFallback") is True
            assert messages_data.get("metadata", {}).get("isFallback") is True
            
        finally:
            app.dependency_overrides.clear()
