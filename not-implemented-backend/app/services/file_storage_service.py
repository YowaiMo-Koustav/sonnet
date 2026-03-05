"""
File Storage Service for handling PDF document uploads and storage.

This service manages the storage of uploaded PDF files to the local filesystem
or object storage. It handles file validation, storage, and retrieval.
"""
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from datetime import datetime

from app.core.config import get_settings


class FileStorageService:
    """Service for managing file storage operations."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the file storage service.
        
        Args:
            storage_path: Base path for file storage. If None, uses settings.
        """
        settings = get_settings()
        self.storage_path = Path(storage_path or settings.pdf_storage_path)
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self) -> None:
        """Ensure the storage directory exists."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_pdf(
        self,
        file: BinaryIO,
        filename: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[str, int]:
        """
        Save an uploaded PDF file to storage.
        
        Args:
            file: Binary file object to save
            filename: Original filename
            user_id: Optional user ID who uploaded the file
            
        Returns:
            Tuple of (file_path, file_size) where file_path is the relative path
            from storage_path and file_size is in bytes
            
        Raises:
            ValueError: If the file is invalid or empty
            IOError: If file storage fails
        """
        # Generate unique filename to avoid collisions
        file_id = uuid.uuid4()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = self._sanitize_filename(filename)
        unique_filename = f"{timestamp}_{file_id}_{safe_filename}"
        
        # Organize files by date for better organization
        date_folder = datetime.utcnow().strftime("%Y/%m/%d")
        file_dir = self.storage_path / date_folder
        file_dir.mkdir(parents=True, exist_ok=True)
        
        # Full path for the file
        file_path = file_dir / unique_filename
        relative_path = str(Path(date_folder) / unique_filename)
        
        # Read and validate file content
        file_content = file.read()
        if not file_content:
            raise ValueError("File is empty")
        
        file_size = len(file_content)
        
        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise ValueError(f"File size exceeds maximum allowed size of {max_size} bytes")
        
        # Write file to storage
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            raise IOError(f"Failed to save file: {str(e)}")
        
        return relative_path, file_size
    
    def get_pdf(self, file_path: str) -> bytes:
        """
        Retrieve a PDF file from storage.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            File content as bytes
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If file reading fails
        """
        full_path = self.storage_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Failed to read file: {str(e)}")
    
    def delete_pdf(self, file_path: str) -> None:
        """
        Delete a PDF file from storage.
        
        Args:
            file_path: Relative path to the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If file deletion fails
        """
        full_path = self.storage_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            full_path.unlink()
        except Exception as e:
            raise IOError(f"Failed to delete file: {str(e)}")
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            True if file exists, False otherwise
        """
        full_path = self.storage_path / file_path
        return full_path.exists()
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get the size of a file in storage.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            File size in bytes
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        full_path = self.storage_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return full_path.stat().st_size
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to remove potentially dangerous characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path separators and other dangerous characters
        dangerous_chars = ['/', '\\', '..', '\0']
        sanitized = filename
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit filename length
        max_length = 200
        if len(sanitized) > max_length:
            # Keep the extension
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:max_length - len(ext)] + ext
        
        return sanitized
