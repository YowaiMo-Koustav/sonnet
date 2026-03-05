"""create_users_table

Revision ID: 20260223_1635
Revises: 20260223_1256
Create Date: 2026-02-23 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20260223_1635'
down_revision = '20260223_1256'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('profile', JSONB, nullable=False, server_default='{}'),
        sa.Column('location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True),
    )
    
    # Create index
    op.create_index('idx_location_id', 'users', ['location_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_location_id', 'users')
    
    # Drop table
    op.drop_table('users')
