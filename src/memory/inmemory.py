"""In-memory implementation of the conversation store."""

from uuid import UUID

from src.memory.models import ConversationState
from src.memory.store import ConversationStore


class InMemoryConversationStore(ConversationStore):
    """In-memory conversation store for development and testing."""

    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._sessions: dict[UUID, ConversationState] = {}

    async def create_session(self) -> ConversationState:
        """Create a new conversation session."""
        state = ConversationState()
        self._sessions[state.session_id] = state
        return state

    async def get_session(self, session_id: UUID) -> ConversationState | None:
        """Retrieve a conversation session by ID."""
        return self._sessions.get(session_id)

    async def update_session(self, state: ConversationState) -> None:
        """Update an existing conversation session."""
        if state.session_id not in self._sessions:
            raise ValueError(f"Session {state.session_id} does not exist")
        self._sessions[state.session_id] = state

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a conversation session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def list_sessions(self, active_only: bool = True) -> list[ConversationState]:
        """List all conversation sessions."""
        sessions = list(self._sessions.values())
        if active_only:
            sessions = [s for s in sessions if s.active]
        return sessions

    def clear_all(self) -> None:
        """Clear all sessions (useful for testing)."""
        self._sessions.clear()
