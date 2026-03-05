"""Application tracking API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.services.application_tracker_service import ApplicationTrackerService
from app.api.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
    StatusHistoryResponse,
)
from app.models.application import Application, ApplicationStatus
from app.models.scheme import Scheme
from app.models.user import User


router = APIRouter(prefix="/api", tags=["applications"])


@router.post("/applications", response_model=ApplicationResponse, status_code=201)
def create_application(
    application_data: ApplicationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new application for a user and scheme.
    
    Requirements: 5.1
    """
    # Verify user exists
    user = db.query(User).filter(User.id == application_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify scheme exists
    scheme = db.query(Scheme).filter(Scheme.id == application_data.scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    # Check if application already exists
    existing_application = db.query(Application).filter(
        Application.user_id == application_data.user_id,
        Application.scheme_id == application_data.scheme_id
    ).first()
    
    if existing_application:
        raise HTTPException(
            status_code=400,
            detail="Application already exists for this user and scheme"
        )
    
    # Create application
    tracker = ApplicationTrackerService(db)
    application = tracker.create_application(
        user_id=application_data.user_id,
        scheme_id=application_data.scheme_id,
        notes=application_data.notes or ""
    )
    
    return _convert_application_to_response(application)


@router.get("/applications/{id}", response_model=ApplicationResponse)
def get_application(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get application details by ID.
    
    Requirements: 5.1, 5.5
    """
    tracker = ApplicationTrackerService(db)
    application = tracker.get_application(id)
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return _convert_application_to_response(application)


@router.put("/applications/{id}/status", response_model=ApplicationResponse)
def update_application_status(
    id: UUID,
    status_data: ApplicationStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update application status.
    
    Requirements: 5.2, 5.3
    """
    tracker = ApplicationTrackerService(db)
    application = tracker.get_application(id)
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Validate status
    try:
        new_status = ApplicationStatus(status_data.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status_data.status}. Must be one of: {', '.join([s.value for s in ApplicationStatus])}"
        )
    
    tracker.update_status(
        application_id=id,
        new_status=new_status,
        notes=status_data.notes or ""
    )
    
    db.refresh(application)
    
    return _convert_application_to_response(application)


@router.get("/users/{id}/applications", response_model=List[ApplicationResponse])
def get_user_applications(
    id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of applications to return"),
    offset: int = Query(0, ge=0, description="Number of applications to skip"),
    db: Session = Depends(get_db)
):
    """
    Get all applications for a user with pagination.
    
    Requirements: 5.1, 5.5, 7.1
    """
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tracker = ApplicationTrackerService(db)
    applications = tracker.get_user_applications(id, limit=limit, offset=offset)
    
    return [_convert_application_to_response(app) for app in applications]


@router.get("/applications/{id}/history", response_model=List[StatusHistoryResponse])
def get_application_history(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get status change history for an application.
    
    Requirements: 5.3
    """
    tracker = ApplicationTrackerService(db)
    application = tracker.get_application(id)
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get status history from the application record
    status_history = application.status_history or []
    
    return status_history


def _convert_application_to_response(application: Application) -> dict:
    """Convert an Application model to a response dict."""
    return {
        "id": application.id,
        "user_id": application.user_id,
        "scheme_id": application.scheme_id,
        "status": application.status.value,
        "status_history": application.status_history or [],
        "notes": application.notes,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
    }
