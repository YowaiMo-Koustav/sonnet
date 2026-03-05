"""Application tracker service for managing application records and status tracking."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from datetime import datetime

from app.models.application import Application, ApplicationStatus
from app.models.scheme import Scheme


class ApplicationTrackerService:
    """Service for managing application tracking operations."""
    
    def __init__(self, db: Session):
        """Initialize ApplicationTrackerService with database session."""
        self.db = db
    
    def create_application(self, user_id: UUID, scheme_id: UUID, notes: str = "") -> Application:
        """
        Create a new application record with initial status INTERESTED.
        
        Args:
            user_id: UUID of the user creating the application
            scheme_id: UUID of the scheme being applied to
            notes: Optional notes for the application
            
        Returns:
            The created Application object
            
        Raises:
            IntegrityError: If application already exists for this user-scheme combination
            
        Requirements: 5.1
        """
        # Create initial status change entry
        initial_status_change = {
            "from_status": None,
            "to_status": ApplicationStatus.INTERESTED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": "Application created"
        }
        
        application = Application(
            user_id=user_id,
            scheme_id=scheme_id,
            status=ApplicationStatus.INTERESTED,
            status_history=[initial_status_change],
            notes=notes
        )
        
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        
        return application
    
    def update_status(
        self, 
        application_id: UUID, 
        new_status: ApplicationStatus, 
        notes: str = ""
    ) -> None:
        """
        Update application status and record the change in status history.
        
        Args:
            application_id: UUID of the application to update
            new_status: New ApplicationStatus value
            notes: Optional notes about the status change
            
        Raises:
            ValueError: If application not found
            
        Requirements: 5.2, 5.3
        """
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            raise ValueError(f"Application with id {application_id} not found")
        
        # Record the status change
        status_change = {
            "from_status": application.status.value,
            "to_status": new_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": notes
        }
        
        # Update status and append to history
        application.status = new_status
        application.status_history.append(status_change)
        
        # Mark the status_history as modified for SQLAlchemy to detect the change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(application, "status_history")
        
        self.db.commit()
    
    def get_user_applications(self, user_id: UUID, limit: int = 50, offset: int = 0) -> List[Application]:
        """
        Get all applications for a specific user with pagination and eager loading.
        
        Args:
            user_id: UUID of the user
            limit: Maximum number of applications to return (default: 50)
            offset: Number of applications to skip for pagination (default: 0)
            
        Returns:
            List of Application objects for the user
            
        Requirements: 5.5, 7.1
        """
        from sqlalchemy.orm import joinedload
        
        # Use eager loading to avoid N+1 queries when accessing user and scheme data
        return self.db.query(Application).options(
            joinedload(Application.user),
            joinedload(Application.scheme).joinedload(Scheme.location)
        ).filter(
            Application.user_id == user_id
        ).limit(limit).offset(offset).all()
    
    def get_applications_by_status(
        self, 
        user_id: UUID, 
        status: ApplicationStatus,
        limit: int = 50,
        offset: int = 0
    ) -> List[Application]:
        """
        Get all applications for a user filtered by status with pagination and eager loading.
        
        Args:
            user_id: UUID of the user
            status: ApplicationStatus to filter by
            limit: Maximum number of applications to return (default: 50)
            offset: Number of applications to skip for pagination (default: 0)
            
        Returns:
            List of Application objects matching the status
            
        Requirements: 5.2, 7.1
        """
        from sqlalchemy.orm import joinedload
        
        # Use eager loading to avoid N+1 queries
        return self.db.query(Application).options(
            joinedload(Application.user),
            joinedload(Application.scheme).joinedload(Scheme.location)
        ).filter(
            Application.user_id == user_id,
            Application.status == status
        ).limit(limit).offset(offset).all()
    
    def get_application_history(self, application_id: UUID) -> List[Dict[str, Any]]:
        """
        Get the complete status change history for an application.
        
        Args:
            application_id: UUID of the application
            
        Returns:
            List of StatusChange dictionaries representing the timeline
            
        Raises:
            ValueError: If application not found
            
        Requirements: 5.3, 5.5
        """
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            raise ValueError(f"Application with id {application_id} not found")
        
        return application.status_history
    
    def get_application(self, application_id: UUID) -> Optional[Application]:
        """
        Get an application by ID.
        
        Args:
            application_id: UUID of the application
            
        Returns:
            Application object or None if not found
            
        Requirements: 5.5
        """
        return self.db.query(Application).filter(
            Application.id == application_id
        ).first()
