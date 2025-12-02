"""Tool for calling external services (Service1, Service2) via agent workflows.

This module provides callable tools that agents can use to interact with
downstream microservices. The tools handle authentication (user tokens for
Service1, admin tokens for Service2) and request formatting.

Usage in agent workflows:
    - call_service1: For user-authenticated API calls
    - call_service2: For admin-authenticated API calls with user context headers
"""

import json
from typing import Any, Optional

import httpx
import structlog

from src.config.settings import get_settings
from src.tools.context_utils import get_user_context_info

logger = structlog.get_logger(__name__)


async def call_service1(
    endpoint: str,
    method: str = "POST",
    payload: Optional[dict[str, Any]] = None,
    auth_token: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """
    Call Service1 API with user authentication token.

    This tool is designed for making authenticated requests to Service1
    where the user's Keycloak token is forwarded directly.

    Args:
        endpoint: API endpoint path (e.g., "/call-service2")
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        payload: Request body as dictionary (optional)
        auth_token: Bearer token from Keycloak user auth
        headers: Additional headers to include

    Returns:
        dict with:
            - status_code: HTTP response status
            - success: Boolean indicating success (2xx status)
            - data: Response body (parsed JSON or text)
            - error: Error message if request failed

    Example:
        result = await call_service1(
            endpoint="/call-service2",
            method="POST",
            payload={"action": "test", "data": {"message": "Hello"}},
            auth_token="eyJhbGciOiJSUzI1NiIsInR5cCI6..."
        )
    """
    settings = get_settings()

    if not settings.external_services.service1_enabled:
        logger.warning("service1_disabled")
        return {
            "status_code": 503,
            "success": False,
            "data": None,
            "error": "Service1 is not enabled",
        }

    # Build full URL
    base_url = settings.external_services.service1_base_url.rstrip("/")
    api_path = settings.external_services.service1_api_path.rstrip("/")
    endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{base_url}{api_path}{endpoint_path}"

    # Build headers
    request_headers = {"Content-Type": "application/json"}
    if auth_token:
        request_headers["Authorization"] = f"Bearer {auth_token}"
    if headers:
        request_headers.update(headers)

    logger.info(
        "calling_service1",
        url=url,
        method=method,
        has_auth=bool(auth_token),
    )

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.service1_timeout
        ) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                json=payload if payload else None,
                headers=request_headers,
            )

            # Try to parse response as JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            success = 200 <= response.status_code < 300

            logger.info(
                "service1_response",
                status_code=response.status_code,
                success=success,
            )

            return {
                "status_code": response.status_code,
                "success": success,
                "data": response_data,
                "error": None if success else response_data,
            }

    except httpx.TimeoutException:
        logger.error("service1_timeout", url=url)
        return {
            "status_code": 504,
            "success": False,
            "data": None,
            "error": "Service1 request timed out",
        }
    except httpx.HTTPError as e:
        logger.error("service1_http_error", url=url, error=str(e))
        return {
            "status_code": 502,
            "success": False,
            "data": None,
            "error": f"Service1 request failed: {str(e)}",
        }
    except Exception as e:
        logger.error("service1_error", url=url, error=str(e), exc_info=True)
        return {
            "status_code": 500,
            "success": False,
            "data": None,
            "error": f"Unexpected error: {str(e)}",
        }


