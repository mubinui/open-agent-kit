
"""API router for Library (Workflows, Agents, Tools) management."""

from uuid import UUID
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel

from src.infrastructure.database.config_store import ConfigStore
from src.config.settings import get_settings

router = APIRouter(prefix="/api/library", tags=["library"])

# --- Models ---

class LibraryItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    config: Dict[str, Any]

class LibraryItemCreate(LibraryItemBase):
    type: Optional[str] = None  # Required for agents/tools, not schemas

class LibraryItemResponse(LibraryItemBase):
    id: UUID
    type: Optional[str] = None 
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True

# --- Dependencies ---

def get_config_store() -> ConfigStore:
    settings = get_settings()
    return ConfigStore(database_url=settings.database_url)

# --- Endpoints ---

@router.get("/{item_type}", response_model=List[LibraryItemResponse])
def list_library_items(
    item_type: str,
    store: ConfigStore = Depends(get_config_store)
):
    """List all items of a specific type (workflow, agent, tool) in the library."""
    if item_type not in ["workflow", "agent", "tool"]:
         raise HTTPException(status_code=400, detail="Invalid item type. Must be 'workflow', 'agent', or 'tool'.")
    
    items = store.list_items(item_type)
    return items

@router.post("/{item_type}", response_model=LibraryItemResponse, status_code=status.HTTP_201_CREATED)
def create_library_item(
    item_type: str,
    item: LibraryItemCreate,
    store: ConfigStore = Depends(get_config_store)
):
    """Create a new item in the library."""
    if item_type not in ["workflow", "agent", "tool"]:
         raise HTTPException(status_code=400, detail="Invalid item type. Must be 'workflow', 'agent', or 'tool'.")
    
    # Extract extra args safely
    extra_args = {}
    if item_type in ["agent", "tool"]:
        if not item.type:
             raise HTTPException(status_code=400, detail=f"{item_type} requires a 'type' field.")
        extra_args["type"] = item.type
        
    created_item = store.create_item(
        item_type=item_type,
        name=item.name,
        description=item.description,
        config=item.config,
        **extra_args
    )
    return created_item

@router.get("/{item_type}/{item_id}", response_model=LibraryItemResponse)
def get_library_item(
    item_type: str,
    item_id: UUID,
    store: ConfigStore = Depends(get_config_store)
):
    """Get a specific library item by ID."""
    if item_type not in ["workflow", "agent", "tool"]:
         raise HTTPException(status_code=400, detail="Invalid item type.")
         
    item = store.get_item(item_type, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{item_type} not found")
    return item

@router.put("/{item_type}/{item_id}", response_model=LibraryItemResponse)
def update_library_item(
    item_type: str,
    item_id: UUID,
    updates: Dict[str, Any],
    store: ConfigStore = Depends(get_config_store)
):
    """Update a library item."""
    if item_type not in ["workflow", "agent", "tool"]:
         raise HTTPException(status_code=400, detail="Invalid item type.")
         
    updated_item =store.update_item(item_type, item_id, updates)
    if not updated_item:
        raise HTTPException(status_code=404, detail=f"{item_type} not found")
    return updated_item

@router.delete("/{item_type}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_library_item(
    item_type: str,
    item_id: UUID,
    store: ConfigStore = Depends(get_config_store)
):
    """Delete a library item."""
    if item_type not in ["workflow", "agent", "tool"]:
         raise HTTPException(status_code=400, detail="Invalid item type.")
         
    success = store.delete_item(item_type, item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"{item_type} not found")
