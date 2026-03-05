"""Search service for filtering and searching schemes with multi-criteria support."""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from uuid import UUID
from datetime import date

from app.models.scheme import Scheme, SchemeType, SchemeStatus, EducationLevel
from app.services.location_service import LocationService


class SchemeFilters:
    """Filter criteria for scheme queries with multi-criteria support."""
    
    def __init__(
        self,
        location_ids: Optional[List[UUID]] = None,
        scheme_types: Optional[List[SchemeType]] = None,
        education_levels: Optional[List[EducationLevel]] = None,
        deadline_before: Optional[date] = None,
        deadline_after: Optional[date] = None,
        income_max: Optional[float] = None,
        only_eligible: bool = False,
        text_query: Optional[str] = None,
        status: Optional[SchemeStatus] = None
    ):
        """
        Initialize scheme filters.
        
        Args:
            location_ids: Filter by location IDs (includes descendant locations)
            scheme_types: Filter by scheme types
            education_levels: Filter by education levels
            deadline_before: Filter schemes with deadline before this date
            deadline_after: Filter schemes with deadline after this date
            income_max: Filter schemes with income requirement <= this value
            only_eligible: If True, filter to schemes user is eligible for
            text_query: Search in name, description, or eligibility criteria
            status: Filter by scheme status
        """
        self.location_ids = location_ids or []
        self.scheme_types = scheme_types or []
        self.education_levels = education_levels or []
        self.deadline_before = deadline_before
        self.deadline_after = deadline_after
        self.income_max = income_max
        self.only_eligible = only_eligible
        self.text_query = text_query
        self.status = status


