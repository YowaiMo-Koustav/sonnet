"""Response payload optimization utilities."""
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, date
from uuid import UUID


class ResponseOptimizer:
    """
    Utility class to minimize response payload sizes.
    
    Removes null values, empty collections, and unnecessary fields
    to reduce bandwidth usage for low-bandwidth connections.
    """
    
    @staticmethod
    def remove_null_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove keys with null/None values from a dictionary.
        
        Args:
            data: Dictionary to clean
            
        Returns:
            Dictionary with null values removed
        """
        return {k: v for k, v in data.items() if v is not None}
    
    @staticmethod
    def remove_empty_collections(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove keys with empty lists or dicts from a dictionary.
        
        Args:
            data: Dictionary to clean
            
        Returns:
            Dictionary with empty collections removed
        """
        cleaned = {}
        for k, v in data.items():
            if isinstance(v, (list, dict)) and not v:
                continue
            cleaned[k] = v
        return cleaned
    
    @staticmethod
    def exclude_fields(data: Dict[str, Any], exclude: Set[str]) -> Dict[str, Any]:
        """
        Remove specified fields from a dictionary.
        
        Args:
            data: Dictionary to filter
            exclude: Set of field names to exclude
            
        Returns:
            Dictionary with excluded fields removed
        """
        return {k: v for k, v in data.items() if k not in exclude}
    
    @staticmethod
    def include_only_fields(data: Dict[str, Any], include: Set[str]) -> Dict[str, Any]:
        """
        Keep only specified fields in a dictionary.
        
        Args:
            data: Dictionary to filter
            include: Set of field names to include
            
        Returns:
            Dictionary with only included fields
        """
        return {k: v for k, v in data.items() if k in include}
    
    @staticmethod
    def serialize_for_json(obj: Any) -> Any:
        """
        Convert objects to JSON-serializable format.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: ResponseOptimizer.serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [ResponseOptimizer.serialize_for_json(item) for item in obj]
        return obj
    
    @staticmethod
    def optimize_response(
        data: Any,
        remove_nulls: bool = True,
        remove_empty: bool = True,
        exclude: Optional[Set[str]] = None,
        include: Optional[Set[str]] = None,
    ) -> Any:
        """
        Apply multiple optimizations to response data.
        
        Args:
            data: Response data to optimize
            remove_nulls: Whether to remove null values
            remove_empty: Whether to remove empty collections
            exclude: Fields to exclude
            include: Fields to include (if set, only these fields are kept)
            
        Returns:
            Optimized response data
        """
        if not isinstance(data, dict):
            if isinstance(data, list):
                return [
                    ResponseOptimizer.optimize_response(
                        item, remove_nulls, remove_empty, exclude, include
                    )
                    for item in data
                ]
            return data
        
        result = data.copy()
        
        # Apply field filtering first
        if include:
            result = ResponseOptimizer.include_only_fields(result, include)
        elif exclude:
            result = ResponseOptimizer.exclude_fields(result, exclude)
        
        # Remove nulls
        if remove_nulls:
            result = ResponseOptimizer.remove_null_values(result)
        
        # Remove empty collections
        if remove_empty:
            result = ResponseOptimizer.remove_empty_collections(result)
        
        # Recursively optimize nested objects
        for key, value in result.items():
            if isinstance(value, dict):
                result[key] = ResponseOptimizer.optimize_response(
                    value, remove_nulls, remove_empty, exclude, include
                )
            elif isinstance(value, list):
                result[key] = [
                    ResponseOptimizer.optimize_response(
                        item, remove_nulls, remove_empty, exclude, include
                    )
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
        
        return result
    
    @staticmethod
    def create_minimal_scheme_response(scheme_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a minimal scheme response for list views.
        
        Includes only essential fields for browsing, reducing payload size.
        
        Args:
            scheme_data: Full scheme data
            
        Returns:
            Minimal scheme response
        """
        essential_fields = {
            "id",
            "name",
            "location_id",
            "scheme_type",
            "deadline",
            "status",
            "approaching_deadline",
        }
        return ResponseOptimizer.include_only_fields(scheme_data, essential_fields)
    
    @staticmethod
    def create_minimal_location_response(location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a minimal location response for list views.
        
        Args:
            location_data: Full location data
            
        Returns:
            Minimal location response
        """
        essential_fields = {"id", "name", "type", "parent_id"}
        return ResponseOptimizer.include_only_fields(location_data, essential_fields)
    
    @staticmethod
    def create_minimal_application_response(app_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a minimal application response for list views.
        
        Args:
            app_data: Full application data
            
        Returns:
            Minimal application response
        """
        essential_fields = {
            "id",
            "scheme_id",
            "status",
            "updated_at",
        }
        return ResponseOptimizer.include_only_fields(app_data, essential_fields)
