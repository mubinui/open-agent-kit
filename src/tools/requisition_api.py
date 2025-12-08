"""Tool for calling the Requisition API.

This module provides callable tools that agents can use to interact with
the Requisition service. 

Authentication Flow:
1. Frontend sends user JWT → Backend extracts username and roles
2. Backend gets admin token using client_credentials grant
3. Backend calls Requisition API with:
   - Authorization: Bearer <admin_token>
   - x-client-username: <extracted_username>
   - x-client-ref: <extracted_roles>
"""

import json
from typing import Any, Optional

import httpx
import structlog

from src.config.settings import get_settings
from src.tools.context_utils import get_user_context_info

logger = structlog.get_logger(__name__)

# Default configuration - can be overridden via environment
REQUISITION_API_BASE_URL = "http://10.42.65.155:8012"
REQUISITION_API_PATH = "/api/v1"
REQUISITION_API_TIMEOUT = 30


async def _get_admin_token() -> Optional[str]:
    """
    Get admin token using client_credentials grant from Keycloak.
    
    Returns:
        Admin access token string, or None if acquisition fails
    """
    settings = get_settings()
    
    if not settings.keycloak.enabled:
        logger.warning("keycloak_not_enabled_for_admin_token")
        return None
    
    if not settings.keycloak.admin_client_secret:
        logger.warning("admin_client_secret_not_configured")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            response = await client.post(
                settings.keycloak.token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.keycloak.admin_client_id,
                    "client_secret": settings.keycloak.admin_client_secret,
                },
            )
            response.raise_for_status()
            token_response = response.json()
            logger.info("admin_token_acquired_for_requisition_api", 
                       client_id=settings.keycloak.admin_client_id)
            return token_response["access_token"]
    except Exception as e:
        logger.error("failed_to_acquire_admin_token", error=str(e))
        return None


