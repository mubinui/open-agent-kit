#!/usr/bin/env python3
"""Quick test script to verify configuration versioning and validation."""

import json
from datetime import datetime

from src.config.agent_models import AgentConfig, AgentType, LLMConfig, HumanInputMode
from src.config.workflow_models import (
    WorkflowConfig,
    ConversationPattern,
    WorkflowType,
    PersistenceMode
)
from src.config.tool_models import ToolConfig
from src.config.vector_db_models import VectorDBConfig, VectorDBType, ChromaDBConfig
from src.config.validation import ConfigValidator, VersionManager


def test_agent_versioning():
    """Test agent configuration versioning."""
    print("Testing agent versioning...")
    
    agent = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="Test Agent",
        llm_config=LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-oss-20b"
        )
    )
    
    assert agent.version == 1, "Initial version should be 1"
    assert agent.last_updated is not None, "last_updated should be set"
    
    # Increment version
    agent = ConfigValidator.increment_version(agent)
    assert agent.version == 2, "Version should be incremented to 2"
    
    # Update timestamp
    old_timestamp = agent.last_updated
    agent = ConfigValidator.update_timestamp(agent)
    assert agent.last_updated > old_timestamp, "Timestamp should be updated"
    
    print("✓ Agent versioning works correctly")


def test_workflow_type_validation():
    """Test workflow type validation."""
    print("\nTesting workflow type validation...")
    
    # Valid workflow types
    for wf_type in ["chatbot", "sequential", "tree", "custom"]:
        result = ConfigValidator.validate_workflow_type(wf_type)
        assert result == WorkflowType(wf_type), f"Should accept {wf_type}"
    
    # Invalid workflow type
    try:
        ConfigValidator.validate_workflow_type("invalid")
        assert False, "Should raise ValueError for invalid type"
    except ValueError as e:
        assert "Invalid workflow_type" in str(e)
    
    print("✓ Workflow type validation works correctly")


def test_persistence_validation():
    """Test persistence mode validation."""
    print("\nTesting persistence mode validation...")
    
    # Valid: chatbot with mongo_only
    result = ConfigValidator.validate_persistence_mode(
        "mongo_only",
        WorkflowType.CHATBOT
    )
    assert result == PersistenceMode.MONGO_ONLY
    
    # Invalid: chatbot with postgres
    try:
        ConfigValidator.validate_persistence_mode(
            "postgres",
            WorkflowType.CHATBOT
        )
        assert False, "Should raise ValueError for chatbot with postgres"
    except ValueError as e:
        assert "mongo_only" in str(e).lower()
    
    # Valid: sequential with postgres
    result = ConfigValidator.validate_persistence_mode(
        "postgres",
        WorkflowType.SEQUENTIAL
    )
    assert result == PersistenceMode.POSTGRES
    
    print("✓ Persistence mode validation works correctly")


def test_workflow_config_validation():
    """Test complete workflow configuration validation."""
    print("\nTesting workflow configuration validation...")
    
    # Valid chatbot workflow
    workflow = WorkflowConfig(
        id="test_chatbot",
        name="Test Chatbot",
        description="Test chatbot workflow",
        pattern=ConversationPattern.TWO_AGENT,
        entry_agent_id="agent1",
        recipient_agent_id="agent2",
        workflow_type=WorkflowType.CHATBOT,
        persistence=PersistenceMode.MONGO_ONLY
    )
    
    ConfigValidator.validate_workflow_config(workflow)
    assert workflow.version == 1
    assert workflow.last_updated is not None
    
    # Invalid chatbot workflow (wrong persistence)
    try:
        invalid_workflow = WorkflowConfig(
            id="invalid_chatbot",
            name="Invalid Chatbot",
            description="Invalid chatbot workflow",
            pattern=ConversationPattern.TWO_AGENT,
            entry_agent_id="agent1",
            recipient_agent_id="agent2",
            workflow_type=WorkflowType.CHATBOT,
            persistence=PersistenceMode.POSTGRES
        )
        assert False, "Should raise ValueError for chatbot with postgres"
    except ValueError as e:
        assert "mongo_only" in str(e).lower()
    
    print("✓ Workflow configuration validation works correctly")


