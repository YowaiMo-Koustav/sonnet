"""Eligibility matching engine for comparing user profiles against scheme criteria.

This service computes match scores between user profiles and scheme eligibility
criteria, ranks schemes by compatibility, and provides detailed match explanations.
"""
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.user import User
from app.models.scheme import Scheme, Gender, EducationLevel
from app.services.scheme_service import SchemeService, SchemeFilters


@dataclass
class MatchResult:
    """Result of matching a user profile against scheme eligibility criteria.
    
    Attributes:
        match_percentage: Percentage score (0-100) indicating compatibility
        is_eligible: True if user meets all criteria, False otherwise
        failed_criteria: List of criterion names that the user failed
    """
    match_percentage: float
    is_eligible: bool
    failed_criteria: List[str]


@dataclass
class RankedScheme:
    """Scheme with its match result for a user.
    
    Attributes:
        scheme: The Scheme object
        match_result: The MatchResult for this scheme
    """
    scheme: Scheme
    match_result: MatchResult


@dataclass
class MatchExplanation:
    """Detailed explanation of why a user matches or doesn't match a scheme.
    
    Attributes:
        scheme_id: UUID of the scheme
        user_id: UUID of the user
        match_result: The overall match result
        criteria_details: Dictionary mapping criterion name to pass/fail status and details
    """
    scheme_id: UUID
    user_id: UUID
    match_result: MatchResult
    criteria_details: Dict[str, Dict[str, Any]]


