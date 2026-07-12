"""add integration_credentials

Revision ID: a3d9f10b7c42
Revises: fc80e29dcd57
Create Date: 2026-07-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d9f10b7c42'
down_revision: Union[str, Sequence[str], None] = 'fc80e29dcd57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'integration_credentials',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('encrypted_token', sa.Text(), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('token_expiry', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_integration_provider_email',
        'integration_credentials',
        ['provider', 'account_email'],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_integration_provider_email', table_name='integration_credentials')
    op.drop_table('integration_credentials')
