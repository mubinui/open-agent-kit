"""SQLAlchemy database schema for conversation storage."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from src.memory.models import AgentType, MessageRole

Base = declarative_base()


class Session(Base):
    """Database model for conversation sessions."""

    __tablename__ = "sessions"

    session_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    turn_count = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_metadata = Column(JSON, nullable=False, default=dict)

    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    agent_notes = relationship("AgentNote", back_populates="session", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index("idx_sessions_active", "active"),
        Index("idx_sessions_created_at", "created_at"),
        Index("idx_sessions_updated_at", "updated_at"),
    )


class Message(Base):
    """Database model for conversation messages."""

    __tablename__ = "messages"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    message_metadata = Column(JSON, nullable=False, default=dict)

    # Relationships
    session = relationship("Session", back_populates="messages")

    # Indexes for performance
    __table_args__ = (
        Index("idx_messages_session_id", "session_id"),
        Index("idx_messages_timestamp", "timestamp"),
        Index("idx_messages_role", "role"),
    )


class AgentNote(Base):
    """Database model for agent notes and decisions."""

    __tablename__ = "agent_notes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_type = Column(Enum(AgentType), nullable=False)
    note_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    note_metadata = Column(JSON, nullable=False, default=dict)

    # Relationships
    session = relationship("Session", back_populates="agent_notes")

    # Indexes for performance
    __table_args__ = (
        Index("idx_agent_notes_session_id", "session_id"),
        Index("idx_agent_notes_agent_type", "agent_type"),
        Index("idx_agent_notes_note_type", "note_type"),
        Index("idx_agent_notes_timestamp", "timestamp"),
    )


class ConfigSnapshot(Base):
    """Database model for configuration snapshots."""

    __tablename__ = "config_snapshots"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    config_type = Column(String(50), nullable=False)  # 'agent', 'workflow', 'tool', 'vector_db'
    config_id = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False)
    etag = Column(String(64), nullable=False)  # SHA256 hash
    config_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)  # User identity
    change_summary = Column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("idx_config_snapshots_type_id", "config_type", "config_id"),
        Index("idx_config_snapshots_version", "config_type", "config_id", "version"),
        Index("idx_config_snapshots_created_at", "created_at"),
    )
