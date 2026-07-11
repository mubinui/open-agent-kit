"""Unit tests for builder router helpers."""

import asyncio

import pytest
from fastapi import HTTPException

from src.api.routers import builder


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = "fake-response"

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return self._response


def test_call_llm_sync_raises_for_empty_message_content(monkeypatch):
    response = _FakeResponse({"choices": [{"message": {"content": None}}]})
    monkeypatch.setattr(builder.httpx, "AsyncClient", lambda timeout=120: _FakeAsyncClient(response))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            builder._call_llm_sync(
                "https://example.test",
                "fake-key",
                "google/gemini-3.1-flash-lite",
                [{"role": "user", "content": "Build a chatbot frontend"}],
            )
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "LLM provider returned an empty response."


def test_call_llm_sync_returns_message_content(monkeypatch):
    response = _FakeResponse({"choices": [{"message": {"content": "<html></html>"}}]})
    monkeypatch.setattr(builder.httpx, "AsyncClient", lambda timeout=120: _FakeAsyncClient(response))

    result = asyncio.run(
        builder._call_llm_sync(
            "https://example.test",
            "fake-key",
            "google/gemini-3.1-flash-lite",
            [{"role": "user", "content": "Build a chatbot frontend"}],
        )
    )

    assert result == "<html></html>"
