"""Workflow management endpoints."""

import json
from pathlib import Path
from typing import List, Set

from fastapi import APIRouter, HTTPException, Request, status

from src.api.models import (
    WorkflowCreateRequest,
    WorkflowResponse,
    WorkflowUpdateRequest,
    WorkflowValidationResponse,
)
from src.api.workflow_validation import validate_workflow
from src.audit_logging import get_logger
from src.config.dependency_validation import DependencyError, get_validator
from src.config.workflow_models import WorkflowConfig
from src.config.config_loader import get_config_loader

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


def _get_workflows_config_path() -> Path:
    """Get the path to the workflows configuration file."""
    return Path("configs") / "workflows.json"


def _load_workflows_config() -> dict:
    """Load workflows configuration from file using config loader."""
    try:
        loader = get_config_loader()
        return loader.get_config("workflows")
    except FileNotFoundError:
        return {"version": "1.0", "workflows": []}


def _save_workflows_config(config: dict) -> None:
    """Save workflows configuration to file."""
    config_path = _get_workflows_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    # Trigger reload in config loader
    try:
        loader = get_config_loader()
        loader._reload_single_file(config_path)
    except Exception as e:
        logger.warning(f"Failed to reload config in loader: {e}")


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: Request,
    body: WorkflowCreateRequest,
) -> WorkflowResponse:
    """
    Create a new workflow configuration.
    
    Args:
        request: FastAPI request object
        body: Workflow creation request
        
    Returns:
        Created workflow configuration
        
    Requirements: 1.1, 2.1
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Creating workflow",
        request_id=request_id,
        workflow_id=body.id,
    )
    
    try:
        # Load existing config
        config = _load_workflows_config()
        
        # Check if workflow already exists
        if any(w["id"] == body.id for w in config["workflows"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow already exists: {body.id}",
            )
        
        # Validate agent references
        workflow_dict = body.model_dump()
        workflow_config = WorkflowConfig(**workflow_dict)
        agent_ids = workflow_config.get_all_agent_ids()
        
        validator = get_validator()
        try:
            validator.validate_workflow_agent_references(body.id, agent_ids)
        except DependencyError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "type": "dependency_error",
                    "message": str(e),
                    "dependencies": {
                        "missing": e.missing,
                        "available": e.available,
                    },
                },
            )
        
        # Add new workflow
        config["workflows"].append(workflow_dict)
        
        # Save config
        _save_workflows_config(config)
        
        logger.info(
            "Created workflow",
            request_id=request_id,
            workflow_id=body.id,
        )
        
        return WorkflowResponse(**workflow_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create workflow",
            request_id=request_id,
            workflow_id=body.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}",
        )


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    request: Request,
) -> List[WorkflowResponse]:
    """
    List all workflow configurations.
    
    Args:
        request: FastAPI request object
        
    Returns:
        List of workflow configurations
        
    Requirements: 1.1, 2.1
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Listing workflows",
        request_id=request_id,
    )
    
    try:
        config = _load_workflows_config()
        return [WorkflowResponse(**workflow) for workflow in config["workflows"]]
        
    except Exception as e:
        logger.error(
            "Failed to list workflows",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}",
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    request: Request,
    workflow_id: str,
) -> WorkflowResponse:
    """
    Get workflow configuration by ID.
    
    Args:
        request: FastAPI request object
        workflow_id: Workflow identifier
        
    Returns:
        Workflow configuration
        
    Requirements: 1.1, 2.1
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Getting workflow",
        request_id=request_id,
        workflow_id=workflow_id,
    )
    
    try:
        config = _load_workflows_config()
        
        # Find workflow
        workflow = next((w for w in config["workflows"] if w["id"] == workflow_id), None)
        
        if workflow is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found: {workflow_id}",
            )
        
        return WorkflowResponse(**workflow)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get workflow",
            request_id=request_id,
            workflow_id=workflow_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}",
        )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    request: Request,
    workflow_id: str,
    body: WorkflowUpdateRequest,
) -> WorkflowResponse:
    """
    Update workflow configuration.
    
    Args:
        request: FastAPI request object
        workflow_id: Workflow identifier
        body: Workflow update request
        
    Returns:
        Updated workflow configuration
        
    Requirements: 1.1, 2.1
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Updating workflow",
        request_id=request_id,
        workflow_id=workflow_id,
    )
    
    try:
        config = _load_workflows_config()
        
        # Find workflow
        workflow_idx = next(
            (i for i, w in enumerate(config["workflows"]) if w["id"] == workflow_id),
            None
        )
        
        if workflow_idx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found: {workflow_id}",
            )
        
        # Update workflow
        workflow = config["workflows"][workflow_idx]
        update_data = body.model_dump(exclude_unset=True)
        workflow.update(update_data)
        
        # Validate agent references if workflow structure changed
        workflow_config = WorkflowConfig(**workflow)
        agent_ids = workflow_config.get_all_agent_ids()
        
        validator = get_validator()
        try:
            validator.validate_workflow_agent_references(workflow_id, agent_ids)
        except DependencyError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "type": "dependency_error",
                    "message": str(e),
                    "dependencies": {
                        "missing": e.missing,
                        "available": e.available,
                    },
                },
            )
        
        # Save config
        _save_workflows_config(config)
        
        logger.info(
            "Updated workflow",
            request_id=request_id,
            workflow_id=workflow_id,
        )
        
        return WorkflowResponse(**workflow)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update workflow",
            request_id=request_id,
            workflow_id=workflow_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}",
        )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    request: Request,
    workflow_id: str,
) -> None:
    """
    Delete workflow configuration.
    
    Args:
        request: FastAPI request object
        workflow_id: Workflow identifier
        
    Requirements: 1.1, 2.1
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Deleting workflow",
        request_id=request_id,
        workflow_id=workflow_id,
    )
    
    try:
        config = _load_workflows_config()
        
        # Find and remove workflow
        original_count = len(config["workflows"])
        config["workflows"] = [w for w in config["workflows"] if w["id"] != workflow_id]
        
        if len(config["workflows"]) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found: {workflow_id}",
            )
        
        # Save config
        _save_workflows_config(config)
        
        logger.info(
            "Deleted workflow",
            request_id=request_id,
            workflow_id=workflow_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete workflow",
            request_id=request_id,
            workflow_id=workflow_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {str(e)}",
        )
