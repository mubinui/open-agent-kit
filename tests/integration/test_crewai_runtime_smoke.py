"""Smoke tests for the CrewAI-only runtime boundary."""

from src.crewai_runtime import CrewAIWorkflowRuntime


def test_crewai_runtime_exposes_availability_probe() -> None:
    assert isinstance(CrewAIWorkflowRuntime.is_available(), bool)
