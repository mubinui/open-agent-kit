"""
AUTOGEN 0.2 RESEARCH:
- Feature needed: Centralized error handling and categorization for agent execution
- Autogen provides: Basic exception handling in agents, but no centralized error management
- Using: Custom ErrorHandler implementation
- Documentation: https://microsoft.github.io/autogen/0.2/docs/reference/agentchat/conversable_agent
- Decision: Custom implementation needed - Autogen doesn't provide centralized error handling
  or error categorization for workflow orchestration. We need custom logic to determine
  retryable vs non-retryable errors and manage error propagation across workflows.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from src.config.execution_models import RetryConfig


logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Categories of errors for handling decisions."""
    
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"


class ErrorResolution(str, Enum):
    """Resolution actions for errors."""
    
    RETRY = "retry"
    FAIL = "fail"
    SKIP = "skip"
    FALLBACK = "fallback"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    
    error: Exception
    error_type: str
    error_message: str
    category: ErrorCategory
    agent_id: Optional[str] = None
    node_id: Optional[str] = None
    workflow_id: Optional[str] = None
    session_id: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ErrorHandlingResult:
    """Result of error handling decision."""
    
    resolution: ErrorResolution
    should_retry: bool
    retry_delay: float = 0.0
    error_context: Optional[ErrorContext] = None
    message: Optional[str] = None


