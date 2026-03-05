"""Scheme API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.services.scheme_service import SchemeService, SchemeFilters as ServiceSchemeFilters
from app.services.search_service import SearchService, SchemeFilters as SearchSchemeFilters
from app.api.schemas import (
    SchemeCreate,
    SchemeUpdate,
    SchemeResponse,
    SchemeFiltersRequest,
    SchemeTypeEnum,
    SchemeStatusEnum,
    EducationLevelEnum,
)
from app.models.scheme import Scheme, SchemeType, SchemeStatus, EducationLevel
from app.models.location import Location


router = APIRouter(prefix="/api/schemes", tags=["schemes"])


def _convert_scheme_to_response(scheme: Scheme, service: SchemeService) -> dict:
    """Convert a Scheme model to a response dict with additional fields."""
    response_data = {
        "id": scheme.id,
        "name": scheme.name,
        "description": scheme.description,
        "location_id": scheme.location_id,
        "scheme_type": scheme.scheme_type.value if isinstance(scheme.scheme_type, SchemeType) else scheme.scheme_type,
        "eligibility_criteria": scheme.eligibility_criteria or {},
        "required_documents": scheme.required_documents or [],
        "deadline": scheme.deadline,
        "application_url": scheme.application_url,
        "status": scheme.status.value if isinstance(scheme.status, SchemeStatus) else scheme.status,
        "approaching_deadline": service.is_deadline_approaching(scheme) if scheme.deadline else False,
    }
    return response_data


@router.post("", response_model=SchemeResponse, status_code=201)
def create_scheme(
    scheme_data: SchemeCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new scheme.
    
    Requirements: 6.1
    """
    # Validate location exists
    location = db.query(Location).filter(Location.id == scheme_data.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Prepare scheme data
    scheme_dict = {
        "name": scheme_data.name,
        "description": scheme_data.description,
        "location_id": scheme_data.location_id,
        "scheme_type": SchemeType[scheme_data.scheme_type.value],
        "eligibility_criteria": scheme_data.eligibility_criteria.model_dump() if scheme_data.eligibility_criteria else {},
        "required_documents": [doc.model_dump() for doc in scheme_data.required_documents] if scheme_data.required_documents else [],
        "deadline": scheme_data.deadline,
        "application_url": scheme_data.application_url,
        "status": SchemeStatus[scheme_data.status.value] if scheme_data.status else SchemeStatus.DRAFT,
    }
    
    # Create scheme using service
    service = SchemeService(db)
    new_scheme = service.create_scheme(scheme_dict)
    
    return _convert_scheme_to_response(new_scheme, service)


@router.get("/search", response_model=List[SchemeResponse])
def search_schemes(
    q: str = Query(..., min_length=1, description="Search query"),
    location_ids: Optional[str] = Query(None, description="Comma-separated location IDs"),
    scheme_types: Optional[str] = Query(None, description="Comma-separated scheme types"),
    education_levels: Optional[str] = Query(None, description="Comma-separated education levels"),
    deadline_before: Optional[str] = Query(None, description="Filter schemes with deadline before this date (YYYY-MM-DD)"),
    deadline_after: Optional[str] = Query(None, description="Filter schemes with deadline after this date (YYYY-MM-DD)"),
    income_max: Optional[float] = Query(None, description="Maximum income requirement"),
    status: Optional[str] = Query(None, description="Comma-separated status values"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Search schemes by text query with optional filters and pagination.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1
    """
    # Parse filters
    filters = SearchSchemeFilters()
    
    if location_ids:
        try:
            filters.location_ids = [UUID(lid.strip()) for lid in location_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid location ID format")
    
    if scheme_types:
        try:
            filters.scheme_types = [SchemeType[st.strip().upper()] for st in scheme_types.split(",")]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Invalid scheme type: {e}")
    
    if education_levels:
        try:
            filters.education_levels = [EducationLevel[el.strip().upper()] for el in education_levels.split(",")]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Invalid education level: {e}")
    
    if deadline_before:
        try:
            from datetime import datetime
            filters.deadline_before = datetime.strptime(deadline_before, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline_before format. Use YYYY-MM-DD")
    
    if deadline_after:
        try:
            from datetime import datetime
            filters.deadline_after = datetime.strptime(deadline_after, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline_after format. Use YYYY-MM-DD")
    
    if income_max is not None:
        filters.income_max = income_max
    
    if status:
        try:
            filters.status = [SchemeStatus[s.strip().upper()] for s in status.split(",")]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Invalid status: {e}")
    
    # Search using service with pagination
    search_service = SearchService(db)
    results = search_service.search(q, filters=filters, limit=limit, offset=offset)
    
    # Convert to response format (results is a list of tuples: (scheme, score))
    scheme_service = SchemeService(db)
    return [_convert_scheme_to_response(scheme, scheme_service) for scheme, score in results]


@router.get("/{id}", response_model=SchemeResponse)
def get_scheme(
    id: UUID,
    user_id: Optional[UUID] = Query(None, description="User ID for tracking offline access"),
    db: Session = Depends(get_db)
):
    """
    Get scheme details by ID.
    
    If user_id is provided, tracks that the user accessed this scheme
    for offline access support.
    
    Requirements: 6.1, 7.3, 7.4
    """
    service = SchemeService(db)
    scheme = service.get_scheme(id)
    
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    # Track scheme access for offline support if user_id provided
    if user_id:
        service.track_scheme_access(user_id, id)
    
    return _convert_scheme_to_response(scheme, service)


@router.put("/{id}", response_model=SchemeResponse)
def update_scheme(
    id: UUID,
    scheme_data: SchemeUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing scheme.
    
    Requirements: 6.1
    """
    service = SchemeService(db)
    
    # Verify scheme exists
    existing_scheme = service.get_scheme(id)
    if not existing_scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    # Validate location if provided
    if scheme_data.location_id:
        location = db.query(Location).filter(Location.id == scheme_data.location_id).first()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
    
    # Prepare updates
    updates = {}
    if scheme_data.name is not None:
        updates["name"] = scheme_data.name
    if scheme_data.description is not None:
        updates["description"] = scheme_data.description
    if scheme_data.location_id is not None:
        updates["location_id"] = scheme_data.location_id
    if scheme_data.scheme_type is not None:
        updates["scheme_type"] = SchemeType[scheme_data.scheme_type.value]
    if scheme_data.eligibility_criteria is not None:
        updates["eligibility_criteria"] = scheme_data.eligibility_criteria.model_dump()
    if scheme_data.required_documents is not None:
        updates["required_documents"] = [doc.model_dump() for doc in scheme_data.required_documents]
    if scheme_data.deadline is not None:
        updates["deadline"] = scheme_data.deadline
    if scheme_data.application_url is not None:
        updates["application_url"] = scheme_data.application_url
    if scheme_data.status is not None:
        updates["status"] = SchemeStatus[scheme_data.status.value]
    
    # Update scheme
    service.update_scheme(id, updates)
    
    # Fetch updated scheme
    updated_scheme = service.get_scheme(id)
    
    return _convert_scheme_to_response(updated_scheme, service)


@router.delete("/{id}", status_code=204)
def delete_scheme(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a scheme (soft delete by setting status to CLOSED).
    
    Requirements: 6.1
    """
    service = SchemeService(db)
    
    # Verify scheme exists
    existing_scheme = service.get_scheme(id)
    if not existing_scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    # Delete scheme
    success = service.delete_scheme(id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete scheme")
    
    return None


@router.get("", response_model=List[SchemeResponse])
def list_schemes(
    location_ids: Optional[str] = Query(None, description="Comma-separated location IDs"),
    scheme_types: Optional[str] = Query(None, description="Comma-separated scheme types"),
    education_levels: Optional[str] = Query(None, description="Comma-separated education levels"),
    deadline_before: Optional[str] = Query(None, description="Filter schemes with deadline before this date (YYYY-MM-DD)"),
    deadline_after: Optional[str] = Query(None, description="Filter schemes with deadline after this date (YYYY-MM-DD)"),
    income_max: Optional[float] = Query(None, description="Maximum income requirement"),
    status: Optional[str] = Query(None, description="Comma-separated status values"),
    sort_by_deadline: bool = Query(False, description="Sort results by deadline"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of schemes to return"),
    offset: int = Query(0, ge=0, description="Number of schemes to skip"),
    db: Session = Depends(get_db)
):
    """
    List and filter schemes by various criteria with pagination.
    
    Requirements: 6.3, 6.4, 6.5, 7.1
    """
    # Parse query parameters
    filters = ServiceSchemeFilters()
    
    if location_ids:
        try:
            filters.location_ids = [UUID(lid.strip()) for lid in location_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid location ID format")
    
    if scheme_types:
        try:
            filters.scheme_types = [SchemeType[st.strip().upper()] for st in scheme_types.split(",")]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Invalid scheme type: {e}")
    
    if education_levels:
        try:
            filters.education_levels = [EducationLevel[el.strip().upper()] for el in education_levels.split(",")]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Invalid education level: {e}")
    
    if deadline_before:
        try:
            from datetime import datetime
            filters.deadline_before = datetime.strptime(deadline_before, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline_before format. Use YYYY-MM-DD")
    
    if deadline_after:
        try:
            from datetime import datetime
            filters.deadline_after = datetime.strptime(deadline_after, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline_after format. Use YYYY-MM-DD")
    
    if income_max is not None:
        filters.income_max = income_max
    
    if status:
        try:
            filters.status = [SchemeStatus[s.strip().upper()] for s in status.split(",")]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Invalid status: {e}")
    
    # Get schemes using service with pagination
    service = SchemeService(db)
    schemes = service.list_schemes(filters=filters, sort_by_deadline=sort_by_deadline, limit=limit, offset=offset)
    
    # Convert to response format
    return [_convert_scheme_to_response(scheme, service) for scheme in schemes]


@router.get("/offline/accessed", response_model=List[str])
def get_accessed_schemes(
    user_id: UUID = Query(..., description="User ID to get accessed schemes for"),
    db: Session = Depends(get_db)
):
    """
    Get list of scheme IDs that a user has accessed.
    
    This endpoint helps the frontend determine which schemes should be
    stored in browser local storage for offline access.
    
    Requirements: 7.3, 7.4
    """
    service = SchemeService(db)
    accessed_scheme_ids = service.get_accessed_schemes(user_id)
    return accessed_scheme_ids
