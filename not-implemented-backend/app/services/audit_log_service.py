"""Audit log service for tracking administrator changes to scheme data."""
from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.models.audit_log import AuditLog


class AuditLogService:
    """Service for managing audit log operations."""
    
    def __init__(self, db: Session):
        """Initialize AuditLogService with database session."""
        self.db = db
    
    def create_audit_log(
        self,
        admin_id: UUID,
        scheme_id: UUID,
        field_name: str,
        old_value: Optional[str],
        new_value: Optional[str]
    ) -> str:
        """
        Create a new audit log entry for an administrator change.
        
        Args:
            admin_id: UUID of the administrator making the change
            scheme_id: UUID of the scheme being modified
            field_name: Name of the field that was changed
            old_value: Previous value of the field (as string)
            new_value: New value of the field (as string)
            
        Returns:
            String representation of the created audit log ID
            
        Requirements: 10.5
        """
        audit_log = AuditLog(
            admin_id=admin_id,
            scheme_id=scheme_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return str(audit_log.id)
    
    def get_audit_logs_by_scheme(self, scheme_id: UUID) -> List[AuditLog]:
        """
        Get all audit log entries for a specific scheme.
        
        Args:
            scheme_id: UUID of the scheme
            
        Returns:
            List of AuditLog objects for the scheme, ordered by timestamp descending
            
        Requirements: 10.5
        """
        return self.db.query(AuditLog).filter(
            AuditLog.scheme_id == scheme_id
        ).order_by(AuditLog.timestamp.desc()).all()
    
    def get_audit_logs_by_admin(self, admin_id: UUID) -> List[AuditLog]:
        """
        Get all audit log entries for a specific administrator.
        
        Args:
            admin_id: UUID of the administrator
            
        Returns:
            List of AuditLog objects for the admin, ordered by timestamp descending
            
        Requirements: 10.5
        """
        return self.db.query(AuditLog).filter(
            AuditLog.admin_id == admin_id
        ).order_by(AuditLog.timestamp.desc()).all()
    
    def get_recent_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        """
        Get the most recent audit log entries across all schemes.
        
        Args:
            limit: Maximum number of entries to return (default: 100)
            
        Returns:
            List of AuditLog objects, ordered by timestamp descending
            
        Requirements: 10.5
        """
        return self.db.query(AuditLog).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()
    
    def get_field_history(self, scheme_id: UUID, field_name: str) -> List[AuditLog]:
        """
        Get the change history for a specific field of a scheme.
        
        Args:
            scheme_id: UUID of the scheme
            field_name: Name of the field to get history for
            
        Returns:
            List of AuditLog objects for the field, ordered by timestamp descending
            
        Requirements: 10.5
        """
        return self.db.query(AuditLog).filter(
            AuditLog.scheme_id == scheme_id,
            AuditLog.field_name == field_name
        ).order_by(AuditLog.timestamp.desc()).all()
