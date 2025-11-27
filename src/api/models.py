"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.patterns.conversation_engine import ConversationPattern


# Session Models
class SessionCreateRequest(BaseModel):
    """Request to create a new session."""

    workflow_id: str = Field(description="ID of the workflow to use")
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SessionResponse(BaseModel):
    """Response containing session information."""

    session_id: UUID
    workflow_id: str
    user_id: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime
    turn_count: int
    metadata: dict[str, Any]


# Message Models
class MessageRequest(BaseModel):
    """Request to send a message in a session."""

    message: str = Field(description="The message content")
    pattern: ConversationPattern = Field(
        default=ConversationPattern.TWO_AGENT,
        description="Conversation pattern to use"
    )
    max_turns: Optional[int] = Field(default=None, description="Maximum conversation turns")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MessageResponse(BaseModel):
    """Response from processing a message."""

    session_id: UUID
    response: str
    turn_count: int
    cost: dict[str, Any]
    metadata: dict[str, Any]
    chat_history: list[dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    summary: str = Field(default="", description="Conversation summary")
    safety_passed: bool = Field(default=True, description="Content safety check result")


class ChatHistoryResponse(BaseModel):
    """Response containing chat history."""

    session_id: UUID
    messages: list[dict[str, Any]]
    agent_notes: list[dict[str, Any]]
    turn_count: int


# Agent Configuration Models
class AgentConfigCreateRequest(BaseModel):
    """Request to create an agent configuration."""

    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Unique agent identifier")
    type: str = Field(description="Agent type")
    name: str = Field(description="Agent display name (no spaces allowed)")
    system_message: Optional[str] = Field(default="You are a helpful AI assistant.")
    llm_config: Optional[dict[str, Any] | bool] = None
    human_input_mode: str = Field(default="NEVER")
    code_execution_config: Optional[dict[str, Any] | bool] = False
    tools: list[str] = Field(default_factory=list)
    max_consecutive_auto_reply: int = Field(default=10, ge=0)
    retrieve_config: Optional[dict[str, Any]] = None
    description: Optional[str] = None


class AgentConfigResponse(BaseModel):
    """Response containing agent configuration."""

    id: str
    type: str
    name: str
    system_message: Optional[str] = None
    llm_config: Optional[dict[str, Any] | bool] = None
    human_input_mode: str = "NEVER"
    code_execution_config: Optional[dict[str, Any] | bool] = False
    tools: list[str] = Field(default_factory=list)
    max_consecutive_auto_reply: int = 10
    retrieve_config: Optional[dict[str, Any]] = None
    description: Optional[str] = None


class AgentConfigUpdateRequest(BaseModel):
    """Request to update an agent configuration."""

    name: Optional[str] = None
    system_message: Optional[str] = None
    llm_config: Optional[dict[str, Any] | bool] = None
    human_input_mode: Optional[str] = None
    code_execution_config: Optional[dict[str, Any] | bool] = None
    tools: Optional[list[str]] = None
    max_consecutive_auto_reply: Optional[int] = None
    retrieve_config: Optional[dict[str, Any]] = None
    description: Optional[str] = None


# Tool Models
class ToolRegisterRequest(BaseModel):
    """Request to register a tool."""

    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Unique tool identifier")
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    entrypoint: str = Field(description="Python entrypoint (module.path:function)")
    enabled: bool = Field(default=True)
    settings: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """Response containing tool information."""

    id: str
    name: str
    description: str
    entrypoint: str
    enabled: bool
    settings: dict[str, Any]


class ToolUpdateRequest(BaseModel):
    """Request to update a tool."""

    name: Optional[str] = None
    description: Optional[str] = None
    entrypoint: Optional[str] = None
    enabled: Optional[bool] = None
    settings: Optional[dict[str, Any]] = None


# Workflow Models
class WorkflowStepConfig(BaseModel):
    """Configuration for a workflow step."""

    sender_id: str
    recipient_id: str
    message: Optional[str] = None
    max_turns: int = 10
    summary_method: str = "last_msg"


class GroupChatConfigModel(BaseModel):
    """Configuration for group chat."""

    agents: list[str]
    max_round: int = 10
    speaker_selection_method: str = "auto"
    allowed_transitions: Optional[dict[str, list[str]]] = None
    send_introductions: bool = False


class WorkflowNodePosition(BaseModel):
    """Position of a node in the visual workflow builder."""

    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate")


class WorkflowNode(BaseModel):
    """Node in a visual workflow."""

    id: str = Field(description="Unique node identifier")
    agent_id: str = Field(description="ID of the agent this node represents")
    position: WorkflowNodePosition = Field(description="Position in the canvas")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node-specific configuration")


class WorkflowConnection(BaseModel):
    """Connection between workflow nodes."""

    from_node: str = Field(description="Source node ID")
    to_node: str = Field(description="Target node ID")
    type: str = Field(description="Connection type: 'sequential' or 'parallel'")


class WorkflowCreateRequest(BaseModel):
    """Request to create a workflow."""

    id: str = Field(pattern=r"^[a-z0-9_-]+$", description="Unique workflow identifier")
    name: str = Field(description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    pattern: ConversationPattern = Field(description="Conversation pattern")
    entry_agent_id: str = Field(description="ID of the entry agent")
    recipient_agent_id: Optional[str] = Field(default=None, description="ID of recipient agent (for two_agent pattern)")
    max_turns: int = Field(default=10, ge=1, description="Maximum conversation turns")
    summary_method: str = Field(default="last_msg", description="Summary method")
    enabled: bool = Field(default=True, description="Whether workflow is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    workflow_type: str = Field(default="sequential", description="Workflow type")
    persistence: str = Field(default="postgres", description="Persistence mode")
    steps: Optional[list[WorkflowStepConfig]] = None
    group_chat: Optional[GroupChatConfigModel] = None
    nested_chats: Optional[List[dict]] = None
    nodes: Optional[List[WorkflowNode]] = Field(default=None, description="Visual workflow nodes")
    connections: Optional[List[WorkflowConnection]] = Field(default=None, description="Visual workflow connections")


class WorkflowResponse(BaseModel):
    """Response containing workflow information."""

    id: str
    name: str
    description: str
    pattern: ConversationPattern
    entry_agent_id: str
    recipient_agent_id: Optional[str] = None
    max_turns: Optional[int] = None
    summary_method: Optional[str] = None
    enabled: Optional[bool] = None
    steps: Optional[list[WorkflowStepConfig]] = None
    group_chat: Optional[GroupChatConfigModel] = None
    nested_chats: Optional[List[dict]] = None
    metadata: Optional[Dict[str, Any]] = None
    workflow_type: Optional[str] = None
    persistence: Optional[str] = None
    version: Optional[int] = None
    last_updated: Optional[str] = None
    nodes: Optional[List[WorkflowNode]] = None
    connections: Optional[List[WorkflowConnection]] = None


class WorkflowUpdateRequest(BaseModel):
    """Request to update a workflow."""

    name: Optional[str] = None
    description: Optional[str] = None
    pattern: Optional[ConversationPattern] = None
    entry_agent_id: Optional[str] = None
    steps: Optional[list[WorkflowStepConfig]] = None
    group_chat: Optional[GroupChatConfigModel] = None
    nodes: Optional[List[WorkflowNode]] = None
    connections: Optional[List[WorkflowConnection]] = None


class WorkflowValidationError(BaseModel):
    """Validation error details."""

    field: str = Field(description="Field that failed validation")
    message: str = Field(description="Error message")
    error_type: str = Field(description="Type of validation error")


class WorkflowValidationResponse(BaseModel):
    """Response from workflow validation."""

    valid: bool = Field(description="Whether the workflow is valid")
    errors: List[WorkflowValidationError] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")


# Error Response
class ErrorResponse(BaseModel):
    """Structured error response."""

    error_code: str
    error_message: str
    error_type: str
    request_id: UUID
    timestamp: float
    details: Optional[Any] = None


# Prompt Template Models
class PromptTemplateCreateRequest(BaseModel):
    """Request to create a prompt template."""

    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Unique prompt identifier")
    name: str = Field(description="Prompt display name")
    description: str = Field(description="Prompt description")
    template: str = Field(description="Prompt template text with {variable} placeholders")
    variables: List[str] = Field(default_factory=list, description="List of variable names")
    category: Optional[str] = Field(default=None, description="Optional category")


class PromptTemplateUpdateRequest(BaseModel):
    """Request to update a prompt template."""

    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    variables: Optional[List[str]] = None
    category: Optional[str] = None


class PromptTemplateResponse(BaseModel):
    """Response containing prompt template information."""

    id: str
    name: str
    description: str
    template: str
    variables: List[str]
    category: Optional[str] = None
    version: Optional[int] = None
    etag: Optional[str] = None
    last_updated: Optional[str] = None


class ConfigHistoryEntry(BaseModel):
    """Single configuration history entry."""

    version: int
    etag: str
    created_at: str
    updated_by: Optional[str]
    change_summary: Optional[str]
    config_data: dict[str, Any]


class ConfigHistoryResponse(BaseModel):
    """Response containing configuration history."""

    config_type: str
    config_id: str
    history: List[ConfigHistoryEntry]


# API Provider Models
class APIProviderCreateRequest(BaseModel):
    """Request to create an API provider."""

    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Unique provider identifier")
    name: str = Field(description="Provider display name")
    type: str = Field(description="Provider type (llm, tool, api)")
    description: str = Field(description="Provider description")
    base_url: Optional[str] = Field(default=None, description="Base URL for API")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class APIProviderUpdateRequest(BaseModel):
    """Request to update an API provider."""

    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class APIProviderResponse(BaseModel):
    """Response containing API provider information."""

    id: str
    name: str
    type: str
    description: str
    base_url: Optional[str] = None
    api_key_masked: Optional[str] = None
    enabled: bool
    config: Dict[str, Any] = {}
    models: Optional[List[Dict[str, Any]]] = None
    version: Optional[int] = None
    etag: Optional[str] = None
    last_updated: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    """Response from testing API provider connection."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


# Health Response
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