def test_tool_versioning():
    """Test tool configuration versioning."""
    print("\nTesting tool versioning...")
    
    tool = ToolConfig(
        id="test_tool",
        name="test_tool",
        description="Test tool",
        entrypoint="src.tools.test:test_function"
    )
    
    assert tool.version == 1
    assert tool.last_updated is not None
    
    # Prepare for update
    tool = ConfigValidator.prepare_for_update(tool)
    assert tool.version == 2
    
    print("✓ Tool versioning works correctly")


def test_vector_db_versioning():
    """Test vector database configuration versioning."""
    print("\nTesting vector database versioning...")
    
    db = VectorDBConfig(
        type=VectorDBType.CHROMADB,
        collection_name="test_collection",
        chromadb_config=ChromaDBConfig()
    )
    
    assert db.version == 1
    assert db.last_updated is not None
    
    print("✓ Vector database versioning works correctly")


def test_version_comparison():
    """Test version comparison."""
    print("\nTesting version comparison...")
    
    agent1 = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="Test Agent V1",
        llm_config=LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-oss-20b",
            temperature=0.7
        )
    )
    
    agent2 = AgentConfig(
        id="test_agent",
        type=AgentType.CONVERSABLE,
        name="Test Agent V2",
        llm_config=LLMConfig(
            provider_id="openrouter",
            model="openai/gpt-oss-20b",
            temperature=0.5
        ),
        version=2
    )
    
    diff = VersionManager.compare_versions(agent1, agent2)
    
    assert len(diff["modified"]) > 0, "Should detect modified fields"
    assert any(m["field"] == "name" for m in diff["modified"])
    
    print("✓ Version comparison works correctly")


def test_json_configs():
    """Test that JSON configs can be loaded with new fields."""
    print("\nTesting JSON configuration loading...")
    
    # Load agents.json
    with open("configs/agents.json", "r") as f:
        agents_data = json.load(f)
    
    for agent_data in agents_data["agents"]:
        assert "version" in agent_data, f"Agent {agent_data['id']} missing version"
        assert "last_updated" in agent_data, f"Agent {agent_data['id']} missing last_updated"
    
    # Load workflows.json
    with open("configs/workflows.json", "r") as f:
        workflows_data = json.load(f)
    
    for workflow_data in workflows_data["workflows"]:
        assert "version" in workflow_data, f"Workflow {workflow_data['id']} missing version"
        assert "last_updated" in workflow_data, f"Workflow {workflow_data['id']} missing last_updated"
        assert "workflow_type" in workflow_data, f"Workflow {workflow_data['id']} missing workflow_type"
        assert "persistence" in workflow_data, f"Workflow {workflow_data['id']} missing persistence"
        
        # Validate chatbot workflows
        if workflow_data["workflow_type"] == "chatbot":
            assert workflow_data["persistence"] == "mongo_only", \
                f"Chatbot workflow {workflow_data['id']} must use mongo_only persistence"
    
    # Load tools.json
    with open("configs/tools.json", "r") as f:
        tools_data = json.load(f)
    
    for tool_data in tools_data["tools"]:
        assert "version" in tool_data, f"Tool {tool_data['id']} missing version"
        assert "last_updated" in tool_data, f"Tool {tool_data['id']} missing last_updated"
    
    # Load vector_databases.json
    with open("configs/vector_databases.json", "r") as f:
        vdb_data = json.load(f)
    
    for db_data in vdb_data["databases"]:
        assert "version" in db_data, f"Vector DB {db_data['collection_name']} missing version"
        assert "last_updated" in db_data, f"Vector DB {db_data['collection_name']} missing last_updated"
    
    print("✓ JSON configurations are valid")


if __name__ == "__main__":
    print("=" * 60)
    print("Configuration Versioning and Validation Tests")
    print("=" * 60)
    
    try:
        test_agent_versioning()
        test_workflow_type_validation()
        test_persistence_validation()
        test_workflow_config_validation()
        test_tool_versioning()
        test_vector_db_versioning()
        test_version_comparison()
        test_json_configs()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
