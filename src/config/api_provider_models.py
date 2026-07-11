"""Pydantic models for API provider configuration."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class APIProviderCreateRequest(BaseModel):
    """Request to create an API provider."""

    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Unique provider identifier")
    name: str = Field(min_length=1, description="Provider display name")
    type: str = Field(description="Provider type (llm, tool, api)")
    description: str = Field(min_length=1, description="Provider description")
    base_url: Optional[str] = Field(default=None, description="Base URL for API")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate provider type."""
        valid_types = ["llm", "tool", "api"]
        if v not in valid_types:
            raise ValueError(f"Provider type must be one of: {', '.join(valid_types)}")
        return v


class APIProviderUpdateRequest(BaseModel):
    """Request to update an API provider."""

    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate provider type."""
        if v is None:
            return v
        valid_types = ["llm", "tool", "api"]
        if v not in valid_types:
            raise ValueError(f"Provider type must be one of: {', '.join(valid_types)}")
        return v


class APIProviderResponse(BaseModel):
    """Response containing API provider information."""

    id: str
    name: str
    type: str
    description: str
    base_url: Optional[str] = None
    api_key_masked: Optional[str] = None
    enabled: bool
    config: Dict[str, Any]
    version: Optional[int] = None
    etag: Optional[str] = None
    last_updated: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    """Response from testing API provider connection."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    """
    Mask API key showing only last 4 characters.
    
    Args:
        api_key: API key to mask
        
    Returns:
        Masked API key or None if input is None
    """
    if api_key is None or len(api_key) == 0:
        return None
    
    if len(api_key) <= 4:
        return "*" * len(api_key)
    
    return "*" * (len(api_key) - 4) + api_key[-4:]
