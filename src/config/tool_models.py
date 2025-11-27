"""Pydantic models for tool configuration validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Configuration for a tool."""

    id: str = Field(
        pattern=r"^[a-z0-9_]+$",
        description="Unique tool identifier"
    )
    name: str = Field(
        description="Function name for the tool"
    )
    description: str = Field(
        description="Description of what the tool does"
    )
    entrypoint: str = Field(
        description="Python entrypoint in format 'module.path:function_name'"
    )
    enabled: bool = Field(
        default=True,
        description="Whether the tool is enabled"
    )
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific settings"
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

    def validate_entrypoint(self) -> None:
        """Validate entrypoint format."""
        if ":" not in self.entrypoint:
            raise ValueError(
                f"Tool {self.id}: Invalid entrypoint format. "
                "Expected 'module.path:function_name'"
            )


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
