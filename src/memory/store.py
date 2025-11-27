"""Abstract base class for conversation store implementations."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.memory.models import ConversationState


class ConversationStore(ABC):
    """Abstract interface for conversation persistence."""

    @abstractmethod
    async def create_session(self) -> ConversationState:
        """Create a new conversation session."""
        pass

    @abstractmethod
    async def get_session(self, session_id: UUID) -> ConversationState | None:
        """Retrieve a conversation session by ID."""
        pass

    @abstractmethod
    async def update_session(self, state: ConversationState) -> None:
        """Update an existing conversation session."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a conversation session."""
        pass

    @abstractmethod
    async def list_sessions(self, active_only: bool = True) -> list[ConversationState]:
        """List all conversation sessions."""
        pass
