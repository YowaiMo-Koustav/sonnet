"""create_applications_table

Revision ID: 20260224_1400
Revises: 20260223_1635
Create Date: 2026-02-24 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20260224_1400'
down_revision = '20260223_1635'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create applications table
    op.create_table(
        'applications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('scheme_id', UUID(as_uuid=True), sa.ForeignKey('schemes.id'), nullable=False),
        sa.Column('status', sa.Enum('INTERESTED', 'IN_PROGRESS', 'SUBMITTED', 'UNDER_REVIEW', 'ACCEPTED', 'REJECTED', name='applicationstatus'), nullable=False),
        sa.Column('status_history', JSONB, nullable=False, server_default='[]'),
        sa.Column('notes', sa.Text, nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_user_id', 'applications', ['user_id'])
    op.create_index('idx_scheme_id', 'applications', ['scheme_id'])
    op.create_index('idx_status', 'applications', ['status'])
    
    # Create unique constraint on (user_id, scheme_id)
    op.create_unique_constraint('idx_user_scheme', 'applications', ['user_id', 'scheme_id'])


def downgrade() -> None:
    # Drop unique constraint
    op.drop_constraint('idx_user_scheme', 'applications', type_='unique')
    
    # Drop indexes
    op.drop_index('idx_status', 'applications')
    op.drop_index('idx_scheme_id', 'applications')
    op.drop_index('idx_user_id', 'applications')
    
    # Drop table
    op.drop_table('applications')
    
    # Drop enum type
    op.execute('DROP TYPE applicationstatus')
