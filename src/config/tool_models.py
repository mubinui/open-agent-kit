"""Pydantic models for tool configuration validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class ToolConfig(BaseModel):
    """Configuration for a tool.
    
    Supports two tool types:
    - function: Python function tools (requires entrypoint)
    - api: HTTP API tools (requires settings.api_url)
    """

    id: str = Field(
        pattern=r"^[a-z0-9_]+$",
        description="Unique tool identifier (lowercase alphanumeric and underscores only)"
    )
    name: str = Field(
        description="Function name for the tool"
    )
    description: str = Field(
        description="Description of what the tool does"
    )
    entrypoint: Optional[str] = Field(
        default=None,
        description="Python entrypoint in format 'module.path:function_name'. Required for function tools."
    )
    enabled: bool = Field(
        default=True,
        description="Whether the tool is enabled"
    )
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific settings. For API tools, must include 'type': 'api' and 'api_url'."
    )
    is_async: bool = Field(
        default=False,
        description="Whether the tool function is async (True) or sync (False). For v0.4 compatibility."
    )
    
    # Versioning and metadata fields
    version: int = Field(
        default=1,
        ge=1,
        description="Configuration version number"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last configuration update"
    )

    @model_validator(mode='after')
    def validate_tool_type(self) -> 'ToolConfig':
        """Validate tool configuration based on type."""
        tool_type = self.settings.get('type', 'function')
        
        if tool_type == 'api':
            # API tool validation
            api_url = self.settings.get('api_url')
            if not api_url:
                raise ValueError(
                    f"Tool '{self.id}': API tools require 'api_url' in settings. "
                    "Example: settings={'type': 'api', 'api_url': 'https://api.example.com/endpoint'}"
                )
            # Set default entrypoint for API tools if not provided
            if not self.entrypoint:
                self.entrypoint = "src.tools.api_tool_executor:execute_api_tool"
        else:
            # Function tool validation
            if not self.entrypoint:
                raise ValueError(
                    f"Tool '{self.id}': Function tools require 'entrypoint' field. "
                    "Example: entrypoint='src.tools.calculator:calculate'"
                )
        
        return self

    def validate_entrypoint(self) -> None:
        """Validate entrypoint format."""
        if self.entrypoint and ":" not in self.entrypoint:
            raise ValueError(
                f"Tool '{self.id}': Invalid entrypoint format '{self.entrypoint}'. "
                "Expected 'module.path:function_name' (e.g., 'src.tools.calculator:calculate')"
            )
    
    def is_api_tool(self) -> bool:
        """Check if this is an API tool."""
        return self.settings.get('type') == 'api'


class ToolsConfig(BaseModel):
    """Root configuration for tools."""

    version: str = Field(
        description="Configuration version"
    )
    tools: list[ToolConfig] = Field(
        description="List of tool configurations"
    )

    def get_tool(self, tool_id: str) -> Optional[ToolConfig]:
        """
        Get tool configuration by ID.

        Args:
            tool_id: Tool identifier

        Returns:
            ToolConfig or None if not found
        """
        return next((t for t in self.tools if t.id == tool_id), None)

    def get_enabled_tools(self) -> list[ToolConfig]:
        """
        Get all enabled tool configurations.

        Returns:
            List of enabled ToolConfig objects
        """
        return [t for t in self.tools if t.enabled]

    def validate_all(self) -> None:
        """Validate all tool configurations."""
        for tool in self.tools:
            tool.validate_entrypoint()
