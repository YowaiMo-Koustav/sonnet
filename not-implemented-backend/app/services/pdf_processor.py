"""
PDF Processor Service for extracting text from PDF documents.

This service handles PDF text extraction while preserving reading order
and document structure. It uses pdfplumber as the primary extraction library
with PyPDF2 as a fallback.
"""
import io
import uuid
from typing import Dict, Any, Optional, BinaryIO
from datetime import datetime

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from sqlalchemy.orm import Session

from app.models.pdf_document import PDFDocument, ProcessingStatus
from app.services.file_storage_service import FileStorageService
from app.services.gemini_service import GeminiService, GeminiServiceError


class PDFProcessingError(Exception):
    """Exception raised when PDF processing fails."""
    pass


class PDFProcessor:
    """Service for processing PDF documents and extracting text content."""
    
    def __init__(self, db: Session, storage_service: Optional[FileStorageService] = None):
        """
        Initialize the PDF processor.
        
        Args:
            db: Database session for storing processing results
            storage_service: File storage service for retrieving PDFs
        """
        self.db = db
        self.storage_service = storage_service or FileStorageService()
        self.gemini_service = None  # Lazy initialization
        
        if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
            raise RuntimeError("No PDF processing library available. Install pdfplumber or PyPDF2.")
    
    def ingest_pdf(
        self,
        file: BinaryIO,
        filename: str,
        user_id: Optional[uuid.UUID] = None,
        process_immediately: bool = True
    ) -> PDFDocument:
        """
        Ingest a PDF file and initiate processing.
        
        This method:
        1. Saves the PDF file to storage
        2. Creates a PDFDocument record in the database
        3. Optionally processes the PDF immediately to extract text
        
        Args:
            file: Binary file object containing the PDF
            filename: Original filename of the PDF
            user_id: Optional ID of the user uploading the file
            process_immediately: If True, extract text immediately; if False, mark as PENDING
            
        Returns:
            PDFDocument object with processing status and extracted data
            
        Raises:
            ValueError: If the file is invalid
            PDFProcessingError: If processing fails
        """
        # Save the PDF file to storage
        try:
            file_path, file_size = self.storage_service.save_pdf(file, filename, user_id)
        except (ValueError, IOError) as e:
            raise ValueError(f"Failed to save PDF file: {str(e)}")
        
        # Detect MIME type
        mime_type = "application/pdf"
        
        # Create PDFDocument record
        pdf_doc = PDFDocument(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            processing_status=ProcessingStatus.PENDING,
            uploaded_by=user_id
        )
        
        self.db.add(pdf_doc)
        self.db.commit()
        self.db.refresh(pdf_doc)
        
        # Process immediately if requested
        if process_immediately:
            try:
                self._process_pdf(pdf_doc)
            except Exception as e:
                # Mark as failed but don't raise - the document is saved
                pdf_doc.processing_status = ProcessingStatus.FAILED
                pdf_doc.extracted_data = {"error": str(e)}
                self.db.commit()
                raise PDFProcessingError(f"PDF processing failed: {str(e)}")
        
        return pdf_doc
    
    def _process_pdf(self, pdf_doc: PDFDocument) -> None:
        """
        Process a PDF document to extract text content.
        
        Args:
            pdf_doc: PDFDocument object to process
            
        Raises:
            PDFProcessingError: If extraction fails
        """
        # Update status to PROCESSING
        pdf_doc.processing_status = ProcessingStatus.PROCESSING
        self.db.commit()
        
        try:
            # Retrieve the PDF file from storage
            pdf_content = self.storage_service.get_pdf(pdf_doc.file_path)
            
            # Extract text using available library
            extracted_text = self._extract_text(pdf_content)
            
            # Store extracted data
            pdf_doc.extracted_data = {
                "text": extracted_text,
                "page_count": self._count_pages(pdf_content),
                "extraction_method": "pdfplumber" if PDFPLUMBER_AVAILABLE else "pypdf2",
                "extracted_at": datetime.utcnow().isoformat()
            }
            
            # Mark as completed
            pdf_doc.processing_status = ProcessingStatus.COMPLETED
            self.db.commit()
            
        except Exception as e:
            pdf_doc.processing_status = ProcessingStatus.FAILED
            pdf_doc.extracted_data = {"error": str(e)}
            self.db.commit()
            raise PDFProcessingError(f"Text extraction failed: {str(e)}")
    
    def _extract_text(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content while preserving reading order.
        
        Uses pdfplumber as the primary method (better layout preservation)
        with PyPDF2 as a fallback.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            PDFProcessingError: If extraction fails with all methods
        """
        # Try pdfplumber first (better layout and table handling)
        if PDFPLUMBER_AVAILABLE:
            try:
                return self._extract_with_pdfplumber(pdf_content)
            except Exception as e:
                # If pdfplumber fails and PyPDF2 is available, try it
                if PYPDF2_AVAILABLE:
                    try:
                        return self._extract_with_pypdf2(pdf_content)
                    except Exception:
                        raise PDFProcessingError(f"Text extraction failed: {str(e)}")
                else:
                    raise PDFProcessingError(f"Text extraction failed: {str(e)}")
        
        # Fall back to PyPDF2
        elif PYPDF2_AVAILABLE:
            try:
                return self._extract_with_pypdf2(pdf_content)
            except Exception as e:
                raise PDFProcessingError(f"Text extraction failed: {str(e)}")
        
        else:
            raise PDFProcessingError("No PDF processing library available")
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> str:
        """
        Extract text using pdfplumber (preserves layout better).
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text content
        """
        text_parts = []
        
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                # Extract text while preserving layout
                page_text = page.extract_text(layout=True)
                if page_text:
                    text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> str:
        """
        Extract text using PyPDF2 (fallback method).
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text content
        """
        text_parts = []
        
        reader = PdfReader(io.BytesIO(pdf_content))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def _count_pages(self, pdf_content: bytes) -> int:
        """
        Count the number of pages in a PDF.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Number of pages
        """
        try:
            if PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                    return len(pdf.pages)
            elif PYPDF2_AVAILABLE:
                reader = PdfReader(io.BytesIO(pdf_content))
                return len(reader.pages)
        except Exception:
            return 0
        
        return 0
    
    def get_processing_status(self, job_id: uuid.UUID) -> Optional[PDFDocument]:
        """
        Get the processing status of a PDF document.
        
        Args:
            job_id: ID of the PDF document
            
        Returns:
            PDFDocument object or None if not found
        """
        return self.db.query(PDFDocument).filter(PDFDocument.id == job_id).first()
    
    def get_extraction_results(self, job_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get the extraction results for a processed PDF.
        
        Args:
            job_id: ID of the PDF document
            
        Returns:
            Dictionary containing extracted data or None if not found/not processed
        """
        pdf_doc = self.get_processing_status(job_id)
        
        if not pdf_doc:
            return None
        
        if pdf_doc.processing_status != ProcessingStatus.COMPLETED:
            return {
                "status": pdf_doc.processing_status.value,
                "extracted_data": pdf_doc.extracted_data
            }
        
        return pdf_doc.extracted_data
    
    def extract_scholarship_data_with_gemini(self, pdf_doc: PDFDocument) -> Dict[str, Any]:
        """
        Extract structured scholarship data from PDF using Gemini AI.
        
        Args:
            pdf_doc: PDFDocument object with extracted text
            
        Returns:
            Dictionary containing structured scholarship data
            
        Raises:
            PDFProcessingError: If extraction fails
        """
        # Lazy initialize Gemini service
        if self.gemini_service is None:
            try:
                self.gemini_service = GeminiService()
            except ValueError as e:
                raise PDFProcessingError(f"Gemini service not configured: {str(e)}")
        
        # Check if PDF has been processed
        if pdf_doc.processing_status != ProcessingStatus.COMPLETED:
            raise PDFProcessingError("PDF must be processed before extracting scholarship data")
        
        # Get extracted text
        extracted_text = pdf_doc.extracted_data.get("text", "")
        if not extracted_text:
            raise PDFProcessingError("No text found in PDF")
        
        try:
            # Use Gemini to extract structured data
            scholarship_data = self.gemini_service.extract_scholarship_from_pdf(
                pdf_text=extracted_text,
                filename=pdf_doc.filename
            )
            
            # Update PDF document with structured data
            pdf_doc.extracted_data["scholarship_data"] = scholarship_data
            self.db.commit()
            
            return scholarship_data
            
        except GeminiServiceError as e:
            raise PDFProcessingError(f"Gemini extraction failed: {str(e)}")
