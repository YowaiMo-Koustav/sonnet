import enum
import uuid
from sqlalchemy import Column, String, Enum, ForeignKey, Index, BigInteger

from app.core.database import Base
from app.models.location import GUID, JSON


class ProcessingStatus(str, enum.Enum):
    """Enum for PDF processing status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PDFDocument(Base):
    """
    PDFDocument model representing uploaded PDF files.
    
    Stores metadata about uploaded PDFs and their processing status.
    Contains extracted data and confidence scores as JSONB fields.
    """
    __tablename__ = "pdf_documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=True)
    processing_status = Column(Enum(ProcessingStatus), nullable=False, server_default='PENDING')
    extracted_data = Column(JSON(), nullable=True)
    confidence_scores = Column(JSON(), nullable=True)
    uploaded_by = Column(GUID(), nullable=True)  # Will be FK to users table later
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.processing_status is None:
            self.processing_status = ProcessingStatus.PENDING

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_processing_status", "processing_status"),
    )

    def __repr__(self):
        return f"<PDFDocument(id={self.id}, filename='{self.filename}', status={self.processing_status})>"
