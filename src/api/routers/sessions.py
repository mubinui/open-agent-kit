"""Session management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.auth import CurrentUser, get_current_user, require_user
from src.api.context import set_request_user
from src.api.models import (
    ChatHistoryResponse,
    MessageRequest,
    MessageResponse,
    SessionCreateRequest,
    SessionResponse,
)
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
    request_id = getattr(request.state, "request_id", None)
    
    # Set request context
    set_request_user(current_user)
    
    logger.info(
        "Sending message",
        request_id=request_id,
        session_id=session_id,
        pattern=body.pattern,
    )
    
    try:
        session_manager = get_session_manager()
        result = await session_manager.process_message(
            session_id=session_id,
            message=body.message,
            max_turns=body.max_turns,
            metadata=body.metadata,
        )
        
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )
