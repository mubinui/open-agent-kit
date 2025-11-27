"""Observability module for metrics, tracing, and logging."""

from src.observability.metrics import (
    get_metrics_registry,
    track_agent_conversation,
    track_agent_error,
    track_agent_turn,
    track_cache_hit,
    track_cache_miss,
    track_http_request,
    track_llm_call,
    track_llm_cost,
    track_llm_tokens,
    track_queue_depth,
)
from src.observability.tracing import (
    add_span_event,
    configure_tracing,
    get_tracer,
    instrument_fastapi,
    set_span_error,
    trace_agent_conversation,
    trace_cache_operation,
    trace_database_query,
    trace_llm_call,
    trace_tool_execution,
)

__all__ = [
    # Metrics
    "get_metrics_registry",
    "track_http_request",
    "track_agent_conversation",
    "track_agent_turn",
    "track_agent_error",
    "track_llm_call",
    "track_llm_tokens",
    "track_llm_cost",
    "track_cache_hit",
    "track_cache_miss",
    "track_queue_depth",
    # Tracing
    "configure_tracing",
    "instrument_fastapi",
    "get_tracer",
    "trace_agent_conversation",
    "trace_llm_call",
    "trace_tool_execution",
    "trace_database_query",
    "trace_cache_operation",
    "add_span_event",
    "set_span_error",
]
