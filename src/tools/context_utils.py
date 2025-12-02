"""Utilities for tool context management."""

import json
from typing import Dict, List, Optional

from src.api.context import get_request_user


def get_user_context_headers() -> Dict[str, str]:
    """
    Get headers containing current user context.
    
    Returns:
        Dict with x-client-ref and x-client-username headers if user context exists.
    """
    headers = {}
    current_user = get_request_user()
    
    if current_user:
        if current_user.username:
            headers["x-client-username"] = current_user.username
        
        if current_user.role:
            # Convert single role to list for x-client-ref
            headers["x-client-ref"] = json.dumps([current_user.role.value])
            
    return headers


def get_user_context_info() -> Dict[str, Optional[str | List[str]]]:
    """
    Get current user context information.
    
    Returns:
        Dict with username and roles.
    """
    current_user = get_request_user()
    
    if current_user:
        return {
            "username": current_user.username,
            "roles": [current_user.role.value] if current_user.role else [],
            "user_id": str(current_user.user_id) if current_user.user_id else None,
        }
    
    return {
        "username": None,
        "roles": [],
        "user_id": None,
    }
