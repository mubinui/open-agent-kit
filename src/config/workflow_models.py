"""Pydantic models for workflow configuration validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ConversationPattern(str, Enum):
    """Type of conversation pattern."""

    TWO_AGENT = "two_agent"
    SEQUENTIAL = "sequential"
    GROUP_CHAT = "group_chat"
    NESTED = "nested"


class SpeakerSelectionMethod(str, Enum):
    """Speaker selection method for group chats."""

    AUTO = "auto"
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    MANUAL = "manual"


class SummaryMethod(str, Enum):
    """Method for generating conversation summaries."""

    LAST_MSG = "last_msg"
    REFLECTION_WITH_LLM = "reflection_with_llm"


class WorkflowType(str, Enum):
    """Type of workflow for classification and routing."""

    CHATBOT = "chatbot"
    SEQUENTIAL = "sequential"
    TREE = "tree"
    CUSTOM = "custom"


class PersistenceMode(str, Enum):
    """Persistence backend mode."""

    POSTGRES = "postgres"
    MONGO_ONLY = "mongo_only"


class WorkflowStep(BaseModel):
    """Configuration for a single step in a sequential workflow."""

    sender_id: str = Field(
        description="ID of the agent that initiates this conversation"
    )
    recipient_id: str = Field(
        description="ID of the agent that receives the message"
    )
    message: Optional[str] = Field(
        default=None,
        description="Initial message for this step (optional if using carryover)"
    )
    max_turns: int = Field(
        default=10,
        ge=1,
        description="Maximum number of conversation turns for this step"
    )
    summary_method: SummaryMethod = Field(
        default=SummaryMethod.LAST_MSG,
        description="Method for generating summary of this conversation"
    )
    carryover: bool = Field(
        default=True,
        description="Whether to carry over context from previous step"
    )
    clear_history: bool = Field(
        default=False,
        description="Whether to clear chat history before this step"
    )

    @field_validator('sender_id', 'recipient_id')
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Validate agent ID format."""
        if not v or not v.strip():
            raise ValueError("Agent ID cannot be empty")
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError(
                f"Agent ID '{v}' must contain only alphanumeric characters, "
                "underscores, and hyphens"
            )
        return v


class GroupChatConfig(BaseModel):
    """Configuration for a group chat workflow."""

    agents: list[str] = Field(
        min_length=2,
        description="List of agent IDs participating in the group chat"
    )
    max_round: int = Field(
        default=10,
        ge=1,
        description="Maximum number of conversation rounds"
    )
    speaker_selection_method: SpeakerSelectionMethod = Field(
        default=SpeakerSelectionMethod.AUTO,
        description="Method for selecting the next speaker"
    )
    allowed_transitions: Optional[dict[str, list[str]]] = Field(
        default=None,
        description="Dictionary mapping agent IDs to lists of agent IDs they can transition to"
    )
    speaker_transitions_type: Optional[str] = Field(
        default=None,
        description="Type of transitions: 'allowed' or 'disallowed'"
    )
    send_introductions: bool = Field(
        default=False,
        description="Whether agents should introduce themselves at the start"
    )
    admin_name: str = Field(
        default="GroupChatManager",
        description="Name for the GroupChatManager agent"
    )
    select_speaker_message_template: Optional[str] = Field(
        default=None,
        description="Custom template for speaker selection prompt"
    )
    select_speaker_auto_verbose: bool = Field(
        default=False,
        description="Whether to show verbose output during speaker selection"
    )

    @field_validator('agents')
    @classmethod
    def validate_agents(cls, v: list[str]) -> list[str]:
        """Validate agent list."""
        if len(v) < 2:
            raise ValueError("Group chat requires at least 2 agents")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Agent IDs must be unique in group chat")
        
        # Validate each agent ID
        for agent_id in v:
            if not agent_id or not agent_id.strip():
                raise ValueError("Agent ID cannot be empty")
            if not agent_id.replace('_', '').replace('-', '').isalnum():
                raise ValueError(
                    f"Agent ID '{agent_id}' must contain only alphanumeric characters, "
                    "underscores, and hyphens"
                )
        
        return v

    @field_validator('speaker_transitions_type')
    @classmethod
    def validate_transitions_type(cls, v: Optional[str], info) -> Optional[str]:
        """Validate speaker transitions type."""
        if v is not None and v not in ['allowed', 'disallowed']:
            raise ValueError("speaker_transitions_type must be 'allowed' or 'disallowed'")
        
        # If allowed_transitions is set, speaker_transitions_type should be set
        allowed_transitions = info.data.get('allowed_transitions')
        if allowed_transitions is not None and v is None:
            return 'allowed'  # Default to 'allowed'
        
        return v


