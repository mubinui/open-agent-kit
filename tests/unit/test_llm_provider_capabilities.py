"""Tests for model capability inference."""

from src.config.llm_provider import ProviderConfig, ProviderType
from src.config.model_capabilities import infer_model_capabilities


def test_gpt_4o_capabilities_include_streaming_tools_vision_and_schema() -> None:
    capabilities = infer_model_capabilities("openai/gpt-4o-2024-11-20", ProviderType.OPENROUTER)

    assert capabilities.streaming is True
    assert capabilities.tool_calling is True
    assert capabilities.vision is True
    assert capabilities.json_schema is True
    assert capabilities.max_context >= 128_000


def test_reasoning_models_expose_reasoning_trace_flag() -> None:
    capabilities = infer_model_capabilities("deepseek/deepseek-r1-0528", ProviderType.OPENROUTER)

    assert capabilities.reasoning_trace is True
    assert capabilities.tool_calling is True
    assert capabilities.json_schema is True


def test_audio_models_expose_audio_flags() -> None:
    capabilities = infer_model_capabilities("openai/gpt-4o-realtime-preview", ProviderType.OPENROUTER)

    assert capabilities.audio_in is True
    assert capabilities.audio_out is True


def test_provider_config_uses_active_model_for_capabilities() -> None:
    config = ProviderConfig(
        provider=ProviderType.VLLM,
        model_name="openai/gpt-oss-20b-128k",
    )

    capabilities = config.get_model_capabilities()

    assert capabilities.streaming is True
    assert capabilities.tool_calling is True
    assert capabilities.max_context == 128_000
    assert config.check_function_calling_support() is True


def test_unknown_model_defaults_are_conservative() -> None:
    capabilities = infer_model_capabilities("local/custom-small-model", ProviderType.OLLAMA)

    assert capabilities.streaming is True
    assert capabilities.tool_calling is False
    assert capabilities.vision is False
    assert capabilities.reasoning_trace is False
    assert capabilities.max_context == 8192