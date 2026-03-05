"""Location service for managing hierarchical location operations."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID

from app.models.location import Location, LocationType
from app.services.cache_service import cache_result, get_cache_service
from app.core.config import get_settings


class LocationService:
    """Service for managing location hierarchy operations."""
    
    def __init__(self, db: Session):
        """Initialize LocationService with database session."""
        self.db = db
        self.cache = get_cache_service()
        self.settings = get_settings()
    
    def get_children(self, location_id: UUID) -> List[Location]:
        """
        Get all immediate child locations of a given location.
        
        Cached with long TTL since location hierarchies rarely change.
        
        Args:
            location_id: UUID of the parent location
            
        Returns:
            List of child Location objects
            
        Requirements: 1.2, 1.3
        """
        cache_key = f"location:children:{location_id}"
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            # Reconstruct Location objects from cached data
            return [self._dict_to_location(loc_dict) for loc_dict in cached]
        
        # Fetch from database
        children = self.db.query(Location).filter(
            Location.parent_id == location_id
        ).all()
        
        # Cache the results
        children_dicts = [self._location_to_dict(loc) for loc in children]
        self.cache.set(cache_key, children_dicts, self.settings.cache_ttl_locations)
        
        return children
    
    def get_ancestors(self, location_id: UUID) -> List[Location]:
        """
        Get all ancestor locations from root to the given location using materialized path.
        
        Cached with long TTL since location hierarchies rarely change.
        
        Args:
            location_id: UUID of the location
            
        Returns:
            List of ancestor Location objects ordered from root to immediate parent
            
        Requirements: 1.2, 1.5
        """
        cache_key = f"location:ancestors:{location_id}"
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            return [self._dict_to_location(loc_dict) for loc_dict in cached]
        
        # Get the location to access its materialized path
        location = self.db.query(Location).filter(Location.id == location_id).first()
        
        if not location or not location.materialized_path:
            return []
        
        # Parse the materialized path to extract ancestor IDs
        # Format: "/country_id/state_id/" or "/country_id/"
        path_parts = [p for p in location.materialized_path.split('/') if p]
        
        if not path_parts:
            return []
        
        # Convert string IDs to UUID objects
        ancestor_ids = [UUID(part) for part in path_parts]
        
        # Query all ancestors
        ancestors = self.db.query(Location).filter(
            Location.id.in_(ancestor_ids)
        ).all()
        
        # Sort ancestors by their position in the materialized path
        # to maintain correct order from root to immediate parent
        ancestor_dict = {str(a.id): a for a in ancestors}
        ordered_ancestors = [ancestor_dict[part] for part in path_parts if part in ancestor_dict]
        
        # Cache the results
        ancestors_dicts = [self._location_to_dict(loc) for loc in ordered_ancestors]
        self.cache.set(cache_key, ancestors_dicts, self.settings.cache_ttl_locations)
        
        return ordered_ancestors
    
    def get_schemes(self, location_id: UUID, limit: int = 50, offset: int = 0) -> List:
        """
        Get all schemes available at a given location with pagination.
        
        Args:
            location_id: UUID of the location
            limit: Maximum number of schemes to return (default: 50)
            offset: Number of schemes to skip (default: 0)
            
        Returns:
            List of Scheme objects
            
        Requirements: 1.4, 7.1
        """
        from app.models.scheme import Scheme
        from sqlalchemy.orm import joinedload
        
        # Use eager loading to avoid N+1 queries when accessing location data
        return self.db.query(Scheme).options(
            joinedload(Scheme.location)
        ).filter(
            Scheme.location_id == location_id
        ).limit(limit).offset(offset).all()
    
    def search_locations(self, query: str, limit: int = 20) -> List[Location]:
        """
        Search for locations by name with fuzzy matching.
        
        Uses case-insensitive partial matching to find locations
        whose names contain the query string.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 20)
            
        Returns:
            List of matching Location objects
            
        Requirements: 1.5
        """
        if not query or not query.strip():
            return []
        
        # Use case-insensitive LIKE for fuzzy matching
        search_pattern = f"%{query.strip()}%"
        
        return self.db.query(Location).filter(
            Location.name.ilike(search_pattern)
        ).limit(limit).all()
    
    def invalidate_location_cache(self, location_id: Optional[UUID] = None):
        """
        Invalidate location cache entries.
        
        Args:
            location_id: If provided, invalidate cache for specific location.
                        If None, invalidate all location caches.
        """
        if location_id:
            self.cache.delete(f"location:children:{location_id}")
            self.cache.delete(f"location:ancestors:{location_id}")
        else:
            self.cache.delete_pattern("location:*")
    
    def _location_to_dict(self, location: Location) -> dict:
        """Convert Location object to dictionary for caching."""
        return {
            "id": str(location.id),
            "name": location.name,
            "type": location.type.value if location.type else None,
            "parent_id": str(location.parent_id) if location.parent_id else None,
            "materialized_path": location.materialized_path,
            "metadata": location.metadata
        }
    
    def _dict_to_location(self, data: dict) -> Location:
        """Convert dictionary to Location object (detached from session)."""
        location = Location(
            id=UUID(data["id"]),
            name=data["name"],
            type=LocationType(data["type"]) if data["type"] else None,
            parent_id=UUID(data["parent_id"]) if data["parent_id"] else None,
            materialized_path=data["materialized_path"],
            metadata=data["metadata"]
        )
        return location
