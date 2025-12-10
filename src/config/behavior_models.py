"""
AUTOGEN 0.2 RESEARCH:
- Feature needed: Agent behavior configuration and output validation
- Autogen provides: ConversableAgent with system_message, register_reply for custom handlers
- Using: ConversableAgent base class, register_reply for validation hooks
- Documentation: https://microsoft.github.io/autogen/0.2/docs/reference/agentchat/conversable_agent
- Decision: Autogen doesn't provide output format validation or behavior constraints.
  We need to implement custom validation as an extension using register_reply hooks.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class OutputFormatType(str, Enum):
    """Type of output format."""
    
    JSON = "json"
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"


class OutputFormatConfig(BaseModel):
    """Configuration for agent output format."""
    
    type: OutputFormatType = Field(
        description="Type of output format expected from the agent"
    )
    language: Optional[str] = Field(
        default=None,
        description="Programming language for code output (e.g., 'python', 'javascript')"
    )
    include_explanation: bool = Field(
        default=False,
        description="Whether to include explanation with the output"
    )
    format_template: Optional[str] = Field(
        default=None,
        description="Template for formatting output (supports {language}, {code}, {explanation} placeholders)"
    )
    json_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="JSON schema for validating JSON output"
    )
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v: Optional[str], info) -> Optional[str]:
        """Validate language is provided for code output."""
        output_type = info.data.get('type')
        if output_type == OutputFormatType.CODE and v is None:
            # Allow auto_detect as a special value
            return "auto_detect"
        return v


class ConstraintsConfig(BaseModel):
    """Configuration for agent output constraints."""
    
    max_output_length: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum length of output in characters"
    )
    min_output_length: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum length of output in characters"
    )
    require_language_specification: bool = Field(
        default=False,
        description="Whether to require language specification in code blocks"
    )
    forbidden_patterns: list[str] = Field(
        default_factory=list,
        description="List of regex patterns that are forbidden in output"
    )
    required_patterns: list[str] = Field(
        default_factory=list,
        description="List of regex patterns that must be present in output"
    )
    allowed_languages: Optional[list[str]] = Field(
        default=None,
        description="List of allowed programming languages for code output"
    )


class SecurityConfig(BaseModel):
    """Configuration for security checks on agent output."""
    
    syntax_check: bool = Field(
        default=False,
        description="Whether to perform syntax checking on code output"
    )
    security_scan: bool = Field(
        default=False,
        description="Whether to scan for security vulnerabilities in code"
    )
    dangerous_functions: list[str] = Field(
        default_factory=lambda: ["eval", "exec", "compile", "__import__"],
        description="List of dangerous function names to check for"
    )
    allow_file_operations: bool = Field(
        default=False,
        description="Whether to allow file operations in code"
    )
    allow_network_operations: bool = Field(
        default=False,
        description="Whether to allow network operations in code"
    )


class AgentBehaviorConfig(BaseModel):
    """Complete behavior configuration for an agent."""
    
    output_format: Optional[OutputFormatConfig] = Field(
        default=None,
        description="Output format configuration"
    )
    constraints: Optional[ConstraintsConfig] = Field(
        default=None,
        description="Output constraints configuration"
    )
    validation: Optional[SecurityConfig] = Field(
        default=None,
        description="Security and validation configuration"
    )
    
    def has_validation(self) -> bool:
        """Check if any validation is configured."""
        return (
            self.output_format is not None
            or self.constraints is not None
            or self.validation is not None
        )
