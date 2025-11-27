"""add_auth_tables

Revision ID: 7f4271a7a773
Revises: 9a89de92579f
Create Date: 2025-11-16 11:44:49.964682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f4271a7a773'
down_revision: Union[str, Sequence[str], None] = '9a89de92579f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_role enum
    user_role_enum = sa.Enum('admin', 'user', 'readonly', name='userrole')
    user_role_enum.create(op.get_bind())
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(255), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False, default='user'),
        sa.Column('active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime, nullable=True),
    )
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('encrypted_key', sa.Text, nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('role', user_role_enum, nullable=False, default='user'),
        sa.Column('active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_active', 'users', ['active'])
    op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_keys_active', 'api_keys', ['active'])
    op.create_index('idx_api_keys_user_id', 'api_keys', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_api_keys_user_id')
    op.drop_index('idx_api_keys_active')
    op.drop_index('idx_api_keys_key_hash')
    op.drop_index('idx_users_active')
    op.drop_index('idx_users_email')
    op.drop_index('idx_users_username')
    
    # Drop tables
    op.drop_table('api_keys')
    op.drop_table('users')
    
    # Drop enum
    sa.Enum(name='userrole').drop(op.get_bind())
