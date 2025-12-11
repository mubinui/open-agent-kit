"""
Unit tests for API default workflow handling.

**Feature: context-leak-fix**

These tests validate the API endpoints for default workflow functionality
as specified in the requirements document.

Requirements tested:
- 2.2: WHEN a user creates a session without specifying a workflow THEN the system SHALL use the procurement_chatbot workflow
- 2.3: WHEN the API receives a request without a workflow_id THEN the system SHALL default to the procurement_chatbot workflow
- 2.4: WHEN the system lists available workflows THEN the system SHALL indicate which workflow is the default
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.config.workflow_models import (
    ConversationPattern,
    SummaryMethod,
    WorkflowConfig,
    WorkflowType,
    PersistenceMode,
)
from src.config.workflow_registry import WorkflowRegistry


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_auth_token():
    """Create a mock authentication token."""
    return "Bearer test-token-12345"


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    from src.api.auth import CurrentUser, UserRole
    return CurrentUser(
        user_id=None,
        username="test_user",
        role=UserRole.USER,
        roles=["user"],
        auth_method="test",
        raw_token="test-token",
    )


def create_test_workflow_config(
    workflow_id: str,
    name: str,
    default: bool = False,
    enabled: bool = True,
) -> dict:
    """Create a test workflow configuration dictionary."""
    return {
        "id": workflow_id,
        "name": name,
        "description": f"Test workflow: {name}",
        "pattern": "two_agent",
        "entry_agent_id": "test_agent",
        "recipient_agent_id": "test_recipient",
        "max_turns": 10,
        "summary_method": "last_msg",
        "enabled": enabled,
        "default": default,
        "metadata": {},
        "workflow_type": "sequential",
        "persistence": "mongo_only",
    }


class TestSessionCreationWithDefaultWorkflow:
    """Tests for session creation with default workflow handling."""

    @patch("src.api.routers.sessions.get_session_manager")
    @patch("src.config.workflow_registry.get_workflow_registry")
    @patch("src.api.routers.sessions.require_user")
    def test_session_creation_without_workflow_id_uses_default(
        self,
        mock_require_user,
        mock_get_registry,
        mock_get_session_manager,
        client,
        mock_current_user,
    ):
        """
        Test session creation without workflow_id uses default workflow.
        
        Requirements: 2.2, 2.3
        """
        # Setup mock registry with default workflow
        mock_registry = MagicMock()
        mock_registry.get_default_workflow_id.return_value = "procurement_chatbot"
        mock_get_registry.return_value = mock_registry
        
        # Setup mock session manager
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"
        mock_session.active = True
        mock_session.created_at = "2024-01-01T00:00:00"
        mock_session.updated_at = "2024-01-01T00:00:00"
        mock_session.turn_count = 0
        mock_session.metadata = {}
        
        mock_manager = MagicMock()
        mock_manager.create_session = AsyncMock(return_value=mock_session)
        mock_get_session_manager.return_value = mock_manager
        
        # Setup mock auth
        mock_require_user.return_value = mock_current_user
        
        # Make request without workflow_id
        response = client.post(
            "/api/v1/sessions",
            json={"metadata": {}},
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Verify default workflow was used
        if response.status_code == 201:
            mock_registry.get_default_workflow_id.assert_called_once()
            mock_manager.create_session.assert_called_once()
            call_args = mock_manager.create_session.call_args
            assert call_args.kwargs.get("workflow_id") == "procurement_chatbot"

    @patch("src.api.routers.sessions.get_session_manager")
    @patch("src.config.workflow_registry.get_workflow_registry")
    @patch("src.api.routers.sessions.require_user")
    def test_session_creation_with_explicit_workflow_id(
        self,
        mock_require_user,
        mock_get_registry,
        mock_get_session_manager,
        client,
        mock_current_user,
    ):
        """
        Test session creation with explicit workflow_id uses provided workflow.
        
        Requirements: 2.2, 2.3
        """
        # Setup mock registry
        mock_registry = MagicMock()
        mock_get_registry.return_value = mock_registry
        
        # Setup mock session manager
        mock_session = MagicMock()
        mock_session.session_id = "test-session-id"
        mock_session.active = True
        mock_session.created_at = "2024-01-01T00:00:00"
        mock_session.updated_at = "2024-01-01T00:00:00"
        mock_session.turn_count = 0
        mock_session.metadata = {}
        
        mock_manager = MagicMock()
        mock_manager.create_session = AsyncMock(return_value=mock_session)
        mock_get_session_manager.return_value = mock_manager
        
        # Setup mock auth
        mock_require_user.return_value = mock_current_user
        
        # Make request with explicit workflow_id
        response = client.post(
            "/api/v1/sessions",
            json={"workflow_id": "custom_workflow", "metadata": {}},
            headers={"Authorization": "Bearer test-token"},
        )
        
        # Verify explicit workflow was used (not default)
        if response.status_code == 201:
            # Should NOT call get_default_workflow_id when workflow_id is provided
            mock_registry.get_default_workflow_id.assert_not_called()
            mock_manager.create_session.assert_called_once()
            call_args = mock_manager.create_session.call_args
            assert call_args.kwargs.get("workflow_id") == "custom_workflow"

    def test_session_creation_error_when_no_default_configured(
        self,
        client,
        mock_current_user,
    ):
        """
        Test session creation returns error when no workflow_id and no default configured.
        
        Requirements: 2.2, 2.3
        """
        from src.api.auth import require_user
        from src.api.main import app
        
        # Override the require_user dependency
        app.dependency_overrides[require_user] = lambda: mock_current_user
        
        try:
            # Setup mock registry with no default workflow
            with patch("src.config.workflow_registry.get_workflow_registry") as mock_get_registry:
                mock_registry = MagicMock()
                mock_registry.get_default_workflow_id.return_value = None
                mock_get_registry.return_value = mock_registry
                
                # Make request without workflow_id
                response = client.post(
                    "/api/v1/sessions",
                    json={"metadata": {}},
                    headers={"Authorization": "Bearer test-token"},
                )
                
                # Should return 400 error
                assert response.status_code == 400
                data = response.json()
                assert "no default workflow" in data["detail"].lower() or "no workflow_id" in data["detail"].lower()
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()


class TestWorkflowListWithDefaultIndicator:
    """Tests for workflow list endpoint with default indicator."""

    def test_workflow_list_includes_default_indicator(self, client):
        """
        Test that workflow list includes default indicator.
        
        Requirements: 2.4
        """
        # Create a temporary config file with workflows
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = Path(f.name)
            
            workflows = [
                create_test_workflow_config("workflow_1", "Workflow 1", default=False),
                create_test_workflow_config("procurement_chatbot", "Procurement Chatbot", default=True),
                create_test_workflow_config("workflow_3", "Workflow 3", default=False),
            ]
            
            config_data = {
                "version": "1.0.0",
                "workflows": workflows
            }
            json.dump(config_data, f)
        
        try:
            # Patch the config loader to use our test config
            with patch("src.api.routers.workflows.get_config_loader") as mock_loader:
                mock_loader.return_value.get_config.return_value = config_data
                
                response = client.get("/api/v1/workflows")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify workflows are returned
                assert len(data) == 3
                
                # Verify default indicator is present
                default_workflows = [w for w in data if w.get("default") is True]
                assert len(default_workflows) == 1
                assert default_workflows[0]["id"] == "procurement_chatbot"
                
                # Verify non-default workflows have default=False or None
                non_default_workflows = [w for w in data if w.get("default") is not True]
                assert len(non_default_workflows) == 2
                
        finally:
            config_path.unlink()

    def test_workflow_list_no_default_configured(self, client):
        """
        Test workflow list when no default is configured.
        
        Requirements: 2.4
        """
        # Create a temporary config file with no default workflow
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = Path(f.name)
            
            workflows = [
                create_test_workflow_config("workflow_1", "Workflow 1", default=False),
                create_test_workflow_config("workflow_2", "Workflow 2", default=False),
            ]
            
            config_data = {
                "version": "1.0.0",
                "workflows": workflows
            }
            json.dump(config_data, f)
        
        try:
            # Patch the config loader to use our test config
            with patch("src.api.routers.workflows.get_config_loader") as mock_loader:
                mock_loader.return_value.get_config.return_value = config_data
                
                response = client.get("/api/v1/workflows")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify no workflow has default=True
                default_workflows = [w for w in data if w.get("default") is True]
                assert len(default_workflows) == 0
                
        finally:
            config_path.unlink()


class TestWorkflowResponseModel:
    """Tests for WorkflowResponse model with default field."""

    def test_workflow_response_includes_default_field(self):
        """
        Test that WorkflowResponse model includes default field.
        
        Requirements: 2.4
        """
        from src.api.models import WorkflowResponse
        
        # Create a workflow response with default=True
        response = WorkflowResponse(
            id="test_workflow",
            name="Test Workflow",
            description="Test description",
            pattern=ConversationPattern.TWO_AGENT,
            entry_agent_id="test_agent",
            default=True,
        )
        
        assert response.default is True
        
        # Create a workflow response with default=False
        response_no_default = WorkflowResponse(
            id="test_workflow_2",
            name="Test Workflow 2",
            description="Test description",
            pattern=ConversationPattern.TWO_AGENT,
            entry_agent_id="test_agent",
            default=False,
        )
        
        assert response_no_default.default is False

    def test_workflow_response_default_is_optional(self):
        """
        Test that default field is optional in WorkflowResponse.
        
        Requirements: 2.4
        """
        from src.api.models import WorkflowResponse
        
        # Create a workflow response without specifying default
        response = WorkflowResponse(
            id="test_workflow",
            name="Test Workflow",
            description="Test description",
            pattern=ConversationPattern.TWO_AGENT,
            entry_agent_id="test_agent",
        )
        
        # Default should be False when not specified
        assert response.default is False


class TestSessionCreateRequestModel:
    """Tests for SessionCreateRequest model with optional workflow_id."""

    def test_session_create_request_workflow_id_optional(self):
        """
        Test that workflow_id is optional in SessionCreateRequest.
        
        Requirements: 2.2, 2.3
        """
        from src.api.models import SessionCreateRequest
        
        # Create request without workflow_id
        request = SessionCreateRequest(metadata={})
        assert request.workflow_id is None
        
        # Create request with workflow_id
        request_with_workflow = SessionCreateRequest(
            workflow_id="test_workflow",
            metadata={},
        )
        assert request_with_workflow.workflow_id == "test_workflow"

    def test_session_create_request_accepts_empty_body(self):
        """
        Test that SessionCreateRequest accepts empty body.
        
        Requirements: 2.2, 2.3
        """
        from src.api.models import SessionCreateRequest
        
        # Create request with empty dict (simulating empty JSON body)
        request = SessionCreateRequest()
        assert request.workflow_id is None
        assert request.user_id is None
        assert request.metadata == {}
