"""User profile API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.services.eligibility_matching_engine import EligibilityMatchingEngine, MatchResult
from app.services.scheme_service import SchemeService
from app.api.schemas import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    MatchResponse,
    MatchExplanationResponse,
)
from app.models.user import User
from app.models.scheme import Scheme


router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserProfileResponse, status_code=201)
def create_user(
    user_data: UserProfileCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user profile.
    
    Requirements: 9.1
    """
    # Check if user with email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        phone=user_data.phone,
        location_id=user_data.location_id,
        profile={
            "age": user_data.age,
            "gender": user_data.gender,
            "education_level": user_data.education_level,
            "family_income": user_data.family_income,
        }
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return _convert_user_to_response(user)


@router.get("/{id}", response_model=UserProfileResponse)
def get_user_profile(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get user profile by ID.
    
    Requirements: 9.1
    """
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return _convert_user_to_response(user)


@router.put("/{id}/profile", response_model=UserProfileResponse)
def update_user_profile(
    id: UUID,
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user profile information.
    
    Requirements: 9.5
    """
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update profile fields
    if profile_data.email is not None:
        # Check if new email is already taken
        existing_user = db.query(User).filter(
            User.email == profile_data.email,
            User.id != id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        user.email = profile_data.email
    
    if profile_data.phone is not None:
        user.phone = profile_data.phone
    
    if profile_data.location_id is not None:
        user.location_id = profile_data.location_id
    
    if profile_data.profile is not None:
        # Merge profile updates
        current_profile = user.profile or {}
        current_profile.update(profile_data.profile.model_dump())
        user.profile = current_profile
    
    db.commit()
    db.refresh(user)
    
    return _convert_user_to_response(user)


@router.get("/{id}/matching-schemes", response_model=list)
def get_matching_schemes(
    id: UUID,
    location_ids: Optional[str] = None,
    scheme_types: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get schemes matching user's eligibility profile.
    
    Requirements: 9.2, 9.3, 9.4
    """
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Parse filters
    filters = {}
    if location_ids:
        try:
            from uuid import UUID
            filters["location_ids"] = [UUID(lid.strip()) for lid in location_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid location ID format")
    
    if scheme_types:
        try:
            from app.models.scheme import SchemeType
            filters["scheme_types"] = [SchemeType[st.strip().upper()] for st in scheme_types.split(",")]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Invalid scheme type: {e}")
    
    # Get matching schemes using engine
    engine = EligibilityMatchingEngine(db)
    ranked_schemes = engine.find_matching_schemes(
        user_id=id,
        filters=filters if filters else None
    )
    
    # Convert to response format
    scheme_service = SchemeService(db)
    return [
        {
            "scheme_id": rs.scheme.id,
            "scheme_name": rs.scheme.name,
            "match_percentage": rs.match_result.match_percentage,
            "is_eligible": rs.match_result.is_eligible,
            "failed_criteria": rs.match_result.failed_criteria,
        }
        for rs in ranked_schemes
    ]


@router.get("/{id}/match/{scheme_id}", response_model=MatchExplanationResponse)
def get_match_explanation(
    id: UUID,
    scheme_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed explanation of how user matches a specific scheme.
    
    Requirements: 9.2, 9.3, 9.4
    """
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    # Get match explanation
    engine = EligibilityMatchingEngine(db)
    explanation = engine.explain_match(user_id=id, scheme_id=scheme_id)
    
    return explanation


@router.get("/{id}/accessed-schemes", response_model=list)
def get_accessed_schemes(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get list of scheme IDs that the user has accessed.
    
    This endpoint helps the frontend determine which schemes should be
    stored in browser local storage for offline access.
    
    Requirements: 7.3, 7.4
    """
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get accessed schemes from cache
    scheme_service = SchemeService(db)
    accessed_scheme_ids = scheme_service.get_accessed_schemes(id)
    
    return accessed_scheme_ids


@router.post("/{id}/accessed-schemes/{scheme_id}", status_code=204)
def track_scheme_access(
    id: UUID,
    scheme_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Track that a user has accessed a scheme.
    
    This helps the system know which schemes the user has viewed and should
    be available for offline access.
    
    Requirements: 7.3, 7.4
    """
    user = db.query(User).filter(User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    # Track the access
    scheme_service = SchemeService(db)
    success = scheme_service.track_scheme_access(id, scheme_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to track scheme access"
        )
    
    return None


def _convert_user_to_response(user: User) -> dict:
    """Convert a User model to a response dict."""
    profile = user.profile or {}
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "location_id": user.location_id,
        "age": profile.get("age"),
        "gender": profile.get("gender"),
        "education_level": profile.get("education_level"),
        "family_income": profile.get("family_income"),
    }
