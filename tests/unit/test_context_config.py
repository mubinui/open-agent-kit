"""Tests for ContextConfig in settings."""

import pytest

from src.config.settings import ContextConfig, Settings, get_settings, reset_settings


class TestContextConfig:
    """Tests for ContextConfig."""

    def test_context_config_defaults(self) -> None:
        """Test that ContextConfig has correct default values."""
        config = ContextConfig()

        assert config.max_history_messages == 10
        assert config.max_context_exchanges == 5
        assert config.max_message_length == 500
        assert config.strip_wrappers_from_storage is True
        assert config.strip_wrappers_from_response is True

    def test_context_config_custom_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that ContextConfig accepts custom values from environment."""
        # Set environment variables
        monkeypatch.setenv("MAX_HISTORY_MESSAGES", "20")
        monkeypatch.setenv("MAX_CONTEXT_EXCHANGES", "10")
        monkeypatch.setenv("MAX_MESSAGE_LENGTH", "1000")
        monkeypatch.setenv("STRIP_WRAPPERS_FROM_STORAGE", "false")
        monkeypatch.setenv("STRIP_WRAPPERS_FROM_RESPONSE", "false")

        config = ContextConfig()

        assert config.max_history_messages == 20
        assert config.max_context_exchanges == 10
        assert config.max_message_length == 1000
        assert config.strip_wrappers_from_storage is False
        assert config.strip_wrappers_from_response is False

    def test_context_config_in_settings(self) -> None:
        """Test that ContextConfig is accessible through Settings."""
        reset_settings()
        settings = get_settings()

        assert hasattr(settings, "context")
        assert isinstance(settings.context, ContextConfig)
        assert settings.context.max_history_messages == 10
        assert settings.context.max_context_exchanges == 5
        assert settings.context.max_message_length == 500
        assert settings.context.strip_wrappers_from_storage is True
        assert settings.context.strip_wrappers_from_response is True

    def test_context_config_field_types(self) -> None:
        """Test that ContextConfig fields have correct types."""
        config = ContextConfig()

        assert isinstance(config.max_history_messages, int)
        assert isinstance(config.max_context_exchanges, int)
        assert isinstance(config.max_message_length, int)
        assert isinstance(config.strip_wrappers_from_storage, bool)
        assert isinstance(config.strip_wrappers_from_response, bool)
