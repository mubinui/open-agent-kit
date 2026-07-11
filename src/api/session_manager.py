"""CrewAI-native session management for Open Agent Kit."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import structlog

from src.config.settings import get_settings
from src.config.workflow_registry import get_workflow_registry
from src.core.events import ResponseDelta, ResponseDeltaType, StreamEventBuilder
from src.crewai_runtime import CrewAIWorkflowRuntime
from src.memory.models import ConversationState, MessageRole

logger = structlog.get_logger(__name__)


class SessionManager:
    """Manage CrewAI chat sessions behind the existing REST API."""

    def __init__(self, runtime: CrewAIWorkflowRuntime | None = None) -> None:
        settings = get_settings()
        self.workflow_registry = get_workflow_registry()
        self.runtime = runtime or CrewAIWorkflowRuntime(
            memory_enabled=settings.app.crewai_memory_enabled,
            storage_dir=settings.app.crewai_storage_dir,
            default_process=settings.app.crewai_process_default,
        )
        self.storage_path = Path(settings.app.crewai_storage_dir) / "sessions.json"
        self._sessions: dict[str, ConversationState] = {}
        self._load_sessions()
        logger.info(
            "crewai_session_manager_initialized",
            memory_enabled=settings.app.crewai_memory_enabled,
            storage_dir=settings.app.crewai_storage_dir,
            restored_sessions=len(self._sessions),
        )

    async def create_session(
        self,
        workflow_id: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationState:
        """Create a session for a CrewAI workflow."""
        workflow = self.workflow_registry.get_workflow(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        now = datetime.utcnow()
        session = ConversationState(
            session_id=uuid4(),
            active=True,
            created_at=now,
            updated_at=now,
            turn_count=0,
            messages=[],
            agent_notes=[],
            metadata={
                "workflow_id": workflow_id,
                "user_id": user_id or "default_user",
                "runtime": "crewai",
                **(metadata or {}),
            },
        )
        self._sessions[str(session.session_id)] = session
        self._save_sessions()
        logger.info("crewai_session_created", session_id=session.session_id, workflow_id=workflow_id)
        return session

    async def get_session(self, session_id: UUID) -> ConversationState | None:
        """Return a session by ID."""
        return self._sessions.get(str(session_id))

    async def list_sessions(
        self,
        user_id: str | None = None,
        active_only: bool = True,
    ) -> list[ConversationState]:
        """List sessions from the in-process CrewAI session index."""
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [session for session in sessions if session.metadata.get("user_id") == user_id]
        if active_only:
            sessions = [session for session in sessions if session.active]
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session."""
        deleted = self._sessions.pop(str(session_id), None) is not None
        if deleted:
            self._save_sessions()
        return deleted

    async def process_message(
        self,
        session_id: UUID,
        message: str,
        max_turns: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process one message with CrewAI and return the legacy response DTO."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        if not session.active:
            raise ValueError(f"Session is no longer active: {session_id}")

        workflow_id = session.metadata.get("workflow_id")
        workflow = self.workflow_registry.get_workflow(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        session.add_message(MessageRole.USER, message, runtime="crewai")
        session.increment_turn()

        if max_turns and session.turn_count > max_turns:
            session.active = False
            response = "This session reached the configured turn limit. Start a new session to continue."
            session.add_message(MessageRole.ASSISTANT, response, runtime="crewai", limited=True)
            self._save_sessions()
            return self._response(session, response, {"runtime": "crewai", "limited": True})

        run_metadata = {
            "session_metadata": session.metadata,
            "history": session.conversation_history[-20:],
            **(metadata or {}),
        }
        result = await self.runtime.run_message(
            workflow=workflow,
            message=message,
            session_id=str(session_id),
            user_id=session.metadata.get("user_id", "default_user"),
            metadata=run_metadata,
        )

        response_text = result.response or "I could not generate a response."
        session.add_message(
            MessageRole.ASSISTANT,
            response_text,
            runtime="crewai",
            trace_steps=result.trace_steps,
        )
        session.metadata["last_trace_steps"] = result.trace_steps
        session.metadata["last_run"] = result.metadata
        session.updated_at = datetime.utcnow()
        self._save_sessions()

        return self._response(session, response_text, {**result.metadata, "trace_steps": result.trace_steps})

    async def stream_message(
        self,
        session_id: UUID,
        message: str,
        max_turns: int | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> AsyncIterator[ResponseDelta]:
        """Stream CrewAI execution through the existing SSE event schema."""
        builder = StreamEventBuilder(str(session_id), correlation_id=correlation_id)
        yield builder.delta(
            ResponseDeltaType.START,
            {"runtime": "crewai", "message_length": len(message), "metadata": metadata or {}},
        )
        try:
            result = await self.process_message(session_id, message, max_turns=max_turns, metadata=metadata)
            for step in result.get("metadata", {}).get("trace_steps", []):
                yield builder.delta(ResponseDeltaType.REASONING_DELTA, step)
            response = result.get("response", "")
            if response:
                yield builder.delta(ResponseDeltaType.TOKEN, {"text": response})
            yield builder.delta(
                ResponseDeltaType.DONE,
                {
                    "runtime": "crewai",
                    "turn_count": result.get("turn_count", 0),
                    "metadata": result.get("metadata", {}),
                },
            )
        except Exception as exc:
            logger.error("crewai_message_stream_failed", session_id=session_id, error=str(exc), exc_info=True)
            yield builder.delta(
                ResponseDeltaType.ERROR,
                {"error_type": type(exc).__name__, "error_message": str(exc), "runtime": "crewai"},
            )

    async def get_chat_history(self, session_id: UUID) -> dict[str, Any]:
        """Return chat history in the router's response shape."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        return {
            "session_id": session.session_id,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                    "timestamp": message.timestamp,
                    "metadata": message.metadata,
                }
                for message in session.messages
            ],
            "agent_notes": [
                {
                    "agent_type": note.agent_type.value,
                    "note_type": note.note_type,
                    "content": note.content,
                    "timestamp": note.timestamp,
                    "metadata": note.metadata,
                }
                for note in session.agent_notes
            ],
            "turn_count": session.turn_count,
            "active": session.active,
            "metadata": session.metadata,
        }

    def _response(
        self,
        session: ConversationState,
        response: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        meta = metadata or {}
        cost_info = {
            "cost_usd": meta.get("cost_usd", 0.0),
            "usage": meta.get("usage", {}),
        }
        return {
            "session_id": session.session_id,
            "response": response,
            "turn_count": session.turn_count,
            "chat_history": session.conversation_history,
            "summary": "",
            "safety_passed": True,
            "cost": cost_info,
            "metadata": {"runtime": "crewai", **meta},
        }

    def _load_sessions(self) -> None:
        """Restore persisted CrewAI sessions from local storage."""
        if not self.storage_path.exists():
            return
        try:
            payload = json.loads(self.storage_path.read_text())
            sessions = payload.get("sessions", payload if isinstance(payload, list) else [])
            for item in sessions:
                session = ConversationState.model_validate(item)
                self._sessions[str(session.session_id)] = session
        except Exception as exc:
            logger.warning("crewai_session_restore_failed", path=str(self.storage_path), error=str(exc))

    def _save_sessions(self) -> None:
        """Persist sessions so run history survives API restarts."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "runtime": "crewai",
                "updated_at": datetime.utcnow().isoformat(),
                "sessions": [
                    session.model_dump(mode="json")
                    for session in sorted(self._sessions.values(), key=lambda item: item.updated_at)
                ],
            }
            self.storage_path.write_text(json.dumps(payload, indent=2))
        except Exception as exc:
            logger.warning("crewai_session_persist_failed", path=str(self.storage_path), error=str(exc))


_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Return the process-wide CrewAI session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager() -> None:
    """Reset the global session manager for tests."""
    global _session_manager
    _session_manager = None
