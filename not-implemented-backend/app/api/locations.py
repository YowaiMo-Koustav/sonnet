"""Location API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.services.location_service import LocationService
from app.api.schemas import LocationCreate, LocationResponse, SchemeResponse, LocationTypeEnum
from app.models.location import Location, LocationType


router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.post("", response_model=LocationResponse, status_code=201)
def create_location(
    location_data: LocationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new location.
    
    Requirements: 1.1, 1.2
    """
    # Validate parent exists if parent_id is provided
    if location_data.parent_id:
        parent = db.query(Location).filter(Location.id == location_data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent location not found")
        
        # Validate hierarchy rules
        if location_data.type == LocationTypeEnum.COUNTRY:
            raise HTTPException(
                status_code=400,
                detail="Country cannot have a parent location"
            )
        elif location_data.type == LocationTypeEnum.STATE:
            if parent.type != LocationType.COUNTRY:
                raise HTTPException(
                    status_code=400,
                    detail="State must have a country as parent"
                )
        elif location_data.type == LocationTypeEnum.DISTRICT:
            if parent.type != LocationType.STATE:
                raise HTTPException(
                    status_code=400,
                    detail="District must have a state as parent"
                )
    else:
        # Only countries can have no parent
        if location_data.type != LocationTypeEnum.COUNTRY:
            raise HTTPException(
                status_code=400,
                detail="Only countries can have no parent location"
            )
    
    # Create location
    new_location = Location(
        name=location_data.name,
        type=LocationType[location_data.type.value],
        parent_id=location_data.parent_id,
        location_metadata=location_data.metadata or {}
    )
    
    # Build materialized path
    if location_data.parent_id:
        parent = db.query(Location).filter(Location.id == location_data.parent_id).first()
        if parent.materialized_path:
            new_location.materialized_path = f"{parent.materialized_path}{location_data.parent_id}/"
        else:
            new_location.materialized_path = f"/{location_data.parent_id}/"
    else:
        new_location.materialized_path = "/"
    
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    
    return new_location


@router.get("/roots", response_model=List[LocationResponse])
def get_root_locations(
    db: Session = Depends(get_db)
):
    """
    Get all root locations (countries with no parent).
    
    Requirements: 1.1
    """
    locations = db.query(Location).filter(Location.parent_id.is_(None)).all()
    return locations


@router.get("/search", response_model=List[LocationResponse])
def search_locations(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Search locations by name with fuzzy matching.
    
    Requirements: 1.5
    """
    service = LocationService(db)
    locations = service.search_locations(q, limit=limit)
    
    return locations


@router.get("/{id}", response_model=LocationResponse)
def get_location(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get location details by ID.
    
    Requirements: 1.1, 1.2
    """
    location = db.query(Location).filter(Location.id == id).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return location


@router.get("/{id}/children", response_model=List[LocationResponse])
def get_location_children(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get all immediate child locations of a location.
    
    Requirements: 1.2, 1.3
    """
    # Verify location exists
    location = db.query(Location).filter(Location.id == id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get children using service
    service = LocationService(db)
    children = service.get_children(id)
    
    return children


@router.get("/{id}/ancestors", response_model=List[LocationResponse])
def get_location_ancestors(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get ancestor path from root to the location.
    
    Requirements: 1.2, 1.5
    """
    # Verify location exists
    location = db.query(Location).filter(Location.id == id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get ancestors using service
    service = LocationService(db)
    ancestors = service.get_ancestors(id)
    
    return ancestors


@router.get("/{id}/schemes", response_model=List[SchemeResponse])
def get_location_schemes(
    id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of schemes to return"),
    offset: int = Query(0, ge=0, description="Number of schemes to skip"),
    db: Session = Depends(get_db)
):
    """
    Get all schemes available at a location with pagination.
    
    Requirements: 1.4, 7.1
    """
    # Verify location exists
    location = db.query(Location).filter(Location.id == id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get schemes using service with pagination
    service = LocationService(db)
    schemes = service.get_schemes(id, limit=limit, offset=offset)
    
    return schemes
