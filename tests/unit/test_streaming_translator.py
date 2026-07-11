"""Tests for CrewAI result to ResponseDelta translation."""

import asyncio

from src.core.events import ResponseDeltaType, StreamEventBuilder
from src.core.streaming import stream_crewai_result


def test_stream_crewai_result_emits_trace_token_and_done() -> None:
    async def collect():
        builder = StreamEventBuilder("session-1", correlation_id="request-1")
        return [
            delta
            async for delta in stream_crewai_result(
                builder,
                {
                    "response": "Policy found",
                    "metadata": {
                        "trace_steps": [{"type": "tool", "description": "lookup_policy"}],
                    },
                },
            )
        ]

    deltas = asyncio.run(collect())

    assert [delta.type for delta in deltas] == [
        ResponseDeltaType.REASONING_DELTA,
        ResponseDeltaType.TOKEN,
        ResponseDeltaType.DONE,
    ]
    assert deltas[0].payload["type"] == "tool"
    assert deltas[1].payload["text"] == "Policy found"
    assert deltas[2].payload["runtime"] == "crewai"