class NestedChatConfig(BaseModel):
    """Configuration for a nested chat trigger."""

    trigger_agent_id: str = Field(
        description="ID of the agent that will trigger nested chats"
    )
    nested_chats: list[dict[str, Any]] = Field(
        description="List of nested chat configurations"
    )
    trigger_condition: Optional[str] = Field(
        default=None,
        description="String to match in messages to trigger nested chat (None = always trigger)"
    )
    position: int = Field(
        default=2,
        ge=0,
        description="Position in reply sequence where nested chat executes"
    )


class WorkflowConfig(BaseModel):
    """Configuration for a complete workflow."""

    id: str = Field(
        pattern=r"^[a-z0-9_-]+$",
        description="Unique workflow identifier"
    )
    name: str = Field(
        description="Human-readable workflow name"
    )
    description: str = Field(
        description="Description of what this workflow does"
    )
    pattern: ConversationPattern = Field(
        description="Type of conversation pattern to use"
    )
    entry_agent_id: str = Field(
        description="ID of the agent that starts the workflow"
    )
    
    # Pattern-specific configurations
    steps: Optional[list[WorkflowStep]] = Field(
        default=None,
        description="Steps for sequential workflow (required for SEQUENTIAL pattern)"
    )
    group_chat: Optional[GroupChatConfig] = Field(
        default=None,
        description="Group chat configuration (required for GROUP_CHAT pattern)"
    )
    nested_chats: Optional[list[NestedChatConfig]] = Field(
        default=None,
        description="Nested chat configurations (required for NESTED pattern)"
    )
    
    # Two-agent pattern configuration
    recipient_agent_id: Optional[str] = Field(
        default=None,
        description="ID of recipient agent (required for TWO_AGENT pattern)"
    )
    max_turns: int = Field(
        default=10,
        ge=1,
        description="Maximum conversation turns (for TWO_AGENT pattern)"
    )
    summary_method: SummaryMethod = Field(
        default=SummaryMethod.LAST_MSG,
        description="Summary method (for TWO_AGENT pattern)"
    )
    
    # Common settings
    enabled: bool = Field(
        default=True,
        description="Whether this workflow is enabled"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional workflow metadata"
    )
    
    # Persistence configuration (Requirement 16.4, 17.2, 17.3)
    persistence: PersistenceMode = Field(
        default=PersistenceMode.POSTGRES,
        description="Persistence backend: 'postgres' or 'mongo_only'"
    )
    workflow_type: WorkflowType = Field(
        default=WorkflowType.SEQUENTIAL,
        description="Workflow type: 'chatbot', 'sequential', 'tree', or 'custom'"
    )
    
    # Versioning and metadata fields (Requirement 17.1, 17.2)
    version: int = Field(
        default=1,
        ge=1,
        description="Configuration version number"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last configuration update"
    )

    @field_validator('persistence')
    @classmethod
    def validate_persistence(cls, v: PersistenceMode, info) -> PersistenceMode:
        """Validate persistence mode and enforce mongo_only for chatbot workflows."""
        # Enforce mongo_only for chatbot workflows
        workflow_type = info.data.get('workflow_type')
        if workflow_type == WorkflowType.CHATBOT and v != PersistenceMode.MONGO_ONLY:
            raise ValueError("Chatbot workflows must use mongo_only persistence")
        
        return v
    
    @field_validator('workflow_type')
    @classmethod
    def validate_workflow_type(cls, v: WorkflowType) -> WorkflowType:
        """Validate workflow_type enum value."""
        if v not in WorkflowType:
            raise ValueError(
                f"workflow_type must be one of {[t.value for t in WorkflowType]}, got '{v}'"
            )
        return v

    def validate_pattern_config(self) -> None:
        """
        Validate that required configuration is present for the selected pattern.
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if self.pattern == ConversationPattern.TWO_AGENT:
            if not self.recipient_agent_id:
                raise ValueError(
                    f"Workflow {self.id}: TWO_AGENT pattern requires recipient_agent_id"
                )
        
        elif self.pattern == ConversationPattern.SEQUENTIAL:
            if not self.steps or len(self.steps) == 0:
                raise ValueError(
                    f"Workflow {self.id}: SEQUENTIAL pattern requires at least one step"
                )
        
        elif self.pattern == ConversationPattern.GROUP_CHAT:
            if not self.group_chat:
                raise ValueError(
                    f"Workflow {self.id}: GROUP_CHAT pattern requires group_chat configuration"
                )
            
            # Validate that entry_agent_id is in the group
            if self.entry_agent_id not in self.group_chat.agents:
                raise ValueError(
                    f"Workflow {self.id}: entry_agent_id '{self.entry_agent_id}' "
                    f"must be in group_chat.agents"
                )
        
        elif self.pattern == ConversationPattern.NESTED:
            if not self.nested_chats or len(self.nested_chats) == 0:
                raise ValueError(
                    f"Workflow {self.id}: NESTED pattern requires at least one nested chat"
                )

    def get_all_agent_ids(self) -> set[str]:
        """
        Get all agent IDs referenced in this workflow.
        
        Returns:
            Set of agent IDs used in the workflow
        """
        agent_ids = {self.entry_agent_id}
        
        if self.pattern == ConversationPattern.TWO_AGENT:
            if self.recipient_agent_id:
                agent_ids.add(self.recipient_agent_id)
        
        elif self.pattern == ConversationPattern.SEQUENTIAL:
            if self.steps:
                for step in self.steps:
                    agent_ids.add(step.sender_id)
                    agent_ids.add(step.recipient_id)
        
        elif self.pattern == ConversationPattern.GROUP_CHAT:
            if self.group_chat:
                agent_ids.update(self.group_chat.agents)
        
        elif self.pattern == ConversationPattern.NESTED:
            if self.nested_chats:
                for nested_chat in self.nested_chats:
                    agent_ids.add(nested_chat.trigger_agent_id)
        
        return agent_ids


class WorkflowsConfig(BaseModel):
    """Root configuration for workflows."""

    version: str = Field(
        description="Configuration version"
    )
    workflows: list[WorkflowConfig] = Field(
        description="List of workflow configurations"
    )

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """
        Get workflow configuration by ID.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            WorkflowConfig or None if not found
        """
        return next((w for w in self.workflows if w.id == workflow_id), None)

    def get_enabled_workflows(self) -> list[WorkflowConfig]:
        """
        Get all enabled workflow configurations.
        
        Returns:
            List of enabled WorkflowConfig objects
        """
        return [w for w in self.workflows if w.enabled]

    def validate_all(self) -> None:
        """
        Validate all workflow configurations.
        
        Raises:
            ValueError: If any workflow configuration is invalid
        """
        # Check for duplicate IDs
        workflow_ids = [w.id for w in self.workflows]
        if len(workflow_ids) != len(set(workflow_ids)):
            duplicates = [wid for wid in workflow_ids if workflow_ids.count(wid) > 1]
            raise ValueError(f"Duplicate workflow IDs found: {set(duplicates)}")
        
        # Validate each workflow
        for workflow in self.workflows:
            workflow.validate_pattern_config()
