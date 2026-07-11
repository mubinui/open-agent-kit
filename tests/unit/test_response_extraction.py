"""Tests for CrewAI response text extraction."""

from src.core.response_extraction import extract_response_text, looks_like_internal_json


class FakeCrewResult:
    raw = "visible answer"


def test_extract_response_text_reads_crewai_raw_result() -> None:
    assert extract_response_text(FakeCrewResult()) == "visible answer"


def test_internal_json_detection_keeps_regular_text() -> None:
    assert looks_like_internal_json('{"agent_name": "search"}') is True
    assert looks_like_internal_json("regular user-visible answer") is False