async def call_service2(
    endpoint: str,
    method: str = "POST",
    payload: Optional[dict[str, Any]] = None,
    roles: Optional[list[str]] = None,
    username: Optional[str] = None,
    admin_token: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """
    Call Service2 API with admin authentication and client context headers.

    This tool is designed for making admin-authenticated requests to Service2
    where the admin/service account token is used, but user context is passed
    via custom headers (x-client-ref for roles, x-client-username).

    Args:
        endpoint: API endpoint path (e.g., "/process")
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        payload: Request body as dictionary (optional)
        roles: Array of roles for x-client-ref header
        username: Username for x-client-username header
        admin_token: Admin Bearer token (if not provided, will be fetched)
        headers: Additional headers to include

    Returns:
        dict with:
            - status_code: HTTP response status
            - success: Boolean indicating success (2xx status)
            - data: Response body (parsed JSON or text)
            - error: Error message if request failed

    Example:
        result = await call_service2(
            endpoint="/process",
            method="POST",
            payload={"operation": "test"},
            roles=["user", "analyst"],
            username="testuser"
        )
    """
    settings = get_settings()

    # Resolve context from request if not provided
    if not username or not roles:
        context_info = get_user_context_info()
        if not username:
            username = context_info["username"]
        if not roles:
            roles = context_info["roles"]

    if not settings.external_services.service2_enabled:
        logger.warning("service2_disabled")
        return {
            "status_code": 503,
            "success": False,
            "data": None,
            "error": "Service2 is not enabled",
        }

    # Acquire admin token if not provided
    if not admin_token and settings.keycloak.enabled:
        from src.api.keycloak_auth import get_admin_token
        try:
            admin_token = await get_admin_token()
        except Exception as e:
            logger.error("failed_to_acquire_admin_token", error=str(e))
            return {
                "status_code": 503,
                "success": False,
                "data": None,
                "error": f"Failed to acquire admin token: {str(e)}",
            }

    # Build full URL
    base_url = settings.external_services.service2_base_url.rstrip("/")
    api_path = settings.external_services.service2_api_path.rstrip("/")
    endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{base_url}{api_path}{endpoint_path}"

    # Build headers
    request_headers = {"Content-Type": "application/json"}
    if admin_token:
        request_headers["Authorization"] = f"Bearer {admin_token}"
    if roles:
        request_headers["x-client-ref"] = json.dumps(roles)
    if username:
        request_headers["x-client-username"] = username
    if headers:
        request_headers.update(headers)

    logger.info(
        "calling_service2",
        url=url,
        method=method,
        has_admin_token=bool(admin_token),
        has_roles=bool(roles),
        username=username,
    )

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.service2_timeout
        ) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                json=payload if payload else None,
                headers=request_headers,
            )

            # Try to parse response as JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            success = 200 <= response.status_code < 300

            logger.info(
                "service2_response",
                status_code=response.status_code,
                success=success,
            )

            return {
                "status_code": response.status_code,
                "success": success,
                "data": response_data,
                "error": None if success else response_data,
            }

    except httpx.TimeoutException:
        logger.error("service2_timeout", url=url)
        return {
            "status_code": 504,
            "success": False,
            "data": None,
            "error": "Service2 request timed out",
        }
    except httpx.HTTPError as e:
        logger.error("service2_http_error", url=url, error=str(e))
        return {
            "status_code": 502,
            "success": False,
            "data": None,
            "error": f"Service2 request failed: {str(e)}",
        }
    except Exception as e:
        logger.error("service2_error", url=url, error=str(e), exc_info=True)
        return {
            "status_code": 500,
            "success": False,
            "data": None,
            "error": f"Unexpected error: {str(e)}",
        }


async def call_external_service(
    service_name: str,
    endpoint: str,
    method: str = "POST",
    payload: Optional[dict[str, Any]] = None,
    auth_token: Optional[str] = None,
    roles: Optional[list[str]] = None,
    username: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generic external service caller that routes to appropriate service.

    This is a convenience function that dispatches to call_service1 or
    call_service2 based on the service_name parameter.

    Args:
        service_name: Either "service1" or "service2"
        endpoint: API endpoint path
        method: HTTP method
        payload: Request body
        auth_token: User Bearer token (for service1)
        roles: Array of roles (for service2)
        username: Username (for service2)

    Returns:
        dict with status_code, success, data, error
    """
    service_name = service_name.lower()

    if service_name == "service1":
        return await call_service1(
            endpoint=endpoint,
            method=method,
            payload=payload,
            auth_token=auth_token,
        )
    elif service_name == "service2":
        return await call_service2(
            endpoint=endpoint,
            method=method,
            payload=payload,
            roles=roles,
            username=username,
        )
    else:
        return {
            "status_code": 400,
            "success": False,
            "data": None,
            "error": f"Unknown service: {service_name}. Use 'service1' or 'service2'",
        }
