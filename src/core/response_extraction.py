"""Utilities for extracting user-visible text from CrewAI results."""

from __future__ import annotations

from typing import Any


def extract_response_text(response: Any) -> str:
    """Extract text from common CrewAI result shapes."""
    if response is None:
        return ""
    raw = getattr(response, "raw", None)
    if raw is not None:
        return str(raw)
    if isinstance(response, dict):
        return str(response.get("response") or response.get("raw") or "")
    return str(response)


def clean_json_artifacts(value: str) -> str:
    """Return the response unchanged except for leading/trailing whitespace."""
    return value.strip()


def looks_like_internal_json(value: str) -> bool:
    """Detect internal-looking JSON strings."""
    stripped = value.strip()
    return stripped.startswith("{") and stripped.endswith("}")
