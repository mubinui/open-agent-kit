"""MongoDB implementation of ConversationStore for chatbot workflows."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

from src.memory.models import (
    AgentNote,
    ConversationState,
    Message,
    MessageRole,
)
from src.memory.store import ConversationStore

logger = logging.getLogger(__name__)


class MongoDBConversationStore(ConversationStore):
    """MongoDB-backed conversation store for chatbot workflows with TTL support."""

    def __init__(
        self,
        connection_string: str,
        database_name: str = "orchestration",
        pool_size: int = 10,
        max_idle_time_ms: int = 45000,
        server_selection_timeout_ms: int = 5000,
    ):
        """Initialize MongoDB conversation store.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
            pool_size: Maximum number of connections in the pool
            max_idle_time_ms: Maximum idle time for connections
            server_selection_timeout_ms: Timeout for server selection
        """
        self.connection_string = connection_string
        self.database_name = database_name
        
        # Initialize MongoDB client with connection pooling
        self.client: MongoClient = MongoClient(
            connection_string,
            maxPoolSize=pool_size,
            maxIdleTimeMS=max_idle_time_ms,
            serverSelectionTimeoutMS=server_selection_timeout_ms,
            retryWrites=True,
            retryReads=True,
        )
        
        # Get database
        self.db: Database = self.client[database_name]
        
        # Get collections
        self.sessions_collection: Collection = self.db["sessions"]
        self.messages_collection: Collection = self.db["messages"]
        self.transcripts_collection: Collection = self.db["transcripts"]
        
        logger.info(
            f"MongoDB conversation store initialized",
            database=database_name,
            pool_size=pool_size,
        )

    async def create_session(self) -> ConversationState:
        """Create a new conversation session.

        Returns:
            ConversationState: Newly created session
        """
        try:
            # Create session document
            session_doc = {
                "turn_count": 0,
                "active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metadata": {},
            }
            
            # Insert into MongoDB
            result = self.sessions_collection.insert_one(session_doc)
            session_id = result.inserted_id
            
            # Convert to ConversationState
            state = ConversationState(
                session_id=UUID(str(session_id)),
                messages=[],
                agent_notes=[],
                turn_count=0,
                active=True,
                created_at=session_doc["created_at"],
                updated_at=session_doc["updated_at"],
                metadata={},
            )
            
            logger.info(f"Created MongoDB session: {session_id}")
            
            return state
            
        except PyMongoError as e:
            logger.error(f"Failed to create MongoDB session: {e}")
            raise

    async def get_session(self, session_id: UUID) -> Optional[ConversationState]:
        """Retrieve a conversation session by ID.

        Args:
            session_id: UUID of the session to retrieve

        Returns:
            ConversationState if found, None otherwise
        """
        try:
            # Query session document
            session_doc = self.sessions_collection.find_one(
                {"_id": str(session_id)}
            )
            
            if session_doc is None:
                return None
            
            # Query messages for this session
            messages_cursor = self.messages_collection.find(
                {"session_id": str(session_id)}
            ).sort("timestamp", ASCENDING)
            
            messages = []
            agent_notes = []
            
            for msg_doc in messages_cursor:
                # Check if this is an agent note or regular message
                if msg_doc.get("is_agent_note", False):
                    agent_note = AgentNote(
                        id=UUID(msg_doc["_id"]),
                        agent_type=msg_doc["agent_type"],
                        note_type=msg_doc["note_type"],
                        content=msg_doc["content"],
                        timestamp=msg_doc["timestamp"],
                        metadata=msg_doc.get("metadata", {}),
                    )
                    agent_notes.append(agent_note)
                else:
                    message = Message(
                        id=UUID(msg_doc["_id"]),
                        role=MessageRole(msg_doc["role"]),
                        content=msg_doc["content"],
                        timestamp=msg_doc["timestamp"],
                        metadata=msg_doc.get("metadata", {}),
                    )
                    messages.append(message)
            
            # Convert to ConversationState
            state = ConversationState(
                session_id=session_id,
                messages=messages,
                agent_notes=agent_notes,
                turn_count=session_doc["turn_count"],
                active=session_doc["active"],
                created_at=session_doc["created_at"],
                updated_at=session_doc["updated_at"],
                metadata=session_doc.get("metadata", {}),
            )
            
            return state
            
        except PyMongoError as e:
            logger.error(f"Failed to get MongoDB session {session_id}: {e}")
            raise

    async def update_session(self, state: ConversationState) -> None:
        """Update an existing conversation session.

        Args:
            state: ConversationState to update
        """
        try:
            session_id_str = str(state.session_id)
            
            # Update session document
            update_doc = {
                "$set": {
                    "turn_count": state.turn_count,
                    "active": state.active,
                    "updated_at": datetime.utcnow(),
                    "metadata": state.metadata,
                }
            }
            
            result = self.sessions_collection.update_one(
                {"_id": session_id_str},
                update_doc,
                upsert=False,
            )
            
            if result.matched_count == 0:
                raise ValueError(f"Session {state.session_id} not found")
            
            # Get existing message IDs
            existing_messages = set()
            for msg_doc in self.messages_collection.find(
                {"session_id": session_id_str},
                {"_id": 1}
            ):
                existing_messages.add(msg_doc["_id"])
            
            # Insert new messages
            new_messages = []
            for message in state.messages:
                msg_id_str = str(message.id)
                if msg_id_str not in existing_messages:
                    msg_doc = {
                        "_id": msg_id_str,
                        "session_id": session_id_str,
                        "role": message.role.value,
                        "content": message.content,
                        "timestamp": message.timestamp,
                        "created_at": datetime.utcnow(),
                        "metadata": message.metadata,
                        "is_agent_note": False,
                    }
                    new_messages.append(msg_doc)
            
            # Insert new agent notes
            new_notes = []
            for note in state.agent_notes:
                note_id_str = str(note.id)
                if note_id_str not in existing_messages:
                    note_doc = {
                        "_id": note_id_str,
                        "session_id": session_id_str,
                        "agent_type": note.agent_type.value,
                        "note_type": note.note_type,
                        "content": note.content,
                        "timestamp": note.timestamp,
                        "created_at": datetime.utcnow(),
                        "metadata": note.metadata,
                        "is_agent_note": True,
                    }
                    new_notes.append(note_doc)
            
            # Bulk insert new messages and notes
            if new_messages:
                self.messages_collection.insert_many(new_messages, ordered=False)
            
            if new_notes:
                self.messages_collection.insert_many(new_notes, ordered=False)
            
            logger.debug(
                f"Updated MongoDB session {state.session_id}: "
                f"{len(new_messages)} new messages, {len(new_notes)} new notes"
            )
            
        except PyMongoError as e:
            logger.error(f"Failed to update MongoDB session {state.session_id}: {e}")
            raise

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a conversation session.

        Args:
            session_id: UUID of the session to delete

        Returns:
            True if session was deleted, False if not found
        """
        try:
            session_id_str = str(session_id)
            
            # Delete messages first
            self.messages_collection.delete_many({"session_id": session_id_str})
            
            # Delete session
            result = self.sessions_collection.delete_one({"_id": session_id_str})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted MongoDB session: {session_id}")
                return True
            else:
                logger.warning(f"MongoDB session not found for deletion: {session_id}")
                return False
                
        except PyMongoError as e:
            logger.error(f"Failed to delete MongoDB session {session_id}: {e}")
            raise

    async def list_sessions(self, active_only: bool = True) -> list[ConversationState]:
        """List all conversation sessions.

        Args:
            active_only: If True, only return active sessions

        Returns:
            List of ConversationState objects
        """
        try:
            # Build query
            query: Dict[str, Any] = {}
            if active_only:
                query["active"] = True
            
            # Query sessions
            sessions_cursor = self.sessions_collection.find(query).sort(
                "updated_at", DESCENDING
            )
            
            # Convert to ConversationState objects
            states = []
            for session_doc in sessions_cursor:
                session_id = UUID(session_doc["_id"])
                state = await self.get_session(session_id)
                if state:
                    states.append(state)
            
            return states
            
        except PyMongoError as e:
            logger.error(f"Failed to list MongoDB sessions: {e}")
            raise

    def create_indexes(self) -> None:
        """Create TTL and query optimization indexes.
        
        This method should be called during application startup or via
        bootstrap scripts to ensure indexes are created.
        """
        try:
            # Sessions collection indexes
            # TTL index: expire sessions after 24 hours of inactivity
            self.sessions_collection.create_index(
                "updated_at",
                expireAfterSeconds=86400,
                name="ttl_updated_at",
            )
            
            # Index for active sessions query
            self.sessions_collection.create_index(
                [("active", ASCENDING), ("updated_at", DESCENDING)],
                name="active_updated_idx",
            )
            
            # Messages collection indexes
            # TTL index: expire messages after 7 days
            self.messages_collection.create_index(
                "created_at",
                expireAfterSeconds=604800,
                name="ttl_created_at",
            )
            
            # Compound index for session queries
            self.messages_collection.create_index(
                [("session_id", ASCENDING), ("timestamp", ASCENDING)],
                name="session_timestamp_idx",
            )
            
            # Index for agent notes queries
            self.messages_collection.create_index(
                [("session_id", ASCENDING), ("is_agent_note", ASCENDING)],
                name="session_agent_note_idx",
            )
            
            # Transcripts collection indexes
            # TTL index: expire transcripts after 30 days
            self.transcripts_collection.create_index(
                "created_at",
                expireAfterSeconds=2592000,
                name="ttl_created_at",
            )
            
            # Index for session lookup
            self.transcripts_collection.create_index(
                "session_id",
                name="session_id_idx",
            )
            
            logger.info("MongoDB indexes created successfully")
            
        except PyMongoError as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")
            raise

    def health_check(self) -> bool:
        """Check if MongoDB connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Ping the database
            self.client.admin.command("ping")
            logger.debug("MongoDB health check passed")
            return True
        except ConnectionFailure as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB health check error: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get MongoDB connection information.

        Returns:
            Dictionary with connection details
        """
        try:
            server_info = self.client.server_info()
            return {
                "database": self.database_name,
                "version": server_info.get("version", "unknown"),
                "connected": True,
            }
        except Exception as e:
            logger.error(f"Failed to get MongoDB connection info: {e}")
            return {
                "database": self.database_name,
                "connected": False,
                "error": str(e),
            }

    def close(self) -> None:
        """Close MongoDB connections and cleanup resources."""
        try:
            self.client.close()
            logger.info("MongoDB connections closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connections: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
