"""
Workflow Test Models for database persistence.

Provides SQLAlchemy models and Pydantic schemas for workflow test cases and results.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# SQLAlchemy models live in the unified schema so Alembic sees one metadata;
# re-exported here for backwards compatibility with existing imports.
from src.infrastructure.database.schema import (  # noqa: F401
    Base,
    WorkflowTestCase,
    WorkflowTestResult,
    WorkflowTestRun,
)


class TestStatus(str, Enum):
    """Status of a test execution."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


# Pydantic Schemas for API

class WorkflowTestCaseCreate(BaseModel):
    """Request to create a workflow test case."""
    workflow_id: str = Field(description="ID of the workflow to test")
    name: str = Field(description="Name of the test case")
    description: Optional[str] = Field(default=None, description="Test case description")
    input_message: str = Field(description="Message to send to the workflow")
    expected_agent: Optional[str] = Field(default=None, description="Expected agent to respond")
    expected_tools: Optional[List[str]] = Field(default=None, description="Expected tools to be called")
    expected_output_contains: Optional[List[str]] = Field(default=None, description="Strings that should appear in output")
    expected_output_pattern: Optional[str] = Field(default=None, description="Regex pattern to match output")
    timeout_seconds: int = Field(default=60, ge=1, le=300, description="Timeout in seconds")
    enabled: bool = Field(default=True, description="Whether test case is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowTestCaseUpdate(BaseModel):
    """Request to update a workflow test case."""
    name: Optional[str] = None
    description: Optional[str] = None
    input_message: Optional[str] = None
    expected_agent: Optional[str] = None
    expected_tools: Optional[List[str]] = None
    expected_output_contains: Optional[List[str]] = None
    expected_output_pattern: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowTestCaseResponse(BaseModel):
    """Response containing a workflow test case."""
    id: UUID
    workflow_id: str
    name: str
    description: Optional[str]
    input_message: str
    expected_agent: Optional[str]
    expected_tools: Optional[List[str]]
    expected_output_contains: Optional[List[str]]
    expected_output_pattern: Optional[str]
    timeout_seconds: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    metadata: Dict[str, Any]
    
    model_config = {"from_attributes": True}


class WorkflowTestResultResponse(BaseModel):
    """Response containing a test result."""
    id: UUID
    test_case_id: UUID
    workflow_id: str
    status: TestStatus
    actual_response: Optional[str]
    actual_agent: Optional[str]
    actual_tools: Optional[List[str]]
    execution_time_ms: Optional[int]
    error_message: Optional[str]
    execution_trace: Optional[Dict[str, Any]]
    started_at: datetime
    completed_at: Optional[datetime]
    run_by: Optional[str]
    run_id: Optional[UUID]
    metadata: Dict[str, Any]
    
    model_config = {"from_attributes": True}


class WorkflowTestRunResponse(BaseModel):
    """Response containing a test run summary."""
    id: UUID
    workflow_id: Optional[str]
    name: Optional[str]
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    status: TestStatus
    started_at: datetime
    completed_at: Optional[datetime]
    run_by: Optional[str]
    metadata: Dict[str, Any]
    pass_rate: float = Field(default=0.0)
    
    model_config = {"from_attributes": True}
    
    def model_post_init(self, __context) -> None:
        if self.total_tests > 0:
            self.pass_rate = (self.passed_tests / self.total_tests) * 100


class WorkflowExecuteRequest(BaseModel):
    """Request for standalone workflow execution."""
    message: str = Field(description="Input message for the workflow")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timeout_seconds: int = Field(default=60, ge=1, le=300, description="Execution timeout")
    dry_run: bool = Field(default=False, description="If true, validate but don't execute")


class WorkflowExecuteResponse(BaseModel):
    """Response from standalone workflow execution."""
    workflow_id: str
    response: str
    execution_time_ms: int
    agents_called: List[str] = Field(default_factory=list)
    tools_called: List[str] = Field(default_factory=list)
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TestRunRequest(BaseModel):
    """Request to run tests for a workflow."""
    workflow_id: Optional[str] = Field(default=None, description="Workflow to test (null = all)")
    test_case_ids: Optional[List[UUID]] = Field(default=None, description="Specific test cases (null = all enabled)")
    name: Optional[str] = Field(default=None, description="Name for this test run")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowValidationResponse(BaseModel):
    """Response from workflow configuration validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
