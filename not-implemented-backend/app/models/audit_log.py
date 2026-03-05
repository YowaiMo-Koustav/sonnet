import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Index, DateTime, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.location import GUID


class AuditLog(Base):
    """
    AuditLog model for tracking administrator changes to scheme data.
    
    Records all modifications made by administrators including the field changed,
    old value, new value, and timestamp for compliance and auditing purposes.
    """
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    admin_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    scheme_id = Column(GUID(), ForeignKey("schemes.id"), nullable=False)
    field_name = Column(String(255), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    admin = relationship("User", backref="audit_logs")
    scheme = relationship("Scheme", backref="audit_logs")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_admin_id", "admin_id"),
        Index("idx_scheme_id", "scheme_id"),
        Index("idx_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, admin_id={self.admin_id}, scheme_id={self.scheme_id}, field='{self.field_name}', timestamp={self.timestamp})>"
