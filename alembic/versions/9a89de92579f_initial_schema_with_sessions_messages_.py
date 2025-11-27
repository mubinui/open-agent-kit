"""Initial schema with sessions, messages, and agent_notes

Revision ID: 9a89de92579f
Revises: 
Create Date: 2025-11-13 11:46:30.759310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a89de92579f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types
    message_role_enum = postgresql.ENUM('user', 'assistant', 'system', 'agent', name='messagerole')
    message_role_enum.create(op.get_bind())
    
    agent_type_enum = postgresql.ENUM('orchestrator', 'reasoning', 'knowledge', 'response', name='agenttype')
    agent_type_enum.create(op.get_bind())
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('turn_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('session_metadata', postgresql.JSON(), nullable=False, server_default='{}'),
    )
    
    # Create indexes for sessions
    op.create_index('idx_sessions_active', 'sessions', ['active'])
    op.create_index('idx_sessions_created_at', 'sessions', ['created_at'])
    op.create_index('idx_sessions_updated_at', 'sessions', ['updated_at'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', message_role_enum, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('message_metadata', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ondelete='CASCADE'),
    )
    
    # Create indexes for messages
    op.create_index('idx_messages_session_id', 'messages', ['session_id'])
    op.create_index('idx_messages_timestamp', 'messages', ['timestamp'])
    op.create_index('idx_messages_role', 'messages', ['role'])
    
    # Create agent_notes table
    op.create_table(
        'agent_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', agent_type_enum, nullable=False),
        sa.Column('note_type', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('note_metadata', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ondelete='CASCADE'),
    )
    
    # Create indexes for agent_notes
    op.create_index('idx_agent_notes_session_id', 'agent_notes', ['session_id'])
    op.create_index('idx_agent_notes_agent_type', 'agent_notes', ['agent_type'])
    op.create_index('idx_agent_notes_note_type', 'agent_notes', ['note_type'])
    op.create_index('idx_agent_notes_timestamp', 'agent_notes', ['timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables
    op.drop_table('agent_notes')
    op.drop_table('messages')
    op.drop_table('sessions')
    
    # Drop enum types
    op.execute('DROP TYPE agenttype')
    op.execute('DROP TYPE messagerole')
