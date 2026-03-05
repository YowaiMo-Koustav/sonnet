"""create_schemes_table

Revision ID: e71b034aedb7
Revises: 027e910acaf6
Create Date: 2026-02-14 18:01:23.740198

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'e71b034aedb7'
down_revision = '027e910acaf6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create SchemeType enum
    scheme_type_enum = sa.Enum('SCHOLARSHIP', 'GRANT', 'JOB', 'INTERNSHIP', name='schemetype')
    scheme_type_enum.create(op.get_bind())
    
    # Create SchemeStatus enum
    scheme_status_enum = sa.Enum('ACTIVE', 'CLOSED', 'DRAFT', name='schemestatus')
    scheme_status_enum.create(op.get_bind())
    
    # Create EducationLevel enum
    education_level_enum = sa.Enum(
        'PRIMARY', 'SECONDARY', 'HIGHER_SECONDARY', 'UNDERGRADUATE', 'POSTGRADUATE',
        name='educationlevel'
    )
    education_level_enum.create(op.get_bind())
    
    # Create Gender enum
    gender_enum = sa.Enum('MALE', 'FEMALE', 'OTHER', 'ANY', name='gender')
    gender_enum.create(op.get_bind())
    
    # Create schemes table
    op.create_table(
        'schemes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=False),
        sa.Column('scheme_type', scheme_type_enum, nullable=False),
        sa.Column('eligibility_criteria', JSONB, nullable=False),
        sa.Column('required_documents', JSONB, nullable=False),
        sa.Column('deadline', sa.Date, nullable=True),
        sa.Column('application_url', sa.String(1000), nullable=True),
        sa.Column('source_pdf_id', UUID(as_uuid=True), nullable=True),
        sa.Column('status', scheme_status_enum, nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_location_id', 'schemes', ['location_id'])
    op.create_index('idx_scheme_type', 'schemes', ['scheme_type'])
    op.create_index('idx_deadline', 'schemes', ['deadline'])
    op.create_index('idx_status', 'schemes', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_status', 'schemes')
    op.drop_index('idx_deadline', 'schemes')
    op.drop_index('idx_scheme_type', 'schemes')
    op.drop_index('idx_location_id', 'schemes')
    
    # Drop table
    op.drop_table('schemes')
    
    # Drop enums
    sa.Enum(name='gender').drop(op.get_bind())
    sa.Enum(name='educationlevel').drop(op.get_bind())
    sa.Enum(name='schemestatus').drop(op.get_bind())
    sa.Enum(name='schemetype').drop(op.get_bind())

