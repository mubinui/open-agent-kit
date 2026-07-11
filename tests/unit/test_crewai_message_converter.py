"""Tests for CrewAI-facing message conversion helpers."""

from dataclasses import dataclass
from datetime import datetime

from src.utils.message_converter import MessageConverter


@dataclass
class FakeRole:
    value: str


@dataclass
class FakeMessage:
    role: FakeRole
    content: str
    timestamp: datetime
    metadata: dict


def test_message_converter_serializes_platform_message() -> None:
    message = FakeMessage(
        role=FakeRole("assistant"),
        content="hello",
        timestamp=datetime(2026, 5, 13),
        metadata={"runtime": "crewai"},
    )

    assert MessageConverter.message_to_dict(message) == {
        "role": "assistant",
        "content": "hello",
        "timestamp": "2026-05-13T00:00:00",
        "metadata": {"runtime": "crewai"},
    }
