"""create_pdf_documents_table

Revision ID: 20260223_1256
Revises: e71b034aedb7
Create Date: 2026-02-23 12:56:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20260223_1256'
down_revision = 'e71b034aedb7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ProcessingStatus enum
    processing_status_enum = sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='processingstatus')
    processing_status_enum.create(op.get_bind())
    
    # Create pdf_documents table
    op.create_table(
        'pdf_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('processing_status', processing_status_enum, nullable=False),
        sa.Column('extracted_data', JSONB, nullable=True),
        sa.Column('confidence_scores', JSONB, nullable=True),
        sa.Column('uploaded_by', UUID(as_uuid=True), nullable=True),
    )
    
    # Create index
    op.create_index('idx_processing_status', 'pdf_documents', ['processing_status'])
    
    # Add foreign key constraint to schemes table for source_pdf_id
    op.create_foreign_key(
        'fk_schemes_source_pdf_id',
        'schemes',
        'pdf_documents',
        ['source_pdf_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key constraint from schemes table
    op.drop_constraint('fk_schemes_source_pdf_id', 'schemes', type_='foreignkey')
    
    # Drop index
    op.drop_index('idx_processing_status', 'pdf_documents')
    
    # Drop table
    op.drop_table('pdf_documents')
    
    # Drop enum
    sa.Enum(name='processingstatus').drop(op.get_bind())
