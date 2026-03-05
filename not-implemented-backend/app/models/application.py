import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Enum, ForeignKey, Index, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.location import GUID, JSON


class ApplicationStatus(str, enum.Enum):
    """Enum for application status states."""
    INTERESTED = "INTERESTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Application(Base):
    """
    Application model representing user applications to schemes.
    
    Tracks application status and maintains a history of status changes.
    Each user can only have one application per scheme (enforced by unique constraint).
    """
    __tablename__ = "applications"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    scheme_id = Column(GUID(), ForeignKey("schemes.id"), nullable=False)
    status = Column(Enum(ApplicationStatus), nullable=False)
    status_history = Column(JSON(), nullable=False, server_default='[]')
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.status_history is None:
            self.status_history = []

    # Relationships
    user = relationship("User", backref="applications")
    scheme = relationship("Scheme", backref="applications")

    # Indexes and constraints for efficient querying
    __table_args__ = (
        Index("idx_applications_user_id", "user_id"),
        Index("idx_applications_scheme_id", "scheme_id"),
        Index("idx_applications_status", "status"),
        UniqueConstraint("user_id", "scheme_id", name="idx_user_scheme"),
    )

    def __repr__(self):
        return f"<Application(id={self.id}, user_id={self.user_id}, scheme_id={self.scheme_id}, status={self.status})>"
