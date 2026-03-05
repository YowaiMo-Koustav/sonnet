"""Pydantic schemas for API request/response models."""
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from enum import Enum
import re


# Location schemas
class LocationTypeEnum(str, Enum):
    """Location type enum."""
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    DISTRICT = "DISTRICT"


class LocationMetadata(BaseModel):
    """Location metadata schema."""
    population: Optional[int] = None
    language_codes: Optional[List[str]] = None


class LocationCreate(BaseModel):
    """Schema for creating a location."""
    name: str = Field(..., min_length=1, max_length=255, description="Location name (1-255 characters)")
    type: LocationTypeEnum
    parent_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate location name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Location name cannot be empty or only whitespace")
        # Check for valid characters (letters, numbers, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z0-9\s\-']+$", v):
            raise ValueError("Location name contains invalid characters. Only letters, numbers, spaces, hyphens, and apostrophes are allowed")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_hierarchy_rules(self):
        """Validate location hierarchy rules."""
        if self.type == LocationTypeEnum.COUNTRY and self.parent_id is not None:
            raise ValueError("Country locations cannot have a parent")
        if self.type in [LocationTypeEnum.STATE, LocationTypeEnum.DISTRICT] and self.parent_id is None:
            raise ValueError(f"{self.type.value} locations must have a parent")
        return self


class LocationResponse(BaseModel):
    """Schema for location response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    type: str
    parent_id: Optional[UUID] = None
    materialized_path: Optional[str] = None
    location_metadata: Optional[Dict[str, Any]] = None


# Scheme schemas
class SchemeTypeEnum(str, Enum):
    """Scheme type enum."""
    SCHOLARSHIP = "SCHOLARSHIP"
    GRANT = "GRANT"
    JOB = "JOB"
    INTERNSHIP = "INTERNSHIP"


class SchemeStatusEnum(str, Enum):
    """Scheme status enum."""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    DRAFT = "DRAFT"


class EducationLevelEnum(str, Enum):
    """Education level enum."""
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    HIGHER_SECONDARY = "HIGHER_SECONDARY"
    UNDERGRADUATE = "UNDERGRADUATE"
    POSTGRADUATE = "POSTGRADUATE"


class GenderEnum(str, Enum):
    """Gender enum."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    ANY = "ANY"


class EligibilityCriteria(BaseModel):
    """Schema for eligibility criteria."""
    age_min: Optional[int] = Field(None, ge=0, le=150, description="Minimum age (0-150)")
    age_max: Optional[int] = Field(None, ge=0, le=150, description="Maximum age (0-150)")
    education_level: Optional[List[EducationLevelEnum]] = Field(None, description="Required education levels")
    income_max: Optional[float] = Field(None, ge=0, description="Maximum family income (must be non-negative)")
    gender: Optional[GenderEnum] = None
    location_restrictions: Optional[List[str]] = Field(None, description="List of allowed location IDs")
    other_criteria: Optional[List[str]] = Field(None, description="Additional eligibility criteria")
    
    @model_validator(mode='after')
    def validate_age_range(self):
        """Validate that age_min is less than or equal to age_max."""
        if self.age_min is not None and self.age_max is not None:
            if self.age_min > self.age_max:
                raise ValueError(f"Minimum age ({self.age_min}) cannot be greater than maximum age ({self.age_max})")
        return self
    
    @field_validator('education_level')
    @classmethod
    def validate_education_level(cls, v: Optional[List[EducationLevelEnum]]) -> Optional[List[EducationLevelEnum]]:
        """Validate education level list is not empty if provided."""
        if v is not None and len(v) == 0:
            raise ValueError("Education level list cannot be empty. Either provide levels or set to null")
        return v
    
    @field_validator('location_restrictions')
    @classmethod
    def validate_location_restrictions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate location restrictions list."""
        if v is not None:
            if len(v) == 0:
                raise ValueError("Location restrictions list cannot be empty. Either provide locations or set to null")
            # Validate each location ID is a valid UUID
            for loc_id in v:
                try:
                    UUID(loc_id)
                except ValueError:
                    raise ValueError(f"Invalid location ID format: {loc_id}. Must be a valid UUID")
        return v


class RequiredDocument(BaseModel):
    """Schema for required document."""
    name: str = Field(..., min_length=1, max_length=500, description="Document name (1-500 characters)")
    description: Optional[str] = Field(None, max_length=2000, description="Document description (max 2000 characters)")
    is_mandatory: bool = True
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate document name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Document name cannot be empty or only whitespace")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class SchemeCreate(BaseModel):
    """Schema for creating a scheme."""
    name: str = Field(..., min_length=1, max_length=500, description="Scheme name (1-500 characters)")
    description: Optional[str] = Field(None, max_length=10000, description="Scheme description (max 10000 characters)")
    location_id: UUID = Field(..., description="Location ID where scheme is available")
    scheme_type: SchemeTypeEnum
    eligibility_criteria: Optional[EligibilityCriteria] = Field(None, description="Eligibility criteria for the scheme")
    required_documents: Optional[List[RequiredDocument]] = Field(None, description="List of required documents")
    deadline: Optional[date] = Field(None, description="Application deadline")
    application_url: Optional[str] = Field(None, max_length=1000, description="Application URL (max 1000 characters)")
    status: Optional[SchemeStatusEnum] = SchemeStatusEnum.DRAFT
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate scheme name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Scheme name cannot be empty or only whitespace")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v
    
    @field_validator('application_url')
    @classmethod
    def validate_application_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate application URL format."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            # Basic URL validation
            if not re.match(r'^https?://', v, re.IGNORECASE):
                raise ValueError("Application URL must start with http:// or https://")
        return v
    
    @field_validator('deadline')
    @classmethod
    def validate_deadline(cls, v: Optional[date]) -> Optional[date]:
        """Validate deadline is not in the past."""
        if v is not None:
            today = datetime.now().date()
            if v < today:
                raise ValueError(f"Deadline cannot be in the past. Provided: {v}, Today: {today}")
        return v
    
    @field_validator('required_documents')
    @classmethod
    def validate_required_documents(cls, v: Optional[List[RequiredDocument]]) -> Optional[List[RequiredDocument]]:
        """Validate required documents list."""
        if v is not None and len(v) == 0:
            return None  # Convert empty list to None
        return v


class SchemeUpdate(BaseModel):
    """Schema for updating a scheme."""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    location_id: Optional[UUID] = None
    scheme_type: Optional[SchemeTypeEnum] = None
    eligibility_criteria: Optional[EligibilityCriteria] = None
    required_documents: Optional[List[RequiredDocument]] = None
    deadline: Optional[date] = None
    application_url: Optional[str] = Field(None, max_length=1000)
    status: Optional[SchemeStatusEnum] = None


class SchemeResponse(BaseModel):
    """Schema for scheme response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    description: Optional[str] = None
    location_id: UUID
    scheme_type: str
    eligibility_criteria: Dict[str, Any]
    required_documents: List[Dict[str, Any]]
    deadline: Optional[date] = None
    application_url: Optional[str] = None
    status: str
    approaching_deadline: Optional[bool] = None