class EligibilityMatchingEngine:
    """Engine for computing eligibility matches between users and schemes.
    
    Implements the matching algorithm specified in the design document,
    which compares user profile data against scheme eligibility criteria
    and computes a match score.
    """
    
    def __init__(self, db: Session):
        """Initialize the matching engine with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.scheme_service = SchemeService(db)
    
    def compute_match_score(
        self,
        profile: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> MatchResult:
        """Compute match score between a user profile and eligibility criteria.
        
        This implements the matching algorithm from the design document:
        - Each criterion is worth 1 point
        - Score is the number of passed criteria
        - Match percentage is (score / max_score) * 100
        - User is eligible only if all criteria pass
        
        Args:
            profile: User profile dictionary with age, gender, education_level,
                    family_income, location_id
            criteria: Eligibility criteria dictionary with age_min, age_max,
                     education_level, income_max, gender, location_restrictions
        
        Returns:
            MatchResult with match_percentage, is_eligible, and failed_criteria
            
        Requirements: 9.2, 9.3
        """
        score = 0
        max_score = 0
        failed_criteria = []
        
        # Age check
        age_min = criteria.get("age_min")
        age_max = criteria.get("age_max")
        if age_min is not None or age_max is not None:
            max_score += 1
            user_age = profile.get("age")
            
            # Check if age is within range
            age_passes = True
            if user_age is None:
                age_passes = False
            elif age_min is not None and user_age < age_min:
                age_passes = False
            elif age_max is not None and user_age > age_max:
                age_passes = False
            
            if age_passes:
                score += 1
            else:
                failed_criteria.append("age")
        
        # Education check
        education_levels = criteria.get("education_level")
        if education_levels:
            max_score += 1
            user_education = profile.get("education_level")
            
            # Convert to list if single value
            if isinstance(education_levels, str):
                education_levels = [education_levels]
            
            if user_education and user_education in education_levels:
                score += 1
            else:
                failed_criteria.append("education")
        
        # Income check
        income_max = criteria.get("income_max")
        if income_max is not None:
            max_score += 1
            user_income = profile.get("family_income")
            
            if user_income is not None and user_income <= income_max:
                score += 1
            else:
                failed_criteria.append("income")
        
        # Gender check
        required_gender = criteria.get("gender")
        if required_gender and required_gender != "ANY":
            max_score += 1
            user_gender = profile.get("gender")
            
            if user_gender == required_gender:
                score += 1
            else:
                failed_criteria.append("gender")
        
        # Location check
        location_restrictions = criteria.get("location_restrictions")
        if location_restrictions:
            max_score += 1
            user_location_id = profile.get("location_id")
            
            # Convert location_id to string for comparison if needed
            if user_location_id:
                user_location_str = str(user_location_id)
                # Check if user's location is in the allowed list
                location_match = any(
                    str(loc) == user_location_str
                    for loc in location_restrictions
                )
                
                if location_match:
                    score += 1
                else:
                    failed_criteria.append("location")
            else:
                failed_criteria.append("location")
        
        # Calculate match percentage
        if max_score > 0:
            match_percentage = (score / max_score) * 100
        else:
            # No criteria specified means 100% match
            match_percentage = 100.0
        
        # User is eligible only if no criteria failed
        is_eligible = len(failed_criteria) == 0
        
        return MatchResult(
            match_percentage=match_percentage,
            is_eligible=is_eligible,
            failed_criteria=failed_criteria
        )
    
    def match_user(self, user_id: UUID, scheme_id: UUID) -> Optional[MatchResult]:
        """Compute match result for a specific user and scheme.
        
        Args:
            user_id: UUID of the user
            scheme_id: UUID of the scheme
        
        Returns:
            MatchResult if both user and scheme exist, None otherwise
            
        Requirements: 9.2, 9.3
        """
        # Fetch user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Fetch scheme
        scheme = self.scheme_service.get_scheme(scheme_id)
        if not scheme:
            return None
        
        # Prepare profile with location_id
        profile = dict(user.profile)
        profile["location_id"] = user.location_id
        
        # Compute match
        return self.compute_match_score(profile, scheme.eligibility_criteria)
    
    def find_matching_schemes(
        self,
        user_id: UUID,
        filters: Optional[SchemeFilters] = None
    ) -> List[RankedScheme]:
        """Find and rank schemes for a user based on eligibility match.
        
        Returns schemes sorted by match percentage (highest first), with
        eligible schemes appearing before ineligible ones.
        
        Args:
            user_id: UUID of the user
            filters: Optional filters to apply to scheme search
        
        Returns:
            List of RankedScheme objects sorted by eligibility and match score
            
        Requirements: 9.2, 9.3, 9.4
        """
        # Fetch user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # Prepare profile with location_id
        profile = dict(user.profile)
        profile["location_id"] = user.location_id
        
        # Get schemes based on filters
        schemes = self.scheme_service.list_schemes(filters)
        
        # Compute match for each scheme
        ranked_schemes = []
        for scheme in schemes:
            match_result = self.compute_match_score(
                profile,
                scheme.eligibility_criteria
            )
            ranked_schemes.append(RankedScheme(
                scheme=scheme,
                match_result=match_result
            ))
        
        # Sort by eligibility first (eligible schemes first), then by match percentage
        ranked_schemes.sort(
            key=lambda rs: (not rs.match_result.is_eligible, -rs.match_result.match_percentage)
        )
        
        return ranked_schemes
    
    def explain_match(
        self,
        user_id: UUID,
        scheme_id: UUID
    ) -> Optional[MatchExplanation]:
        """Provide detailed explanation of match between user and scheme.
        
        Args:
            user_id: UUID of the user
            scheme_id: UUID of the scheme
        
        Returns:
            MatchExplanation with detailed breakdown, or None if user/scheme not found
            
        Requirements: 9.2, 9.3
        """
        # Fetch user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Fetch scheme
        scheme = self.scheme_service.get_scheme(scheme_id)
        if not scheme:
            return None
        
        # Prepare profile with location_id
        profile = dict(user.profile)
        profile["location_id"] = user.location_id
        
        # Compute match
        match_result = self.compute_match_score(profile, scheme.eligibility_criteria)
        
        # Build detailed explanation for each criterion
        criteria = scheme.eligibility_criteria
        criteria_details = {}
        
        # Age criterion
        age_min = criteria.get("age_min")
        age_max = criteria.get("age_max")
        if age_min is not None or age_max is not None:
            user_age = profile.get("age")
            passed = "age" not in match_result.failed_criteria
            criteria_details["age"] = {
                "passed": passed,
                "required": f"{age_min or 'any'} - {age_max or 'any'}",
                "user_value": user_age,
                "message": f"Age must be between {age_min or 'any'} and {age_max or 'any'}"
            }
        
        # Education criterion
        education_levels = criteria.get("education_level")
        if education_levels:
            user_education = profile.get("education_level")
            passed = "education" not in match_result.failed_criteria
            if isinstance(education_levels, str):
                education_levels = [education_levels]
            criteria_details["education"] = {
                "passed": passed,
                "required": education_levels,
                "user_value": user_education,
                "message": f"Education level must be one of: {', '.join(education_levels)}"
            }
        
        # Income criterion
        income_max = criteria.get("income_max")
        if income_max is not None:
            user_income = profile.get("family_income")
            passed = "income" not in match_result.failed_criteria
            criteria_details["income"] = {
                "passed": passed,
                "required": f"<= {income_max}",
                "user_value": user_income,
                "message": f"Family income must be at most {income_max}"
            }
        
        # Gender criterion
        required_gender = criteria.get("gender")
        if required_gender and required_gender != "ANY":
            user_gender = profile.get("gender")
            passed = "gender" not in match_result.failed_criteria
            criteria_details["gender"] = {
                "passed": passed,
                "required": required_gender,
                "user_value": user_gender,
                "message": f"Gender must be {required_gender}"
            }
        
        # Location criterion
        location_restrictions = criteria.get("location_restrictions")
        if location_restrictions:
            user_location_id = profile.get("location_id")
            passed = "location" not in match_result.failed_criteria
            criteria_details["location"] = {
                "passed": passed,
                "required": location_restrictions,
                "user_value": str(user_location_id) if user_location_id else None,
                "message": f"Location must be one of the allowed locations"
            }
        
        return MatchExplanation(
            scheme_id=scheme_id,
            user_id=user_id,
            match_result=match_result,
            criteria_details=criteria_details
        )
