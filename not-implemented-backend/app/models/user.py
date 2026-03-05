import uuid
from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.location import GUID, JSON


class User(Base):
    """
    User model representing students using the scholarship discovery system.
    
    Contains basic contact information and a JSONB profile field that stores
    detailed user information including age, gender, education, and income.
    """
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    profile = Column(JSON(), nullable=False, server_default='{}')
    location_id = Column(GUID(), ForeignKey("locations.id"), nullable=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.profile is None:
            self.profile = {}

    # Relationships
    location = relationship("Location", backref="users")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_users_location_id", "location_id"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
