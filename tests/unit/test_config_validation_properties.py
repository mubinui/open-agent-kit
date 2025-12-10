"""
Property-based tests for configuration validation.

**Feature: industry-grade-orchestration, Property 9: Agent configuration validation**
**Validates: Requirements 4.1, 4.2, 5.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError

from src.config.agent_models import AgentConfig, AgentType, HumanInputMode, LLMConfig


# Strategies for generating test data
@st.composite
def valid_agent_id(draw):
    """Generate valid agent IDs (lowercase alphanumeric with underscores)."""
    length = draw(st.integers(min_value=3, max_value=20))
    chars = draw(st.lists(
        st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789_'),
        min_size=length,
        max_size=length
    ))
    # Ensure it starts with a letter
    if chars[0].isdigit() or chars[0] == '_':
        chars[0] = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz'))
    return ''.join(chars)


@st.composite
def valid_llm_config(draw):
    """Generate valid LLM configuration."""
    return LLMConfig(
        provider_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        model=draw(st.text(min_size=1, max_size=50)),
        temperature=draw(st.floats(min_value=0.0, max_value=2.0)),
        max_tokens=draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10000))),
        cache_seed=draw(st.one_of(st.none(), st.integers())),
        timeout=draw(st.integers(min_value=1, max_value=600))
    )


@st.composite
def valid_conversable_agent_config(draw):
    """Generate valid conversable agent configuration."""
    return {
        "id": draw(valid_agent_id()),
        "type": AgentType.CONVERSABLE.value,
        "name": draw(st.text(min_size=1, max_size=50)),
        "system_message": draw(st.text(min_size=1, max_size=500)),
        "llm_config": draw(valid_llm_config()).model_dump(),
        "human_input_mode": draw(st.sampled_from([mode.value for mode in HumanInputMode])),
        "max_consecutive_auto_reply": draw(st.integers(min_value=0, max_value=50))
    }


@st.composite
def invalid_agent_config_missing_llm(draw):
    """Generate invalid agent config missing required llm_config."""
    return {
        "id": draw(valid_agent_id()),
        "type": AgentType.CONVERSABLE.value,
        "name": draw(st.text(min_size=1, max_size=50)),
        "system_message": draw(st.text(min_size=1, max_size=500)),
        "llm_config": None,  # Missing required field
        "human_input_mode": HumanInputMode.NEVER.value,
        "max_consecutive_auto_reply": 10
    }


@st.composite
def invalid_agent_config_missing_system_message(draw):
    """Generate invalid agent config missing system_message."""
    return {
        "id": draw(valid_agent_id()),
        "type": AgentType.CONVERSABLE.value,
        "name": draw(st.text(min_size=1, max_size=50)),
        "system_message": None,  # Missing for conversable agent
        "llm_config": draw(valid_llm_config()).model_dump(),
        "human_input_mode": HumanInputMode.NEVER.value,
        "max_consecutive_auto_reply": 10
    }


class TestAgentConfigurationValidation:
    """
    Property 9: Agent configuration validation
    
    For any agent configuration missing required fields (system_message, llm_config),
    creation should fail with detailed validation errors specifying which fields are missing.
    
    Validates: Requirements 4.1, 4.2, 5.5
    """
    
    @settings(max_examples=100)
    @given(config_data=valid_conversable_agent_config())
    def test_valid_agent_config_succeeds(self, config_data):
        """
        Property: Valid agent configurations should be accepted.
        
        For any valid agent configuration with all required fields,
        the AgentConfig should be created successfully.
        """
        # Create agent config
        agent = AgentConfig(**config_data)
        
        # Validate - should not raise
        agent.validate_config()
        
        # Verify fields are set correctly
        assert agent.id == config_data["id"]
        assert agent.type == AgentType.CONVERSABLE
        assert agent.name == config_data["name"]
        assert agent.system_message == config_data["system_message"]
        assert agent.llm_config is not None
    
    @settings(max_examples=100)
    @given(config_data=invalid_agent_config_missing_llm())
    def test_missing_llm_config_fails(self, config_data):
        """
        Property: Conversable agents without llm_config should fail validation.
        
        For any conversable agent configuration with llm_config=None,
        validation should fail with an error indicating llm_config is required.
        """
        # Create agent config (Pydantic validation may pass)
        agent = AgentConfig(**config_data)
        
        # Validate should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            agent.validate_config()
        
        # Error message should mention llm_config
        error_msg = str(exc_info.value).lower()
        assert "llm_config" in error_msg or "llm" in error_msg
        assert agent.id in str(exc_info.value)
    
    @settings(max_examples=100)
    @given(
        agent_id=valid_agent_id(),
        name=st.text(min_size=1, max_size=50)
    )
    def test_retrieve_agent_without_retrieve_config_fails(self, agent_id, name):
        """
        Property: RetrieveUserProxy agents without retrieve_config should fail validation.
        
        For any retrieve_user_proxy agent configuration without retrieve_config,
        validation should fail with an error indicating retrieve_config is required.
        """
        config_data = {
            "id": agent_id,
            "type": AgentType.RETRIEVE_USER_PROXY.value,
            "name": name,
            "retrieve_config": None  # Missing required field
        }
        
        agent = AgentConfig(**config_data)
        
        # Validate should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            agent.validate_config()
        
        # Error message should mention retrieve_config
        error_msg = str(exc_info.value).lower()
        assert "retrieve_config" in error_msg or "retrieve" in error_msg
        assert agent_id in str(exc_info.value)
    
    @settings(max_examples=100)
    @given(
        agent_id=valid_agent_id(),
        name=st.text(min_size=1, max_size=50),
        llm_config=valid_llm_config()
    )
    def test_group_chat_manager_without_llm_config_fails(self, agent_id, name, llm_config):
        """
        Property: GroupChatManager agents without llm_config should fail validation.
        
        For any group_chat_manager agent configuration without llm_config,
        validation should fail with an error indicating llm_config is required.
        """
        # Test with None llm_config
        config_data = {
            "id": agent_id,
            "type": AgentType.GROUP_CHAT_MANAGER.value,
            "name": name,
            "llm_config": None
        }
        
        agent = AgentConfig(**config_data)
        
        # Validate should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            agent.validate_config()
        
        # Error message should mention llm_config
        error_msg = str(exc_info.value).lower()
        assert "llm_config" in error_msg or "llm" in error_msg
        assert agent_id in str(exc_info.value)
    
    @settings(max_examples=100)
    @given(
        invalid_id=st.text(min_size=1, max_size=20).filter(
            lambda x: not x.replace('_', '').replace('-', '').isalnum() or 
                     any(c.isupper() for c in x) or
                     x.startswith('_') or
                     x.startswith('-')
        )
    )
    def test_invalid_agent_id_format_fails(self, invalid_id):
        """
        Property: Agent IDs with invalid format should fail validation.
        
        For any agent ID that doesn't match the pattern ^[a-z0-9_]+$,
        validation should fail.
        """
        config_data = {
            "id": invalid_id,
            "type": AgentType.CONVERSABLE.value,
            "name": "Test Agent",
            "system_message": "Test message",
            "llm_config": LLMConfig(
                provider_id="test",
                model="test-model"
            ).model_dump()
        }
        
        # Should raise ValidationError during creation
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(**config_data)
        
        # Error should mention the id field
        errors = exc_info.value.errors()
        assert any('id' in str(err) for err in errors)