class SearchService:
    """Service for searching and filtering schemes with multi-criteria support."""
    
    def __init__(self, db: Session):
        """
        Initialize SearchService with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.location_service = LocationService(db)
    
    def filter(self, filters: SchemeFilters, limit: int = 50, offset: int = 0) -> List[Scheme]:
        """
        Filter schemes by multiple criteria with AND logic and pagination.
        
        All filter conditions are combined with AND logic - schemes must
        satisfy all specified criteria to be included in results.
        
        Args:
            filters: SchemeFilters object containing filter criteria
            limit: Maximum number of schemes to return (default: 50)
            offset: Number of schemes to skip for pagination (default: 0)
            
        Returns:
            List of Scheme objects matching all filter criteria
            
        Requirements: 6.3, 6.4, 7.1
        """
        from sqlalchemy.orm import joinedload
        
        # Use eager loading to avoid N+1 queries when accessing location data
        query = self.db.query(Scheme).options(
            joinedload(Scheme.location)
        )
        
        # Apply location filter with hierarchy support
        if filters.location_ids:
            # Get all descendant locations for each specified location
            all_location_ids = set(filters.location_ids)
            for location_id in filters.location_ids:
                descendant_ids = self._get_descendant_location_ids(location_id)
                all_location_ids.update(descendant_ids)
            
            query = query.filter(Scheme.location_id.in_(all_location_ids))
        
        # Apply scheme type filter
        if filters.scheme_types:
            query = query.filter(Scheme.scheme_type.in_(filters.scheme_types))
        
        # Apply education level filter
        if filters.education_levels:
            # For SQLite compatibility, we need to filter in Python after fetching
            # For PostgreSQL, we could use JSONB operators
            # We'll apply this filter after the query
            pass
        
        # Apply deadline range filters
        if filters.deadline_before:
            query = query.filter(
                or_(
                    Scheme.deadline <= filters.deadline_before,
                    Scheme.deadline.is_(None)
                )
            )
        
        if filters.deadline_after:
            query = query.filter(
                and_(
                    Scheme.deadline >= filters.deadline_after,
                    Scheme.deadline.isnot(None)
                )
            )
        
        # Apply income filter
        if filters.income_max is not None:
            # For SQLite compatibility, we need to filter in Python after fetching
            # For PostgreSQL, we could use JSONB operators
            # We'll apply this filter after the query
            pass
        
        # Apply status filter (default to ACTIVE if not specified)
        if filters.status:
            query = query.filter(Scheme.status == filters.status)
        else:
            # By default, only show ACTIVE schemes
            query = query.filter(Scheme.status == SchemeStatus.ACTIVE)
        
        # Apply text search filter
        if filters.text_query:
            search_pattern = f"%{filters.text_query}%"
            query = query.filter(
                or_(
                    Scheme.name.ilike(search_pattern),
                    Scheme.description.ilike(search_pattern)
                )
            )
        
        # Apply pagination before executing query
        query = query.limit(limit).offset(offset)
        
        # Execute query
        results = query.all()
        
        # Apply education level filter (post-query for SQLite compatibility)
        if filters.education_levels:
            filtered_results = []
            for scheme in results:
                criteria = scheme.eligibility_criteria or {}
                scheme_edu_levels = criteria.get('education_level', [])
                
                # Check if any of the requested education levels match
                for edu_level in filters.education_levels:
                    if edu_level.value in scheme_edu_levels:
                        filtered_results.append(scheme)
                        break
            
            results = filtered_results
        
        # Apply income filter (post-query for SQLite compatibility)
        if filters.income_max is not None:
            filtered_results = []
            for scheme in results:
                criteria = scheme.eligibility_criteria or {}
                scheme_income_max = criteria.get('income_max')
                
                # Include scheme if it has no income requirement or if requirement is <= user's income
                if scheme_income_max is None or scheme_income_max <= filters.income_max:
                    filtered_results.append(scheme)
            
            results = filtered_results
        
        return results
    
    def _get_descendant_location_ids(self, location_id: UUID) -> List[UUID]:
        """
        Get all descendant location IDs for a given location using hierarchy.
        
        This method recursively finds all child locations at any depth below
        the specified location in the hierarchy.
        
        Args:
            location_id: UUID of the parent location
            
        Returns:
            List of descendant location UUIDs
        """
        descendants = []
        children = self.location_service.get_children(location_id)
        
        for child in children:
            descendants.append(child.id)
            # Recursively get descendants of this child
            child_descendants = self._get_descendant_location_ids(child.id)
            descendants.extend(child_descendants)
        
        return descendants
    
    def search(
        self, 
        query: str, 
        filters: Optional[SchemeFilters] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Tuple[Scheme, float]]:
        """
        Search schemes using full-text search with optional filters and pagination.
        
        Uses PostgreSQL full-text search when available for better performance
        and relevance ranking. Falls back to ILIKE pattern matching for SQLite.
        
        The search query supports:
        - Single words: "scholarship"
        - Multiple words: "engineering scholarship"
        - Phrase queries: "computer science"
        
        Results are ranked by relevance score, with matches in the name
        weighted higher than matches in the description.
        
        Args:
            query: Search query string
            filters: Optional SchemeFilters to combine with search
            limit: Maximum number of results to return (default: 50)
            offset: Number of results to skip for pagination (default: 0)
            
        Returns:
            List of tuples (Scheme, relevance_score) sorted by relevance
            
        Requirements: 6.1, 6.2, 7.1
        """
        if not query or not query.strip():
            # If no query, just use filter
            schemes = self.filter(filters or SchemeFilters(), limit=limit, offset=offset)
            return [(scheme, 0.0) for scheme in schemes]
        
        # Start with base query
        base_query = self.db.query(Scheme)
        
        # Check database dialect
        dialect = self.db.bind.dialect.name
        
        if dialect == 'postgresql':
            # Use PostgreSQL full-text search
            results = self._search_postgresql(query, filters, base_query, limit, offset)
        else:
            # Fallback to ILIKE for SQLite and other databases
            results = self._search_fallback(query, filters, base_query, limit, offset)
        
        return results
    
    def _search_postgresql(
        self, 
        query: str, 
        filters: Optional[SchemeFilters],
        base_query,
        limit: int,
        offset: int
    ) -> List[Tuple[Scheme, float]]:
        """
        Perform full-text search using PostgreSQL's tsvector and tsquery with pagination.
        
        Uses the search_vector column with GIN index for fast searching.
        Implements fuzzy matching using trigram similarity for typo tolerance.
        
        Args:
            query: Search query string
            filters: Optional filters to apply
            base_query: Base SQLAlchemy query
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of tuples (Scheme, relevance_score) sorted by relevance
        """
        from sqlalchemy.orm import joinedload
        
        # Add eager loading to avoid N+1 queries
        base_query = base_query.options(joinedload(Scheme.location))
        
        # Get the search_vector column dynamically (it's added by migration)
        search_vector_col = getattr(Scheme.__table__.c, 'search_vector', None)
        
        if search_vector_col is None:
            # Fallback if search_vector doesn't exist
            return self._search_fallback(query, filters, base_query, limit, offset)
        
        # Create tsquery from search string
        # Use plainto_tsquery for simple query parsing (handles multiple words)
        tsquery = func.plainto_tsquery('english', query)
        
        # Calculate relevance score using ts_rank
        # ts_rank returns a relevance score based on how well the document matches
        relevance = func.ts_rank(
            search_vector_col,
            tsquery
        ).label('relevance')
        
        # Also calculate trigram similarity for fuzzy matching
        # This helps with typos and partial matches
        name_similarity = func.similarity(Scheme.name, query).label('name_sim')
        desc_similarity = func.similarity(
            func.coalesce(Scheme.description, ''), 
            query
        ).label('desc_sim')
        
        # Combined score: prioritize full-text match, boost with trigram similarity
        # Name matches are weighted higher than description matches
        combined_score = (
            relevance * 10.0 + 
            name_similarity * 5.0 + 
            desc_similarity * 2.0
        ).label('score')
        
        # Build query with relevance scoring
        search_query = base_query.add_columns(combined_score).filter(
            or_(
                # Match using full-text search
                search_vector_col.op('@@')(tsquery),
                # Also include trigram matches for fuzzy matching (typo tolerance)
                func.similarity(Scheme.name, query) > 0.3,
                func.similarity(func.coalesce(Scheme.description, ''), query) > 0.3
            )
        )
        
        # Apply filters if provided
        if filters:
            search_query = self._apply_filters_to_query(search_query, filters)
        else:
            # Default to ACTIVE status
            search_query = search_query.filter(Scheme.status == SchemeStatus.ACTIVE)
        
        # Order by relevance score (highest first)
        search_query = search_query.order_by(text('score DESC'))
        
        # Apply pagination
        search_query = search_query.limit(limit).offset(offset)
        
        # Execute query and extract results
        results = search_query.all()
        
        # Apply post-query filters (education level, income)
        filtered_results = []
        for row in results:
            scheme = row[0]
            score = float(row[1])
            
            # Apply education level filter if specified
            if filters and filters.education_levels:
                criteria = scheme.eligibility_criteria or {}
                scheme_edu_levels = criteria.get('education_level', [])
                
                has_matching_edu = any(
                    edu_level.value in scheme_edu_levels 
                    for edu_level in filters.education_levels
                )
                
                if not has_matching_edu:
                    continue
            
            # Apply income filter if specified
            if filters and filters.income_max is not None:
                criteria = scheme.eligibility_criteria or {}
                scheme_income_max = criteria.get('income_max')
                
                if scheme_income_max is not None and scheme_income_max > filters.income_max:
                    continue
            
            filtered_results.append((scheme, score))
        
        return filtered_results
    
    def _search_fallback(
        self, 
        query: str, 
        filters: Optional[SchemeFilters],
        base_query,
        limit: int,
        offset: int
    ) -> List[Tuple[Scheme, float]]:
        """
        Fallback search using ILIKE pattern matching for SQLite with pagination.
        
        Provides basic search functionality without full-text search capabilities.
        Ranks results based on where the match occurs (name vs description).
        
        Args:
            query: Search query string
            filters: Optional filters to apply
            base_query: Base SQLAlchemy query
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of tuples (Scheme, relevance_score) sorted by relevance
        """
        from sqlalchemy.orm import joinedload
        
        # Add eager loading to avoid N+1 queries
        base_query = base_query.options(joinedload(Scheme.location))
        
        search_pattern = f"%{query}%"
        
        # Search in name and description using ILIKE
        search_query = base_query.filter(
            or_(
                Scheme.name.ilike(search_pattern),
                Scheme.description.ilike(search_pattern)
            )
        )
        
        # Apply filters if provided
        if filters:
            search_query = self._apply_filters_to_query(search_query, filters)
        else:
            # Default to ACTIVE status
            search_query = search_query.filter(Scheme.status == SchemeStatus.ACTIVE)
        
        # Apply pagination
        search_query = search_query.limit(limit).offset(offset)
        
        # Execute query
        schemes = search_query.all()
        
        # Apply post-query filters and calculate simple relevance scores
        results = []
        for scheme in schemes:
            # Apply education level filter if specified
            if filters and filters.education_levels:
                criteria = scheme.eligibility_criteria or {}
                scheme_edu_levels = criteria.get('education_level', [])
                
                has_matching_edu = any(
                    edu_level.value in scheme_edu_levels 
                    for edu_level in filters.education_levels
                )
                
                if not has_matching_edu:
                    continue
            
            # Apply income filter if specified
            if filters and filters.income_max is not None:
                criteria = scheme.eligibility_criteria or {}
                scheme_income_max = criteria.get('income_max')
                
                if scheme_income_max is not None and scheme_income_max > filters.income_max:
                    continue
            
            # Calculate simple relevance score
            score = 0.0
            query_lower = query.lower()
            name_lower = scheme.name.lower()
            desc_lower = (scheme.description or '').lower()
            
            # Exact match in name gets highest score
            if query_lower == name_lower:
                score = 10.0
            # Name starts with query
            elif name_lower.startswith(query_lower):
                score = 8.0
            # Query appears in name
            elif query_lower in name_lower:
                score = 5.0
            # Query appears in description
            elif query_lower in desc_lower:
                score = 2.0
            else:
                score = 1.0
            
            results.append((scheme, score))
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def get_suggestions(self, partial: str, limit: int = 10) -> List[str]:
        """
        Get autocomplete suggestions based on partial input.
        
        Uses PostgreSQL's trigram similarity (pg_trgm) for fuzzy matching
        to handle typos. For SQLite, uses simple LIKE matching as fallback.
        
        Returns unique scheme names that match the partial input, ordered
        by relevance/similarity score.
        
        Args:
            partial: Partial text input from user
            limit: Maximum number of suggestions to return (default: 10)
            
        Returns:
            List of scheme name suggestions
            
        Requirements: 6.1
        """
        if not partial or not partial.strip():
            return []
        
        partial = partial.strip()
        
        # Check database dialect
        dialect = self.db.bind.dialect.name
        
        if dialect == 'postgresql':
            # Use PostgreSQL trigram similarity for fuzzy matching
            similarity_score = func.similarity(Scheme.name, partial).label('similarity')
            
            # Query schemes with similarity score
            query = self.db.query(Scheme.name, similarity_score).filter(
                and_(
                    Scheme.status == SchemeStatus.ACTIVE,
                    # Use trigram similarity threshold
                    func.similarity(Scheme.name, partial) > 0.1
                )
            ).order_by(text('similarity DESC')).limit(limit)
            
            results = query.all()
            return [row[0] for row in results]
        else:
            # Fallback to LIKE matching for SQLite
            search_pattern = f"%{partial}%"
            
            query = self.db.query(Scheme.name).filter(
                and_(
                    Scheme.status == SchemeStatus.ACTIVE,
                    Scheme.name.ilike(search_pattern)
                )
            ).distinct().limit(limit)
            
            results = query.all()
            
            # Sort by relevance (prefer matches at start of name)
            suggestions = [row[0] for row in results]
            partial_lower = partial.lower()
            
            # Sort: exact match first, then starts with, then contains
            def sort_key(name):
                name_lower = name.lower()
                if name_lower == partial_lower:
                    return (0, name)
                elif name_lower.startswith(partial_lower):
                    return (1, name)
                else:
                    return (2, name)
            
            suggestions.sort(key=sort_key)
            return suggestions
    
    def _apply_filters_to_query(self, query, filters: SchemeFilters):
        """
        Apply SchemeFilters to a SQLAlchemy query.
        
        This is a helper method to avoid code duplication between
        filter() and search() methods.
        
        Args:
            query: SQLAlchemy query object
            filters: SchemeFilters to apply
            
        Returns:
            Modified query with filters applied
        """
        # Apply location filter with hierarchy support
        if filters.location_ids:
            all_location_ids = set(filters.location_ids)
            for location_id in filters.location_ids:
                descendant_ids = self._get_descendant_location_ids(location_id)
                all_location_ids.update(descendant_ids)
            
            query = query.filter(Scheme.location_id.in_(all_location_ids))
        
        # Apply scheme type filter
        if filters.scheme_types:
            query = query.filter(Scheme.scheme_type.in_(filters.scheme_types))
        
        # Apply deadline range filters
        if filters.deadline_before:
            query = query.filter(
                or_(
                    Scheme.deadline <= filters.deadline_before,
                    Scheme.deadline.is_(None)
                )
            )
        
        if filters.deadline_after:
            query = query.filter(
                and_(
                    Scheme.deadline >= filters.deadline_after,
                    Scheme.deadline.isnot(None)
                )
            )
        
        # Apply status filter (default to ACTIVE if not specified)
        if filters.status:
            query = query.filter(Scheme.status == filters.status)
        else:
            query = query.filter(Scheme.status == SchemeStatus.ACTIVE)
        
        return query
