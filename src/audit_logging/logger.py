"""Structured logging configuration."""

import logging
import sys
from typing import Optional
from uuid import UUID

import structlog

from src.config import get_settings


def configure_logging() -> None:
    """
    Configure structured logging for the application.
    
    This configures structlog with appropriate processors for
    structured logging with correlation IDs and context.
    
    Requirements: 6.1, 6.2, 12.1, 12.2
    """
    settings = get_settings()

    # Configure structlog processors
    processors = [
        # Merge context variables (correlation IDs, etc.)
        structlog.contextvars.merge_contextvars,
        # Add log level
        structlog.processors.add_log_level,
        # Add stack info for errors
        structlog.processors.StackInfoRenderer(),
        # Set exception info
        structlog.dev.set_exc_info,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    # Add appropriate renderer based on environment
    if settings.app.log_level == "DEBUG" or settings.app.environment == "development":
        # Use console renderer for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Use JSON renderer for production
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.app.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def bind_correlation_ids(
    request_id: Optional[str] = None,
    session_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Bind correlation IDs to the logging context.
    
    This adds correlation IDs to all subsequent log messages
    in the current context.
    
    Args:
        request_id: HTTP request ID
        session_id: Conversation session ID
        user_id: User identifier
        
    Requirements: 6.1, 6.2, 12.1, 12.2
    """
    context = {}
    
    if request_id:
        context["request_id"] = request_id
    if session_id:
        context["session_id"] = str(session_id)
    if user_id:
        context["user_id"] = user_id
    
    if context:
        structlog.contextvars.bind_contextvars(**context)


def clear_correlation_ids() -> None:
    """
    Clear correlation IDs from the logging context.
    
    This should be called at the end of a request or operation
    to prevent context leakage.
    
    Requirements: 6.1, 6.2
    """
    structlog.contextvars.clear_contextvars()


def log_agent_decision(
    logger: structlog.BoundLogger,
    agent_id: str,
    decision: str,
    reasoning: Optional[str] = None,
    context: Optional[dict] = None,
) -> None:
    """
    Log an agent decision with structured context.
    
    Args:
        logger: Logger instance
        agent_id: Agent identifier
        decision: Decision made by the agent
        reasoning: Reasoning behind the decision
        context: Additional context
        
    Requirements: 6.1, 6.2, 12.1, 12.2
    """
    logger.info(
        "agent_decision",
        agent_id=agent_id,
        decision=decision,
        reasoning=reasoning,
        context=context or {},
    )


def log_tool_call(
    logger: structlog.BoundLogger,
    agent_id: str,
    tool_name: str,
    tool_args: dict,
    result: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log a tool call with structured context.
    
    Args:
        logger: Logger instance
        agent_id: Agent identifier
        tool_name: Name of the tool
        tool_args: Tool arguments
        result: Tool execution result
        error: Error message if tool failed
        
    Requirements: 6.1, 6.2, 12.1, 12.2
    """
    log_data = {
        "agent_id": agent_id,
        "tool_name": tool_name,
        "tool_args": tool_args,
    }
    
    if result:
        log_data["result"] = result
    if error:
        log_data["error"] = error
    
    if error:
        logger.error("tool_call_failed", **log_data)
    else:
        logger.info("tool_call_success", **log_data)
