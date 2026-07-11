"""Model capability inference for provider feature gating."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCapabilities:
    """Feature flags inferred for a configured model."""

    streaming: bool = True
    tool_calling: bool = False
    vision: bool = False
    audio_in: bool = False
    audio_out: bool = False
    reasoning_trace: bool = False
    json_schema: bool = False
    max_context: int = 8192


def infer_model_capabilities(model_name: str, provider: str | None = None) -> ModelCapabilities:
    """Infer model capabilities from common provider/model naming patterns."""
    model_lower = model_name.lower()
    provider = provider or "openrouter"

    tool_calling_markers = (
        "gpt-4",
        "gpt-4o",
        "gpt-oss",
        "o1",
        "o3",
        "o4",
        "claude-3",
        "claude-3.5",
        "claude-3-5",
        "claude-3.7",
        "claude-3-7",
        "gemini",
        "mistral",
        "mixtral",
        "deepseek",
        "qwen",
        "llama-3.1",
        "llama-3.2",
        "llama-3.3",
    )
    vision_markers = (
        "gpt-4o",
        "vision",
        "claude-3",
        "gemini",
        "qwen-vl",
        "qwen2-vl",
        "llava",
        "pixtral",
        "mllama",
        "llama-3.2-vision",
    )
    audio_markers = ("audio", "realtime", "speech", "gemini-live", "live")
    reasoning_markers = (
        "o1",
        "o3",
        "o4",
        "deepseek-r1",
        "qwq",
        "qwen-qwq",
        "reasoning",
    )
    json_schema_markers = (
        "gpt-4",
        "gpt-4o",
        "gpt-oss",
        "o1",
        "o3",
        "o4",
        "gemini",
        "claude-3",
        "mistral",
        "deepseek",
        "qwen",
    )

    return ModelCapabilities(
        streaming=provider in {"openrouter", "vllm", "ollama"},
        tool_calling=_contains_any(model_lower, tool_calling_markers),
        vision=_contains_any(model_lower, vision_markers),
        audio_in=_contains_any(model_lower, audio_markers),
        audio_out=_contains_any(model_lower, audio_markers),
        reasoning_trace=_contains_any(model_lower, reasoning_markers),
        json_schema=_contains_any(model_lower, json_schema_markers),
        max_context=_infer_max_context(model_lower),
    )


def _contains_any(value: str, markers: tuple[str, ...]) -> bool:
    """Return whether any marker appears in the value."""
    return any(marker in value for marker in markers)


def _infer_max_context(model_lower: str) -> int:
    """Infer approximate maximum context window from model naming conventions."""
    context_markers = (
        ("1m", 1_000_000),
        ("2m", 2_000_000),
        ("200k", 200_000),
        ("128k", 128_000),
        ("120k", 120_000),
        ("100k", 100_000),
        ("64k", 64_000),
        ("32k", 32_000),
        ("16k", 16_000),
    )
    max_context = 8192

    for marker, context_size in context_markers:
        if marker in model_lower:
            max_context = context_size
            break

    if _contains_any(model_lower, ("gemini-1.5", "gemini-2", "gemini-pro")):
        return max(max_context, 1_000_000)
    if _contains_any(
        model_lower,
        ("claude-3", "claude-3.5", "claude-3-5", "claude-3.7", "claude-3-7"),
    ):
        return max(max_context, 200_000)
    if _contains_any(model_lower, ("gpt-4o", "gpt-oss", "o1", "o3", "o4")):
        return max(max_context, 128_000)

    return max_context