class SchemeFiltersRequest(BaseModel):
    """Schema for scheme filtering parameters."""
    location_ids: Optional[List[UUID]] = None
    scheme_types: Optional[List[SchemeTypeEnum]] = None
    education_levels: Optional[List[EducationLevelEnum]] = None
    deadline_before: Optional[date] = None
    deadline_after: Optional[date] = None
    income_max: Optional[float] = None
    status: Optional[List[SchemeStatusEnum]] = None
    sort_by_deadline: Optional[bool] = False


# PDF processing schemas
class PDFUploadResponse(BaseModel):
    """Schema for PDF upload response."""
    id: UUID
    filename: str
    file_size: int
    processing_status: str
    message: str


class PDFStatusResponse(BaseModel):
    """Schema for PDF processing status response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    filename: str
    file_size: int
    processing_status: str
    uploaded_at: Any
    updated_at: Any


class PDFExtractionResultsResponse(BaseModel):
    """Schema for PDF extraction results response."""
    id: UUID
    filename: str
    processing_status: str
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, Any]


# User profile schemas
class UserProfileCreate(BaseModel):
    """Schema for creating a user profile."""
    email: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    location_id: Optional[UUID] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    education_level: Optional[str] = None
    family_income: Optional[float] = None


class UserProfileUpdate(BaseModel):
    """Schema for updating a user profile."""
    email: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    location_id: Optional[UUID] = None
    profile: Optional[Dict[str, Any]] = None


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    location_id: Optional[UUID] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    education_level: Optional[str] = None
    family_income: Optional[float] = None


# Match schemas
class MatchResponse(BaseModel):
    """Schema for match response."""
    scheme_id: UUID
    scheme_name: str
    match_percentage: float
    is_eligible: bool
    failed_criteria: List[str]


class MatchExplanationResponse(BaseModel):
    """Schema for match explanation response."""
    user_id: UUID
    scheme_id: UUID
    match_percentage: float
    is_eligible: bool
    failed_criteria: List[str]
    criteria_details: Dict[str, Any]


# Application schemas
class ApplicationCreate(BaseModel):
    """Schema for creating an application."""
    user_id: UUID
    scheme_id: UUID
    notes: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    """Schema for updating application status."""
    status: str
    notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    """Schema for application response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    scheme_id: UUID
    status: str
    status_history: List[Dict[str, Any]]
    notes: Optional[str] = None
    created_at: Any
    updated_at: Any


class StatusHistoryResponse(BaseModel):
    """Schema for status history entry."""
    from_status: Optional[str] = None
    to_status: str
    timestamp: Any
    notes: str


# Scheme review schemas
class SchemeReviewResponse(BaseModel):
    """Schema for scheme review response."""
    scheme_id: UUID
    scheme_name: str
    scheme_status: str
    low_confidence_fields: Dict[str, float]


# Audit log schemas
class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    id: UUID
    admin_id: str
    scheme_id: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: Any
