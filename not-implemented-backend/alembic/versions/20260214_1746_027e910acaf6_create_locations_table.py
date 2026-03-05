"""Create locations table

Revision ID: 027e910acaf6
Revises: 
Create Date: 2026-02-14 17:46:42.741751

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '027e910acaf6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # LocationType enum should already exist or be created manually
    # If it doesn't exist, create it: CREATE TYPE locationtype AS ENUM ('COUNTRY', 'STATE', 'DISTRICT');
    
    # Create locations table
    op.create_table(
        'locations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.Enum('COUNTRY', 'STATE', 'DISTRICT', name='locationtype', create_type=False), nullable=False),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('materialized_path', sa.String(1000), nullable=True),
        sa.Column('location_metadata', JSONB, nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_parent_id', 'locations', ['parent_id'])
    op.create_index('idx_materialized_path', 'locations', ['materialized_path'])
    op.create_index('idx_name', 'locations', ['name'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_name', 'locations')
    op.drop_index('idx_materialized_path', 'locations')
    op.drop_index('idx_parent_id', 'locations')
    
    # Drop table
    op.drop_table('locations')
    
    # Drop enum
    sa.Enum(name='locationtype').drop(op.get_bind())
