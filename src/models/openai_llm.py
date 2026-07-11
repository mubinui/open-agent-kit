"""OpenAI-compatible model helpers for CrewAI provider configuration."""

from __future__ import annotations


def normalize_openai_model_name(model: str, provider: str = "openrouter") -> str:
    """Return a LiteLLM/CrewAI-friendly model name."""
    if "/" in model and not model.startswith(f"{provider}/"):
        return f"{provider}/{model}"
    return model