class ErrorHandler:
    """Centralized error handling for orchestration."""
    
    # Error type patterns for categorization
    TIMEOUT_PATTERNS = ['timeout', 'timedout', 'time_out']
    RATE_LIMIT_PATTERNS = ['rate_limit', 'ratelimit', 'too_many_requests', '429']
    TEMPORARY_FAILURE_PATTERNS = ['temporary', 'transient', 'unavailable', '503', '502', '504']
    VALIDATION_PATTERNS = ['validation', 'invalid', 'malformed', 'schema']
    AUTHENTICATION_PATTERNS = ['authentication', 'unauthorized', '401', '403', 'forbidden']
    CONFIGURATION_PATTERNS = ['configuration', 'config', 'not_found', 'missing']
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """
        Initialize error handler.
        
        Args:
            retry_config: Retry configuration (uses defaults if not provided)
        """
        self.retry_config = retry_config or RetryConfig()
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize an error based on its type and message.
        
        Args:
            error: Exception to categorize
            
        Returns:
            ErrorCategory for the error
        """
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # Check for timeout errors
        if any(pattern in error_type or pattern in error_message 
               for pattern in self.TIMEOUT_PATTERNS):
            return ErrorCategory.TIMEOUT
        
        # Check for authentication errors
        if any(pattern in error_type or pattern in error_message 
               for pattern in self.AUTHENTICATION_PATTERNS):
            return ErrorCategory.AUTHENTICATION
        
        # Check for validation errors
        if any(pattern in error_type or pattern in error_message 
               for pattern in self.VALIDATION_PATTERNS):
            return ErrorCategory.VALIDATION
        
        # Check for configuration errors
        if any(pattern in error_type or pattern in error_message 
               for pattern in self.CONFIGURATION_PATTERNS):
            return ErrorCategory.CONFIGURATION
        
        # Check for rate limit errors
        if any(pattern in error_type or pattern in error_message 
               for pattern in self.RATE_LIMIT_PATTERNS):
            return ErrorCategory.RETRYABLE
        
        # Check for temporary failures
        if any(pattern in error_type or pattern in error_message 
               for pattern in self.TEMPORARY_FAILURE_PATTERNS):
            return ErrorCategory.RETRYABLE
        
        # Default to non-retryable
        return ErrorCategory.NON_RETRYABLE
    
    def should_retry(
        self,
        error: Exception,
        retry_count: int,
        category: Optional[ErrorCategory] = None,
    ) -> bool:
        """
        Determine if an error should trigger a retry.
        
        Args:
            error: Exception that occurred
            retry_count: Number of retries already performed (not including initial attempt)
            category: Optional pre-determined error category
            
        Returns:
            True if should retry, False otherwise
        
        Note:
            retry_count represents the number of retry attempts already made,
            NOT including the initial attempt. So with max_retries=3:
            - retry_count=0: initial attempt failed, can retry (0 < 3)
            - retry_count=1: 1st retry failed, can retry (1 < 3)
            - retry_count=2: 2nd retry failed, can retry (2 < 3)
            - retry_count=3: 3rd retry failed, cannot retry (3 >= 3)
            Total attempts: 4 (1 initial + 3 retries)
        """
        # Check if max retries exceeded
        # retry_count is the number of retries already performed
        # We can retry if retry_count < max_retries
        if retry_count >= self.retry_config.max_retries:
            return False
        
        # Categorize error if not provided
        if category is None:
            category = self.categorize_error(error)
        
        # Non-retryable categories
        if category in [
            ErrorCategory.NON_RETRYABLE,
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.VALIDATION,
            ErrorCategory.CONFIGURATION,
        ]:
            return False
        
        # Check against retry configuration
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # Check if explicitly marked as non-retryable
        for no_retry_pattern in self.retry_config.dont_retry_on:
            if no_retry_pattern in error_type or no_retry_pattern in error_message:
                return False
        
        # Check if explicitly marked as retryable
        for retry_pattern in self.retry_config.retry_on:
            if retry_pattern in error_type or retry_pattern in error_message:
                return True
        
        # Default: retry for timeout and retryable categories
        return category in [ErrorCategory.TIMEOUT, ErrorCategory.RETRYABLE]
    
    def calculate_retry_delay(self, retry_count: int) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            retry_count: Current retry count (0-indexed)
            
        Returns:
            Delay in seconds
        """
        backoff_strategy = self.retry_config.backoff_strategy.value
        backoff_factor = self.retry_config.backoff_factor
        
        if backoff_strategy == "constant":
            return backoff_factor
        elif backoff_strategy == "linear":
            return backoff_factor * (retry_count + 1)
        else:  # exponential
            return backoff_factor ** (retry_count + 1)
    
    def handle_error(
        self,
        error: Exception,
        retry_count: int = 0,
        agent_id: Optional[str] = None,
        node_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ErrorHandlingResult:
        """
        Handle an error and determine resolution.
        
        Args:
            error: Exception that occurred
            retry_count: Current retry count
            agent_id: Optional agent identifier
            node_id: Optional node identifier
            workflow_id: Optional workflow identifier
            session_id: Optional session identifier
            metadata: Optional additional metadata
            
        Returns:
            ErrorHandlingResult with resolution decision
        """
        # Categorize the error
        category = self.categorize_error(error)
        
        # Create error context
        error_context = ErrorContext(
            error=error,
            error_type=type(error).__name__,
            error_message=str(error),
            category=category,
            agent_id=agent_id,
            node_id=node_id,
            workflow_id=workflow_id,
            session_id=session_id,
            retry_count=retry_count,
            metadata=metadata or {},
        )
        
        # Determine if should retry
        should_retry_flag = self.should_retry(error, retry_count, category)
        
        # Calculate retry delay if retrying
        retry_delay = 0.0
        if should_retry_flag:
            retry_delay = self.calculate_retry_delay(retry_count)
        
        # Determine resolution
        if should_retry_flag:
            resolution = ErrorResolution.RETRY
            message = (
                f"Retrying after {category.value} error "
                f"(attempt {retry_count + 1}/{self.retry_config.max_retries}): {error}"
            )
        else:
            resolution = ErrorResolution.FAIL
            message = f"Failed with {category.value} error: {error}"
        
        # Log the error handling decision
        self._log_error_handling(error_context, resolution, should_retry_flag, retry_delay)
        
        return ErrorHandlingResult(
            resolution=resolution,
            should_retry=should_retry_flag,
            retry_delay=retry_delay,
            error_context=error_context,
            message=message,
        )
    
    def _log_error_handling(
        self,
        error_context: ErrorContext,
        resolution: ErrorResolution,
        should_retry: bool,
        retry_delay: float,
    ) -> None:
        """
        Log error handling decision.
        
        Args:
            error_context: Error context
            resolution: Resolution decision
            should_retry: Whether to retry
            retry_delay: Retry delay in seconds
        """
        log_data = {
            'error_type': error_context.error_type,
            'error_message': error_context.error_message,
            'category': error_context.category.value,
            'resolution': resolution.value,
            'should_retry': should_retry,
            'retry_count': error_context.retry_count,
            'agent_id': error_context.agent_id,
            'node_id': error_context.node_id,
            'workflow_id': error_context.workflow_id,
            'session_id': error_context.session_id,
        }
        
        if should_retry:
            log_data['retry_delay'] = retry_delay
            logger.warning(
                f"Error will be retried: {error_context.error_message}",
                extra=log_data
            )
        else:
            logger.error(
                f"Error will not be retried: {error_context.error_message}",
                extra=log_data
            )
    
    def format_error_message(
        self,
        error_context: ErrorContext,
        include_details: bool = True,
    ) -> str:
        """
        Format error message for user display.
        
        Args:
            error_context: Error context
            include_details: Whether to include detailed information
            
        Returns:
            Formatted error message
        """
        message = f"{error_context.category.value.replace('_', ' ').title()}: {error_context.error_message}"
        
        if include_details:
            details = []
            if error_context.agent_id:
                details.append(f"Agent: {error_context.agent_id}")
            if error_context.node_id:
                details.append(f"Node: {error_context.node_id}")
            if error_context.workflow_id:
                details.append(f"Workflow: {error_context.workflow_id}")
            if error_context.retry_count > 0:
                details.append(f"Retry: {error_context.retry_count}/{self.retry_config.max_retries}")
            
            if details:
                message += f" ({', '.join(details)})"
        
        return message
