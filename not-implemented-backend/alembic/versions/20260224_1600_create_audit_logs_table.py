"""create_audit_logs_table

Revision ID: 20260224_1600
Revises: 20260224_1400
Create Date: 2026-02-24 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '20260224_1600'
down_revision = '20260224_1400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('admin_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('scheme_id', UUID(as_uuid=True), sa.ForeignKey('schemes.id'), nullable=False),
        sa.Column('field_name', sa.String(255), nullable=False),
        sa.Column('old_value', sa.Text, nullable=True),
        sa.Column('new_value', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_admin_id', 'audit_logs', ['admin_id'])
    op.create_index('idx_scheme_id', 'audit_logs', ['scheme_id'])
    op.create_index('idx_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_timestamp', 'audit_logs')
    op.drop_index('idx_scheme_id', 'audit_logs')
    op.drop_index('idx_admin_id', 'audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')
