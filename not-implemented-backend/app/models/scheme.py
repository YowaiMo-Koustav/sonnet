import enum
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Enum, ForeignKey, Index, Date, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.location import GUID, JSON


class SchemeType(str, enum.Enum):
    """Enum for scheme types."""
    SCHOLARSHIP = "SCHOLARSHIP"
    GRANT = "GRANT"
    JOB = "JOB"
    INTERNSHIP = "INTERNSHIP"


class SchemeStatus(str, enum.Enum):
    """Enum for scheme status."""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    DRAFT = "DRAFT"


class EducationLevel(str, enum.Enum):
    """Enum for education levels."""
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    HIGHER_SECONDARY = "HIGHER_SECONDARY"
    UNDERGRADUATE = "UNDERGRADUATE"
    POSTGRADUATE = "POSTGRADUATE"


class Gender(str, enum.Enum):
    """Enum for gender eligibility."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    ANY = "ANY"


class Scheme(Base):
    """
    Scheme model representing scholarships, grants, jobs, and internships.
    
    Contains eligibility criteria and required documents as JSONB fields.
    Associated with a location in the hierarchy.
    
    Note: For PostgreSQL, a search_vector column is added via migration
    for full-text search capabilities. This column is not declared here
    to maintain SQLite compatibility in tests.
    """
    __tablename__ = "schemes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location_id = Column(GUID(), ForeignKey("locations.id"), nullable=False)
    scheme_type = Column(Enum(SchemeType), nullable=False)
    eligibility_criteria = Column(JSON(), nullable=False, server_default='{}')
    required_documents = Column(JSON(), nullable=False, server_default='[]')
    deadline = Column(Date, nullable=True)
    application_url = Column(String(1000), nullable=True)
    source_pdf_id = Column(GUID(), nullable=True)  # Will be FK to pdf_documents later
    status = Column(Enum(SchemeStatus), nullable=False, server_default='DRAFT')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.eligibility_criteria is None:
            self.eligibility_criteria = {}
        if self.required_documents is None:
            self.required_documents = []
        if self.status is None:
            self.status = SchemeStatus.DRAFT

    # Relationships
    location = relationship("Location", backref="schemes")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_location_id", "location_id"),
        Index("idx_scheme_type", "scheme_type"),
        Index("idx_deadline", "deadline"),
        Index("idx_status", "status"),
    )

    def __repr__(self):
        return f"<Scheme(id={self.id}, name='{self.name}', type={self.scheme_type}, status={self.status})>"
