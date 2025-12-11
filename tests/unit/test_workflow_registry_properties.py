"""
Property-based tests for workflow registry.

**Feature: context-leak-fix**

These tests validate the correctness properties for default workflow
configuration as specified in the design document.
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.config.workflow_models import (
    WorkflowConfig,
    ConversationPattern,
    SummaryMethod,
    WorkflowType,
    PersistenceMode,
)
from src.config.workflow_registry import WorkflowRegistry


# Strategies for generating test data

@st.composite
def workflow_id_strategy(draw):
    """Generate valid workflow IDs."""
    return draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=1,
        max_size=20
    ).filter(lambda x: x and x[0].isalnum()))


@st.composite
def workflow_config_strategy(draw, default=False, enabled=True):
    """Generate a valid WorkflowConfig."""
    workflow_id = draw(workflow_id_strategy())
    
    return WorkflowConfig(
        id=workflow_id,
        name=draw(st.text(min_size=1, max_size=50)),
        description=draw(st.text(min_size=1, max_size=200)),
        pattern=ConversationPattern.TWO_AGENT,
        entry_agent_id="test_agent",
        recipient_agent_id="test_recipient",
        max_turns=draw(st.integers(min_value=1, max_value=20)),
        summary_method=SummaryMethod.LAST_MSG,
        enabled=enabled,
        default=default,
        metadata={},
        workflow_type=WorkflowType.SEQUENTIAL,
        persistence=PersistenceMode.MONGO_ONLY,
    )


# Property 5: Default Workflow Availability
# **Validates: Requirements 2.1, 2.4**

@given(
    num_workflows=st.integers(min_value=1, max_value=10),
    default_index=st.integers(min_value=0, max_value=9),
    data=st.data(),
)
@settings(max_examples=100, deadline=None)
def test_property_5_default_workflow_availability(num_workflows, default_index, data):
    """
    **Feature: context-leak-fix, Property 5: Default Workflow Availability**
    **Validates: Requirements 2.1, 2.4**
    
    Property: For any workflow registry with at least one workflow marked
    as default, get_default_workflow() should return a non-null WorkflowConfig.
    
    This test verifies that:
    1. When a default workflow is configured, it can be retrieved
    2. The returned workflow has the default flag set
    3. The workflow ID can be retrieved via get_default_workflow_id()
    4. If default is disabled, fallback to first enabled workflow works
    """
    assume(default_index < num_workflows)
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = Path(f.name)
        
        # Generate workflows
        workflows = []
        for i in range(num_workflows):
            is_default = (i == default_index)
            workflow = data.draw(workflow_config_strategy(default=is_default, enabled=True))
            # Ensure unique IDs
            workflow.id = f"workflow_{i}"
            workflows.append(workflow)
        
        # Write config
        config_data = {
            "version": "1.0.0",
            "workflows": [w.model_dump(mode='json') for w in workflows]
        }
        json.dump(config_data, f)
    
    try:
        # Create registry
        registry = WorkflowRegistry(config_path=config_path)
        
        # Property: get_default_workflow() should return a non-null workflow
        default_workflow = registry.get_default_workflow()
        assert default_workflow is not None, \
            "get_default_workflow() should return a workflow when default is configured"
        
        # Property: The returned workflow should have default=True
        assert default_workflow.default is True, \
            "Returned workflow should have default flag set"
        
        # Property: The workflow ID should match the expected default
        assert default_workflow.id == f"workflow_{default_index}", \
            "Returned workflow should be the one marked as default"
        
        # Property: get_default_workflow_id() should return the correct ID
        default_id = registry.get_default_workflow_id()
        assert default_id is not None, \
            "get_default_workflow_id() should return an ID when default is configured"
        assert default_id == f"workflow_{default_index}", \
            "get_default_workflow_id() should return the default workflow's ID"
        
        # Property: The returned workflow should be enabled
        assert default_workflow.enabled is True, \
            "Default workflow should be enabled"
        
    finally:
        # Cleanup
        config_path.unlink()


@given(
    num_workflows=st.integers(min_value=1, max_value=10),
    data=st.data(),
)
@settings(max_examples=100, deadline=None)
def test_no_default_workflow_configured(num_workflows, data):
    """
    Test that when no workflow is marked as default, get_default_workflow()
    returns None.
    
    This validates that the registry correctly handles the case where
    no default is configured.
    """
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = Path(f.name)
        
        # Generate workflows with no default
        workflows = []
        for i in range(num_workflows):
            workflow = data.draw(workflow_config_strategy(default=False, enabled=True))
            workflow.id = f"workflow_{i}"
            workflows.append(workflow)
        
        # Write config
        config_data = {
            "version": "1.0.0",
            "workflows": [w.model_dump(mode='json') for w in workflows]
        }
        json.dump(config_data, f)
    
    try:
        # Create registry
        registry = WorkflowRegistry(config_path=config_path)
        
        # Property: get_default_workflow() should return None when no default
        default_workflow = registry.get_default_workflow()
        assert default_workflow is None, \
            "get_default_workflow() should return None when no default is configured"
        
        # Property: get_default_workflow_id() should return None
        default_id = registry.get_default_workflow_id()
        assert default_id is None, \
            "get_default_workflow_id() should return None when no default is configured"
        
    finally:
        # Cleanup
        config_path.unlink()


@given(
    num_workflows=st.integers(min_value=2, max_value=10),
    default_index=st.integers(min_value=0, max_value=9),
    data=st.data(),
)
@settings(max_examples=100, deadline=None)
def test_default_workflow_disabled_fallback(num_workflows, default_index, data):
    """
    Test that when the default workflow is disabled, the registry falls back
    to the first enabled workflow.
    
    This validates the fallback behavior specified in the requirements.
    """
    assume(default_index < num_workflows)
    assume(num_workflows >= 2)  # Need at least 2 workflows for fallback
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = Path(f.name)
        
        # Generate workflows
        workflows = []
        for i in range(num_workflows):
            is_default = (i == default_index)
            # Default workflow is disabled, others are enabled
            is_enabled = not is_default
            workflow = data.draw(workflow_config_strategy(default=is_default, enabled=is_enabled))
            workflow.id = f"workflow_{i}"
            workflows.append(workflow)
        
        # Write config
        config_data = {
            "version": "1.0.0",
            "workflows": [w.model_dump(mode='json') for w in workflows]
        }
        json.dump(config_data, f)
    
    try:
        # Create registry
        registry = WorkflowRegistry(config_path=config_path)
        
        # Property: get_default_workflow() should return first enabled workflow
        default_workflow = registry.get_default_workflow()
        
        if num_workflows > 1:
            # Should fall back to first enabled workflow
            assert default_workflow is not None, \
                "Should fall back to first enabled workflow when default is disabled"
            
            # Should not be the disabled default
            assert default_workflow.id != f"workflow_{default_index}", \
                "Should not return the disabled default workflow"
            
            # Should be enabled
            assert default_workflow.enabled is True, \
                "Fallback workflow should be enabled"
        
    finally:
        # Cleanup
        config_path.unlink()


@given(
    num_workflows=st.integers(min_value=2, max_value=5),
    num_defaults=st.integers(min_value=2, max_value=3),
    data=st.data(),
)
@settings(max_examples=50, deadline=None)
def test_multiple_defaults_uses_first(num_workflows, num_defaults, data):
    """
    Test that when multiple workflows are marked as default,
    the first one is used.
    
    This validates that the registry handles misconfiguration gracefully.
    """
    assume(num_defaults <= num_workflows)
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = Path(f.name)
        
        # Generate workflows with multiple defaults
        workflows = []
        for i in range(num_workflows):
            is_default = (i < num_defaults)
            workflow = data.draw(workflow_config_strategy(default=is_default, enabled=True))
            workflow.id = f"workflow_{i}"
            workflows.append(workflow)
        
        # Write config
        config_data = {
            "version": "1.0.0",
            "workflows": [w.model_dump(mode='json') for w in workflows]
        }
        json.dump(config_data, f)
    
    try:
        # Create registry
        registry = WorkflowRegistry(config_path=config_path)
        
        # Property: Should return the first default workflow
        default_workflow = registry.get_default_workflow()
        assert default_workflow is not None, \
            "Should return a workflow when multiple defaults exist"
        
        # Property: Should be the first one marked as default
        assert default_workflow.id == "workflow_0", \
            "Should return the first workflow marked as default"
        
        assert default_workflow.default is True, \
            "Returned workflow should have default flag"
        
    finally:
        # Cleanup
        config_path.unlink()


def test_empty_registry_no_default():
    """
    Test that an empty registry returns None for default workflow.
    """
    # Create a temporary config file with no workflows
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = Path(f.name)
        
        config_data = {
            "version": "1.0.0",
            "workflows": []
        }
        json.dump(config_data, f)
    
    try:
        # Create registry
        registry = WorkflowRegistry(config_path=config_path)
        
        # Property: Empty registry should return None
        default_workflow = registry.get_default_workflow()
        assert default_workflow is None, \
            "Empty registry should return None for default workflow"
        
        default_id = registry.get_default_workflow_id()
        assert default_id is None, \
            "Empty registry should return None for default workflow ID"
        
    finally:
        # Cleanup
        config_path.unlink()


def test_all_workflows_disabled_no_default():
    """
    Test that when all workflows are disabled (including default),
    get_default_workflow() returns None.
    """
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = Path(f.name)
        
        # Generate workflows all disabled
        workflows = []
        for i in range(3):
            is_default = (i == 0)
            workflow = workflow_config_strategy(default=is_default, enabled=False).example()
            workflow.id = f"workflow_{i}"
            workflows.append(workflow)
        
        # Write config
        config_data = {
            "version": "1.0.0",
            "workflows": [w.model_dump(mode='json') for w in workflows]
        }
        json.dump(config_data, f)
    
    try:
        # Create registry
        registry = WorkflowRegistry(config_path=config_path)
        
        # Property: Should return None when all workflows are disabled
        default_workflow = registry.get_default_workflow()
        assert default_workflow is None, \
            "Should return None when all workflows (including default) are disabled"
        
        default_id = registry.get_default_workflow_id()
        assert default_id is None, \
            "Should return None for ID when all workflows are disabled"
        
    finally:
        # Cleanup
        config_path.unlink()