async def get_requisition(
    req_no: str,
    username: Optional[str] = None,
    roles: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Get requisition details by requisition number.

    This tool retrieves requisition information from the Requisition API
    using admin token (client_credentials) for Bearer authentication 
    and x-client headers for user context propagation.

    Flow:
    1. Extract username/roles from current user context (set by JWT middleware)
    2. Get admin token using client_credentials grant
    3. Call API with admin token + x-client-username + x-client-ref headers

    Args:
        req_no: The requisition number (e.g., "REQ20250010638")
        username: Username for x-client-username header (optional, uses context if not provided)
        roles: Roles for x-client-ref header (optional, uses context if not provided)

    Returns:
        dict with:
            - status_code: HTTP response status
            - success: Boolean indicating success (2xx status)
            - data: Requisition data (parsed JSON or text)
            - error: Error message if request failed

    Example:
        result = await get_requisition(
            req_no="REQ20250010638"
        )
        # username and roles are extracted from the incoming JWT automatically
    """
    settings = get_settings()

    # Resolve context from request if not provided
    # These come from the JWT that was sent by the frontend
    context_info = get_user_context_info()
    
    # Debug logging to trace context propagation
    logger.info(
        "get_requisition_context_debug",
        context_info=context_info,
        provided_username=username,
        provided_roles=roles,
    )
    
    if not username:
        username = context_info.get("username")
    if not roles:
        roles = context_info.get("roles")
    
    # Log resolved values
    logger.info(
        "get_requisition_resolved_context",
        resolved_username=username,
        resolved_roles=roles,
        roles_count=len(roles) if roles else 0,
    )

    # Get admin token for service-to-service authentication
    admin_token = await _get_admin_token()
    if not admin_token:
        logger.warning("proceeding_without_admin_token")

    # Build URL
    base_url = getattr(settings.external_services, 'requisition_base_url', REQUISITION_API_BASE_URL)
    api_path = getattr(settings.external_services, 'requisition_api_path', REQUISITION_API_PATH)
    url = f"{base_url.rstrip('/')}{api_path}/requisition"

    # Build headers
    request_headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    
    # Add admin Bearer token for service-to-service authentication
    if admin_token:
        request_headers["Authorization"] = f"Bearer {admin_token}"
    
    # Add client context headers (user info extracted from incoming JWT)
    if username:
        request_headers["x-client-username"] = username
    if roles:
        # x-client-ref should be comma-separated string
        if isinstance(roles, list):
            request_headers["x-client-ref"] = ",".join(roles)
        else:
            request_headers["x-client-ref"] = roles

    # Query parameters
    params = {"reqNo": req_no}

    timeout = getattr(settings.external_services, 'requisition_timeout', REQUISITION_API_TIMEOUT)

    logger.info(
        "calling_requisition_api",
        url=url,
        req_no=req_no,
        username=username,
        has_roles=bool(roles),
        has_admin_token=bool(admin_token),
    )

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            response = await client.get(
                url=url,
                params=params,
                headers=request_headers,
            )

            # Try to parse response as JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            success = 200 <= response.status_code < 300

            logger.info(
                "requisition_api_response",
                status_code=response.status_code,
                success=success,
                req_no=req_no,
            )

            return {
                "status_code": response.status_code,
                "success": success,
                "data": response_data,
                "error": None if success else response_data,
            }

    except httpx.TimeoutException:
        logger.error("requisition_api_timeout", url=url, req_no=req_no)
        return {
            "status_code": 504,
            "success": False,
            "data": None,
            "error": "Requisition API request timed out",
        }
    except httpx.HTTPError as e:
        logger.error("requisition_api_http_error", url=url, req_no=req_no, error=str(e))
        return {
            "status_code": 502,
            "success": False,
            "data": None,
            "error": f"Requisition API request failed: {str(e)}",
        }
    except Exception as e:
        logger.error("requisition_api_error", url=url, req_no=req_no, error=str(e), exc_info=True)
        return {
            "status_code": 500,
            "success": False,
            "data": None,
            "error": f"Unexpected error: {str(e)}",
        }


async def search_requisitions(
    query: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    username: Optional[str] = None,
    roles: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Search requisitions with optional filters.

    Uses admin token for service-to-service auth and x-client headers for user context.

    Args:
        query: Search query string
        status: Filter by status
        from_date: Filter from date (ISO format)
        to_date: Filter to date (ISO format)
        username: Username for x-client-username header
        roles: Roles for x-client-ref header

    Returns:
        dict with status_code, success, data, error
    """
    settings = get_settings()

    # Resolve context from request if not provided
    context_info = get_user_context_info()
    if not username:
        username = context_info.get("username")
    if not roles:
        roles = context_info.get("roles")

    # Get admin token for service-to-service authentication
    admin_token = await _get_admin_token()

    # Build URL
    base_url = getattr(settings.external_services, 'requisition_base_url', REQUISITION_API_BASE_URL)
    api_path = getattr(settings.external_services, 'requisition_api_path', REQUISITION_API_PATH)
    url = f"{base_url.rstrip('/')}{api_path}/requisition/search"

    # Build headers
    request_headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    
    # Add admin Bearer token
    if admin_token:
        request_headers["Authorization"] = f"Bearer {admin_token}"
    
    # Add client context headers
    if username:
        request_headers["x-client-username"] = username
    if roles:
        # x-client-ref should be comma-separated string
        if isinstance(roles, list):
            request_headers["x-client-ref"] = ",".join(roles)
        else:
            request_headers["x-client-ref"] = roles

    # Query parameters
    params = {}
    if query:
        params["query"] = query
    if status:
        params["status"] = status
    if from_date:
        params["fromDate"] = from_date
    if to_date:
        params["toDate"] = to_date

    timeout = getattr(settings.external_services, 'requisition_timeout', REQUISITION_API_TIMEOUT)

    logger.info(
        "searching_requisitions",
        url=url,
        params=params,
        username=username,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            response = await client.get(
                url=url,
                params=params,
                headers=request_headers,
            )

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            success = 200 <= response.status_code < 300

            return {
                "status_code": response.status_code,
                "success": success,
                "data": response_data,
                "error": None if success else response_data,
            }

    except httpx.TimeoutException:
        return {
            "status_code": 504,
            "success": False,
            "data": None,
            "error": "Requisition API search timed out",
        }
    except httpx.HTTPError as e:
        return {
            "status_code": 502,
            "success": False,
            "data": None,
            "error": f"Requisition API search failed: {str(e)}",
        }
    except Exception as e:
        return {
            "status_code": 500,
            "success": False,
            "data": None,
            "error": f"Unexpected error: {str(e)}",
        }
