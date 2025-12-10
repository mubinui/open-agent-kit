"""Session management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.auth import CurrentUser, get_current_user, require_user
from src.api.context import set_request_user
from src.api.models import (
    Chat,
    ChatHistoryResponse,
    ChatListResponse,
    MessageRequest,
    MessageResponse,
    SessionCreateRequest,
    SessionResponse,
    UserSessionsResponse,
)
from typing import List
from src.api.session_manager import get_session_manager
from src.audit_logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: Request,
    body: SessionCreateRequest,
    current_user: CurrentUser = Depends(require_user),
) -> SessionResponse:
    """
    Create a new conversation session.
    
    Args:
        request: FastAPI request object
        body: Session creation request
        
    Returns:
        Created session information
        
    Requirements: 1.1, 1.3
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Set request context
    set_request_user(current_user)
    
    logger.info(
        "Creating session",
        request_id=request_id,
        workflow_id=body.workflow_id,
        user_id=body.user_id,
    )
    
    try:
        session_manager = get_session_manager()
        session = await session_manager.create_session(
            workflow_id=body.workflow_id,
            user_id=body.user_id,
            metadata=body.metadata,
        )
        
        return SessionResponse(
            session_id=session.session_id,
            workflow_id=body.workflow_id,
            user_id=body.user_id,
            active=session.active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            turn_count=session.turn_count,
            metadata=session.metadata,
        )
        
    except Exception as e:
        logger.error(
            "Failed to create session",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    request: Request,
    user_id: str = None,
    active_only: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
) -> List[SessionResponse]:
    """
    List all sessions, optionally filtered by user.
    
    Args:
        request: FastAPI request object
        user_id: Optional user ID to filter sessions
        active_only: If True, only return active sessions
        
    Returns:
        List of sessions
        
    Requirements: 1.1, 1.3
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Listing sessions",
        request_id=request_id,
        user_id=user_id,
        active_only=active_only,
    )
    
    try:
        session_manager = get_session_manager()
        sessions = await session_manager.list_sessions(
            user_id=user_id,
            active_only=active_only,
        )
        
        return [
            SessionResponse(
                session_id=session.session_id,
                workflow_id=session.metadata.get("workflow_id", ""),
                user_id=session.metadata.get("user_id"),
                active=session.active,
                created_at=session.created_at,
                updated_at=session.updated_at,
                turn_count=session.turn_count,
                metadata=session.metadata,
            )
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(
            "Failed to list sessions",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.get("/chats", response_model=ChatListResponse)
async def get_user_chats(
    request: Request,
    user_id: str = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatListResponse:
    """
    Get all chats for a user in a simplified DTO format.
    
    Args:
        request: FastAPI request object
        user_id: Optional user ID (defaults to current user)
        
    Returns:
        List of Chat objects with id, title, messageCount, createdAt, updatedAt
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Use provided user_id or fall back to current user
    effective_user_id = user_id or current_user.username
    
    logger.info(
        "Getting user chats",
        request_id=request_id,
        user_id=effective_user_id,
    )
    
    try:
        session_manager = get_session_manager()
        sessions = await session_manager.list_sessions(
            user_id=effective_user_id,
            active_only=False,  # Get all chats, not just active
        )
        
        chats = []
        for session in sessions:
            # Generate title from first user message or workflow name
            title = session.metadata.get("title")
            if not title:
                # Try to get first user message as title
                if session.messages:
                    first_user_msg = next(
                        (m for m in session.messages if m.role.value == "user"),
                        None
                    )
                    if first_user_msg:
                        # Truncate to first 50 chars
                        title = first_user_msg.content[:50]
                        if len(first_user_msg.content) > 50:
                            title += "..."
                    else:
                        title = f"Chat {str(session.session_id)[:8]}"
                else:
                    workflow_id = session.metadata.get("workflow_id", "")
                    title = workflow_id.replace("_", " ").title() if workflow_id else f"Chat {str(session.session_id)[:8]}"
            
            chats.append(Chat(
                id=str(session.session_id),
                title=title,
                messageCount=len(session.messages),
                createdAt=session.created_at.isoformat(),
                updatedAt=session.updated_at.isoformat(),
            ))
        
        return ChatListResponse(
            chats=chats,
            total=len(chats),
        )
        
    except Exception as e:
        logger.error(
            "Failed to get user chats",
            request_id=request_id,
            user_id=effective_user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user chats: {str(e)}",
        )


