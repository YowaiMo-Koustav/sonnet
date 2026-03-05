import enum
import json
from sqlalchemy import Column, String, Enum, ForeignKey, Index, TypeDecorator, CHAR, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.core.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            else:
                return uuid.UUID(value)


class JSON(TypeDecorator):
    """Platform-independent JSON type.
    
    Uses PostgreSQL's JSONB type, otherwise uses TEXT with JSON serialization.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return json.loads(value) if value else None


class LocationType(str, enum.Enum):
    """Enum for location hierarchy types."""
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    DISTRICT = "DISTRICT"


class Location(Base):
    """
    Location model representing hierarchical geographic locations.
    
    Supports a three-level hierarchy: Country -> State -> District
    Uses materialized path for efficient ancestor queries.
    """
    __tablename__ = "locations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(Enum(LocationType), nullable=False)
    parent_id = Column(GUID(), ForeignKey("locations.id"), nullable=True)
    materialized_path = Column(String(1000), nullable=True)
    location_metadata = Column(JSON(), nullable=True, default=dict)

    # Relationships
    parent = relationship("Location", remote_side=[id], backref="children")

    # Indexes are defined at the table level
    __table_args__ = (
        Index("idx_parent_id", "parent_id"),
        Index("idx_materialized_path", "materialized_path"),
        Index("idx_name", "name"),
    )

    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}', type={self.type})>"
