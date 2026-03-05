"""Scheme service for managing scheme CRUD operations."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
from datetime import date, datetime, timedelta
import json

from app.models.scheme import Scheme, SchemeType, SchemeStatus
from app.models.pdf_document import PDFDocument
from app.services.cache_service import get_cache_service
from app.core.config import get_settings


class SchemeFilters:
    """Filter criteria for scheme queries."""
    
    def __init__(
        self,
        location_ids: Optional[List[UUID]] = None,
        scheme_types: Optional[List[SchemeType]] = None,
        deadline_before: Optional[date] = None,
        deadline_after: Optional[date] = None,
        text_query: Optional[str] = None,
        status: Optional[SchemeStatus] = None
    ):
        """
        Initialize scheme filters.
        
        Args:
            location_ids: Filter by location IDs
            scheme_types: Filter by scheme types
            deadline_before: Filter schemes with deadline before this date
            deadline_after: Filter schemes with deadline after this date
            text_query: Search in name, description, or eligibility criteria
            status: Filter by scheme status
        """
        self.location_ids = location_ids or []
        self.scheme_types = scheme_types or []
        self.deadline_before = deadline_before
        self.deadline_after = deadline_after
        self.text_query = text_query
        self.status = status


class SchemeService:
    """Service for managing scheme CRUD operations."""
    
    def __init__(self, db: Session):
        """Initialize SchemeService with database session."""
        self.db = db
        self.cache = get_cache_service()
        self.settings = get_settings()
    
    def create_scheme(self, scheme_data: Dict[str, Any]) -> Scheme:
        """
        Create a new scheme.
        
        Args:
            scheme_data: Dictionary containing scheme fields
            
        Returns:
            Created Scheme object
            
        Requirements: 1.4, 6.2, 6.4
        """
        scheme = Scheme(**scheme_data)
        self.db.add(scheme)
        self.db.commit()
        self.db.refresh(scheme)
        
        # Invalidate relevant caches
        self.invalidate_scheme_cache(scheme.id)
        
        return scheme
    
    def update_scheme(
        self, 
        scheme_id: UUID, 
        updates: Dict[str, Any], 
        admin_id: Optional[UUID] = None
    ) -> Optional[Scheme]:
        """
        Update an existing scheme and optionally record audit logs.
        
        Args:
            scheme_id: UUID of the scheme to update
            updates: Dictionary of fields to update
            admin_id: Optional UUID of the administrator making the change (for audit logging)
            
        Returns:
            Updated Scheme object or None if not found
            
        Requirements: 6.2, 6.4, 10.3, 10.4, 10.5
        """
        from app.services.audit_log_service import AuditLogService
        
        scheme = self.db.query(Scheme).filter(Scheme.id == scheme_id).first()
        
        if not scheme:
            return None
        
        # Record audit logs if admin_id is provided
        if admin_id:
            audit_service = AuditLogService(self.db)
            
            for key, new_value in updates.items():
                if hasattr(scheme, key):
                    old_value = getattr(scheme, key)
                    
                    # Convert values to strings for audit log storage
                    old_value_str = self._serialize_value(old_value)
                    new_value_str = self._serialize_value(new_value)
                    
                    # Only log if value actually changed
                    if old_value_str != new_value_str:
                        audit_service.create_audit_log(
                            admin_id=admin_id,
                            scheme_id=scheme_id,
                            field_name=key,
                            old_value=old_value_str,
                            new_value=new_value_str
                        )
        
        # Update only provided fields
        for key, value in updates.items():
            if hasattr(scheme, key):
                setattr(scheme, key, value)
        
        self.db.commit()
        self.db.refresh(scheme)
        
        # Invalidate cache after update
        self.invalidate_scheme_cache(scheme_id)
        
        return scheme
    
    def _serialize_value(self, value: Any) -> Optional[str]:
        """
        Serialize a value to string for audit log storage.
        
        Args:
            value: Value to serialize
            
        Returns:
            String representation of the value
        """
        if value is None:
            return None
        elif isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        elif isinstance(value, (date, datetime)):
            return value.isoformat()
        elif isinstance(value, UUID):
            return str(value)
        else:
            return str(value)
    
    def get_scheme(self, scheme_id: UUID) -> Optional[Scheme]:
        """
        Retrieve a scheme by ID with caching.
        
        Popular schemes are cached with TTL to improve performance.
        
        Args:
            scheme_id: UUID of the scheme
            
        Returns:
            Scheme object or None if not found
            
        Requirements: 1.4, 7.1, 7.3, 7.4
        """
        cache_key = f"scheme:{scheme_id}"
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            return self._dict_to_scheme(cached)
        
        # Fetch from database
        scheme = self.db.query(Scheme).filter(Scheme.id == scheme_id).first()
        
        if scheme:
            # Cache the result
            scheme_dict = self._scheme_to_dict(scheme)
            self.cache.set(cache_key, scheme_dict, self.settings.cache_ttl_schemes)
        
        return scheme
    
    def list_schemes(
        self, 
        filters: Optional[SchemeFilters] = None, 
        sort_by_deadline: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Scheme]:
        """
        List schemes with optional filtering, deadline sorting, and pagination.
        
        Args:
            filters: Optional SchemeFilters object for filtering results
            sort_by_deadline: If True, sort schemes by deadline in ascending order
            limit: Maximum number of schemes to return (default: 50)
            offset: Number of schemes to skip for pagination (default: 0)
            
        Returns:
            List of Scheme objects matching the filters
            
        Requirements: 1.4, 6.2, 6.4, 7.1, 8.4
        """
        from sqlalchemy.orm import joinedload
        
        # Use eager loading to avoid N+1 queries when accessing location data
        query = self.db.query(Scheme).options(
            joinedload(Scheme.location)
        )
        
        if filters:
            # Apply location filter
            if filters.location_ids:
                query = query.filter(Scheme.location_id.in_(filters.location_ids))
            
            # Apply scheme type filter
            if filters.scheme_types:
                query = query.filter(Scheme.scheme_type.in_(filters.scheme_types))
            
            # Apply deadline filters
            if filters.deadline_before:
                query = query.filter(Scheme.deadline <= filters.deadline_before)
            
            if filters.deadline_after:
                query = query.filter(Scheme.deadline >= filters.deadline_after)
            
            # Apply status filter
            if filters.status:
                query = query.filter(Scheme.status == filters.status)
            
            # Apply text search filter
            if filters.text_query:
                search_pattern = f"%{filters.text_query}%"
                query = query.filter(
                    or_(
                        Scheme.name.ilike(search_pattern),
                        Scheme.description.ilike(search_pattern)
                    )
                )
        
        # Apply deadline sorting if requested
        if sort_by_deadline:
            # Sort by deadline ascending, with NULL deadlines at the end
            query = query.order_by(Scheme.deadline.asc().nullslast())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def delete_scheme(self, scheme_id: UUID) -> bool:
        """
        Soft delete a scheme by marking it as CLOSED.
        
        Args:
            scheme_id: UUID of the scheme to delete
            
        Returns:
            True if scheme was deleted, False if not found
            
        Requirements: 6.2, 6.4
        """
        scheme = self.db.query(Scheme).filter(Scheme.id == scheme_id).first()
        
        if not scheme:
            return False
        
        # Soft delete by setting status to CLOSED
        scheme.status = SchemeStatus.CLOSED
        self.db.commit()
        
        # Invalidate cache
        self.invalidate_scheme_cache(scheme_id)
        
        return True
    
    def is_deadline_approaching(self, scheme: Scheme, days: int = 7) -> bool:
        """
        Check if a scheme's deadline is approaching within the specified number of days.
        
        Args:
            scheme: Scheme object to check
            days: Number of days to consider as "approaching" (default: 7)
            
        Returns:
            True if deadline is within the specified days, False otherwise
            
        Requirements: 8.3
        """
        if scheme.deadline is None:
            return False
        
        today = date.today()
        days_until_deadline = (scheme.deadline - today).days
        
        # Deadline is approaching if it's within the specified days and not yet passed
        return 0 <= days_until_deadline <= days
    
    def mark_expired_schemes_as_closed(self) -> int:
        """
        Mark all schemes with past deadlines as CLOSED.
        
        Returns:
            Number of schemes that were marked as CLOSED
            
        Requirements: 8.5
        """
        today = date.today()
        
        # Find all schemes with deadlines in the past that are not already CLOSED
        expired_schemes = self.db.query(Scheme).filter(
            and_(
                Scheme.deadline < today,
                Scheme.status != SchemeStatus.CLOSED
            )
        ).all()
        
        count = 0
        for scheme in expired_schemes:
            scheme.status = SchemeStatus.CLOSED
            count += 1
        
        if count > 0:
            self.db.commit()
        
        return count
    
    def flag_low_confidence_fields(
        self, 
        scheme_id: UUID, 
        confidence_threshold: float = 0.5
    ) -> Dict[str, float]:
        """
        Flag fields with low confidence scores for admin review.
        
        Retrieves confidence scores from the source PDF document and identifies
        fields that fall below the confidence threshold.
        
        Args:
            scheme_id: UUID of the scheme to check
            confidence_threshold: Minimum confidence score (default: 0.5)
            
        Returns:
            Dictionary mapping field names to their confidence scores for fields
            that require review (confidence < threshold)
            
        Requirements: 10.1, 10.2
        """
        scheme = self.db.query(Scheme).filter(Scheme.id == scheme_id).first()
        
        if not scheme or not scheme.source_pdf_id:
            return {}
        
        # Get the source PDF document
        pdf_doc = self.db.query(PDFDocument).filter(
            PDFDocument.id == scheme.source_pdf_id
        ).first()
        
        if not pdf_doc or not pdf_doc.confidence_scores:
            return {}
        
        # Extract low-confidence fields
        low_confidence_fields = {}
        confidence_scores = pdf_doc.confidence_scores
        
        for field_name, confidence in confidence_scores.items():
            if isinstance(confidence, (int, float)) and confidence < confidence_threshold:
                low_confidence_fields[field_name] = confidence
        
        return low_confidence_fields
    
    def get_schemes_requiring_review(
        self, 
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get all schemes that have low-confidence fields requiring admin review.
        
        Returns schemes along with their low-confidence fields and scores.
        
        Args:
            confidence_threshold: Minimum confidence score (default: 0.5)
            
        Returns:
            List of dictionaries containing scheme info and low-confidence fields:
            [
                {
                    'scheme': Scheme object,
                    'low_confidence_fields': {field_name: confidence_score, ...}
                },
                ...
            ]
            
        Requirements: 10.1, 10.2
        """
        # Get all schemes with source PDFs
        schemes = self.db.query(Scheme).filter(
            Scheme.source_pdf_id.isnot(None)
        ).all()
        
        schemes_needing_review = []
        
        for scheme in schemes:
            low_confidence_fields = self.flag_low_confidence_fields(
                scheme.id, 
                confidence_threshold
            )
            
            if low_confidence_fields:
                schemes_needing_review.append({
                    'scheme': scheme,
                    'low_confidence_fields': low_confidence_fields
                })
        
        return schemes_needing_review
    
    def invalidate_scheme_cache(self, scheme_id: Optional[UUID] = None):
        """
        Invalidate scheme cache entries.
        
        Args:
            scheme_id: If provided, invalidate cache for specific scheme.
                      If None, invalidate all scheme caches.
        """
        if scheme_id:
            self.cache.delete(f"scheme:{scheme_id}")
        else:
            self.cache.delete_pattern("scheme:*")
    
    def _scheme_to_dict(self, scheme: Scheme) -> dict:
        """Convert Scheme object to dictionary for caching."""
        return {
            "id": str(scheme.id),
            "name": scheme.name,
            "description": scheme.description,
            "location_id": str(scheme.location_id),
            "scheme_type": scheme.scheme_type.value if scheme.scheme_type else None,
            "eligibility_criteria": scheme.eligibility_criteria,
            "required_documents": scheme.required_documents,
            "deadline": scheme.deadline.isoformat() if scheme.deadline else None,
            "application_url": scheme.application_url,
            "source_pdf_id": str(scheme.source_pdf_id) if scheme.source_pdf_id else None,
            "status": scheme.status.value if scheme.status else None
        }
    
    def _dict_to_scheme(self, data: dict) -> Scheme:
        """Convert dictionary to Scheme object (detached from session)."""
        scheme = Scheme(
            id=UUID(data["id"]),
            name=data["name"],
            description=data["description"],
            location_id=UUID(data["location_id"]),
            scheme_type=SchemeType(data["scheme_type"]) if data["scheme_type"] else None,
            eligibility_criteria=data["eligibility_criteria"],
            required_documents=data["required_documents"],
            deadline=datetime.fromisoformat(data["deadline"]).date() if data["deadline"] else None,
            application_url=data["application_url"],
            source_pdf_id=UUID(data["source_pdf_id"]) if data["source_pdf_id"] else None,
            status=SchemeStatus(data["status"]) if data["status"] else None
        )
        return scheme
    
    def track_scheme_access(self, user_id: UUID, scheme_id: UUID) -> bool:
        """
        Track that a user has accessed a scheme.
        
        This helps the frontend know which schemes to store in local storage
        for offline access.
        
        Args:
            user_id: UUID of the user
            scheme_id: UUID of the accessed scheme
            
        Returns:
            True if successful, False otherwise
            
        Requirements: 7.3, 7.4
        """
        cache_key = f"user:{user_id}:accessed_schemes"
        return self.cache.add_to_set(cache_key, str(scheme_id))
    
    def get_accessed_schemes(self, user_id: UUID) -> List[str]:
        """
        Get list of scheme IDs that a user has accessed.
        
        This endpoint helps the frontend determine which schemes should be
        stored in browser local storage for offline access.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of scheme ID strings
            
        Requirements: 7.3, 7.4
        """
        cache_key = f"user:{user_id}:accessed_schemes"
        return self.cache.get_set_members(cache_key)