@router.get("/user/{user_id}", response_model=UserSessionsResponse)
async def get_user_sessions(
    request: Request,
    user_id: str,
    active_only: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
) -> UserSessionsResponse:
    """
    Get all sessions for a specific user with their messages.
    
    Args:
        request: FastAPI request object
        user_id: User identifier
        active_only: If True, only return active sessions
        
    Returns:
        User sessions with message counts
        
    Requirements: 1.1, 1.3
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Getting user sessions",
        request_id=request_id,
        user_id=user_id,
        active_only=active_only,
    )
    
    try:
        session_manager = get_session_manager()
        sessions = await session_manager.list_sessions(
            user_id=user_id,
            active_only=active_only,
        )
        
        session_responses = [
            SessionResponse(
                session_id=session.session_id,
                workflow_id=session.metadata.get("workflow_id", ""),
                user_id=session.metadata.get("user_id"),
                active=session.active,
                created_at=session.created_at,
                updated_at=session.updated_at,
                turn_count=session.turn_count,
                metadata=session.metadata,
            )
            for session in sessions
        ]
        
        active_count = sum(1 for s in sessions if s.active)
        
        return UserSessionsResponse(
            user_id=user_id,
            sessions=session_responses,
            total_count=len(sessions),
            active_count=active_count,
        )
        
    except Exception as e:
        logger.error(
            "Failed to get user sessions",
            request_id=request_id,
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}",
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    request: Request,
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> SessionResponse:
    """
    Get session information by ID.
    
    Args:
        request: FastAPI request object
        session_id: Session identifier
        
    Returns:
        Session information
        
    Requirements: 1.1, 1.3
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Getting session",
        request_id=request_id,
        session_id=session_id,
    )
    
    try:
        session_manager = get_session_manager()
        session = await session_manager.get_session(session_id)
        
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )
        
        return SessionResponse(
            session_id=session.session_id,
            workflow_id=session.metadata.get("workflow_id", ""),
            user_id=session.metadata.get("user_id"),
            active=session.active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            turn_count=session.turn_count,
            metadata=session.metadata,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get session",
            request_id=request_id,
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}",
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    request: Request,
    session_id: UUID,
    current_user: CurrentUser = Depends(require_user),
) -> None:
    """
    End and delete a session.
    
    Args:
        request: FastAPI request object
        session_id: Session identifier
        
    Requirements: 1.1, 1.3
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Deleting session",
        request_id=request_id,
        session_id=session_id,
    )
    
    try:
        session_manager = get_session_manager()
        deleted = await session_manager.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete session",
            request_id=request_id,
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    request: Request,
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatHistoryResponse:
    """
    Get chat history for a session.
    
    Args:
        request: FastAPI request object
        session_id: Session identifier
        
    Returns:
        Chat history including messages and agent notes
        
    Requirements: 1.1, 1.3
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.info(
        "Getting chat history",
        request_id=request_id,
        session_id=session_id,
    )
    
    try:
        session_manager = get_session_manager()
        history = await session_manager.get_chat_history(session_id)
        
        return ChatHistoryResponse(**history)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Failed to get chat history",
            request_id=request_id,
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat history: {str(e)}",
        )


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    request: Request,
    session_id: UUID,
    body: MessageRequest,
    current_user: CurrentUser = Depends(require_user),
) -> MessageResponse:
    """
    Send a message to a session and get a response.
    
    Args:
        request: FastAPI request object
        session_id: Session identifier
        body: Message request
        
    Returns:
        Response from the agent conversation
        
    Requirements: 1.1, 1.3
    """
    from src.tools.context_utils import set_tool_execution_context, clear_tool_execution_context
    
    request_id = getattr(request.state, "request_id", None)
    
    # Set request context (ContextVar - for direct access)
    set_request_user(current_user)
    
    # Set tool execution context (thread-local - persists through agent execution)
    # This ensures tools like get_requisition can access user info
    set_tool_execution_context(
        username=current_user.username,
        roles=current_user.roles,
        raw_token=current_user.raw_token,
    )
    
    logger.info(
        "Sending message",
        request_id=request_id,
        session_id=session_id,
        pattern=body.pattern,
        username=current_user.username,
        has_roles=bool(current_user.roles),
        has_raw_token=bool(current_user.raw_token),
        roles=current_user.roles,
    )
    
    try:
        session_manager = get_session_manager()
        result = await session_manager.process_message(
            session_id=session_id,
            message=body.message,
            max_turns=body.max_turns,
            metadata=body.metadata,
        )
        
        # Ensure required fields have default values if null
        result.setdefault("cost", {})
        result.setdefault("metadata", {})
        result.setdefault("chat_history", [])
        result.setdefault("summary", "")
        result.setdefault("safety_passed", True)
        
        return MessageResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Failed to send message",
            request_id=request_id,
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        
        # Build detailed error response
        error_detail = {
            "error_code": "MESSAGE_PROCESSING_FAILED",
            "error_message": f"Failed to send message: {str(e)}",
            "error_type": type(e).__name__,
            "request_id": request_id,
            "session_id": str(session_id),
            "context": {
                "message_length": len(body.message),
                "pattern": body.pattern.value if body.pattern else None,
                "max_turns": body.max_turns,
            },
        }
        
        # Add specific error details if available
        if hasattr(e, '__dict__'):
            error_detail["details"] = {
                k: str(v) for k, v in e.__dict__.items()
                if not k.startswith('_')
            }
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )
    finally:
        # Clean up tool execution context
        clear_tool_execution_context()
