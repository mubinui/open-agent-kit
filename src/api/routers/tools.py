"""Tool management endpoints."""

import json
import inspect
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Request, status

from src.api.models import (
    ToolRegisterRequest,
    ToolResponse,
    ToolUpdateRequest,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from src.audit_logging import get_logger
from src.config.dependency_validation import DependencyError, get_validator
from src.config.tool_registry import get_tool_registry
from src.config.config_loader import get_config_loader

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


def _get_tools_config_path() -> Path:
    """Get the path to the tools configuration file."""
    return Path("configs") / "tools.json"


def _load_tools_config() -> dict:
    """Load tools configuration from file using config loader."""
    try:
        loader = get_config_loader()
        return loader.get_config("tools")
    except FileNotFoundError:
        return {"version": "1.0", "tools": []}


def _save_tools_config(config: dict) -> None:
    """Save tools configuration to file."""
    config_path = _get_tools_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    # Trigger reload in config loader
    try:
        loader = get_config_loader()
        loader._reload_single_file(config_path)
    except Exception as e:
        logger.warning(f"Failed to reload config in loader: {e}")


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def register_tool(
    request: Request,
    body: ToolRegisterRequest,
) -> ToolResponse:
    """
    Register a new tool.
    
    Args:
        request: FastAPI request object
        body: Tool registration request
        
    Returns:
        Registered tool information
        
    Requirements: 3.2, 4.1, 4.2
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Registering tool",
        request_id=request_id,
        tool_id=body.id,
    )
    
    try:
        # Load existing config
        config = _load_tools_config()
        
        # Check if tool already exists
        if any(t["id"] == body.id for t in config["tools"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tool already exists: {body.id}",
            )
        
        # Add new tool
        tool_dict = body.model_dump()
        config["tools"].append(tool_dict)
        
        # Save config
        _save_tools_config(config)
        
        # Register with tool registry if enabled
        if body.enabled:
            try:
                tool_registry = get_tool_registry()
                tool_registry.register_tool_from_entrypoint(
                    tool_id=body.id,
                    entrypoint=body.entrypoint,
                    name=body.name,
                    description=body.description,
                )
            except Exception as e:
                logger.warning(
                    "Failed to register tool with registry",
                    tool_id=body.id,
                    error=str(e),
                )
        
        logger.info(
            "Registered tool",
            request_id=request_id,
            tool_id=body.id,
        )
        
        return ToolResponse(**tool_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to register tool",
            request_id=request_id,
            tool_id=body.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register tool: {str(e)}",
        )


@router.get("", response_model=List[ToolResponse])
async def list_tools(
    request: Request,
) -> List[ToolResponse]:
    """
    List all registered tools.
    
    Args:
        request: FastAPI request object
        
    Returns:
        List of tool configurations
        
    Requirements: 3.2, 4.1, 4.2
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Listing tools",
        request_id=request_id,
    )
    
    try:
        config = _load_tools_config()
        return [ToolResponse(**tool) for tool in config["tools"]]
        
    except Exception as e:
        logger.error(
            "Failed to list tools",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    request: Request,
    tool_id: str,
) -> ToolResponse:
    """
    Get tool configuration by ID.
    
    Args:
        request: FastAPI request object
        tool_id: Tool identifier
        
    Returns:
        Tool configuration
        
    Requirements: 3.2, 4.1, 4.2
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Getting tool",
        request_id=request_id,
        tool_id=tool_id,
    )
    
    try:
        config = _load_tools_config()
        
        # Find tool
        tool = next((t for t in config["tools"] if t["id"] == tool_id), None)
        
        if tool is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_id}",
            )
        
        return ToolResponse(**tool)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get tool",
            request_id=request_id,
            tool_id=tool_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool: {str(e)}",
        )


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    request: Request,
    tool_id: str,
    body: ToolUpdateRequest,
) -> ToolResponse:
    """
    Update tool configuration.
    
    Args:
        request: FastAPI request object
        tool_id: Tool identifier
        body: Tool update request
        
    Returns:
        Updated tool configuration
        
    Requirements: 3.2, 4.1, 4.2
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Updating tool",
        request_id=request_id,
        tool_id=tool_id,
    )
    
    try:
        config = _load_tools_config()
        
        # Find tool
        tool_idx = next(
            (i for i, t in enumerate(config["tools"]) if t["id"] == tool_id),
            None
        )
        
        if tool_idx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_id}",
            )
        
        # Update tool
        tool = config["tools"][tool_idx]
        update_data = body.model_dump(exclude_unset=True)
        tool.update(update_data)
        
        # Save config
        _save_tools_config(config)
        
        # Reload tool registry if enabled status changed or entrypoint changed
        if "enabled" in update_data or "entrypoint" in update_data:
            try:
                tool_registry = get_tool_registry()
                tool_registry.reload_from_config()
            except Exception as e:
                logger.warning(
                    "Failed to reload tool registry",
                    error=str(e),
                )
        
        logger.info(
            "Updated tool",
            request_id=request_id,
            tool_id=tool_id,
        )
        
        return ToolResponse(**tool)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update tool",
            request_id=request_id,
            tool_id=tool_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {str(e)}",
        )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    request: Request,
    tool_id: str,
) -> None:
    """
    Delete tool configuration.
    
    Args:
        request: FastAPI request object
        tool_id: Tool identifier
        
    Requirements: 3.2, 4.1, 4.2
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Deleting tool",
        request_id=request_id,
        tool_id=tool_id,
    )
    
    try:
        config = _load_tools_config()
        
        # Check if tool exists
        if not any(t["id"] == tool_id for t in config["tools"]):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_id}",
            )
        
        # Check for dependencies before deletion
        validator = get_validator()
        try:
            validator.validate_tool_deletion(tool_id)
        except DependencyError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "type": "dependency_error",
                    "message": str(e),
                    "dependents": e.dependents,
                },
            )
        
        # Remove tool
        config["tools"] = [t for t in config["tools"] if t["id"] != tool_id]
        
        # Save config
        _save_tools_config(config)
        
        # Reload tool registry
        try:
            tool_registry = get_tool_registry()
            tool_registry.reload_from_config()
        except Exception as e:
            logger.warning(
                "Failed to reload tool registry",
                error=str(e),
            )
        
        logger.info(
            "Deleted tool",
            request_id=request_id,
            tool_id=tool_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete tool",
            request_id=request_id,
            tool_id=tool_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {str(e)}",
        )

@router.post("/{tool_id}/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: Request,
    tool_id: str,
    body: ToolExecutionRequest,
) -> ToolExecutionResponse:
    """
    Execute a tool directly.
    
    Args:
        request: FastAPI request object
        tool_id: Tool identifier
        body: Execution arguments
        
    Returns:
        Execution result
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Executing tool",
        request_id=request_id,
        tool_id=tool_id,
    )
    
    try:
        tool_registry = get_tool_registry()
        tool_def = tool_registry.get_tool(tool_id)
        
        if not tool_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_id}",
            )
            
        # Execute the tool function
        # Note: Context is already set by middleware if headers were provided
        if inspect.iscoroutinefunction(tool_def.function):
            result = await tool_def.function(**body.args)
        else:
            result = tool_def.function(**body.args)
            
        return ToolExecutionResponse(
            status="success",
            result=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Tool execution failed",
            request_id=request_id,
            tool_id=tool_id,
            error=str(e),
            exc_info=True,
        )
        return ToolExecutionResponse(
            status="error",
            result=None,
            error=str(e),
        )
