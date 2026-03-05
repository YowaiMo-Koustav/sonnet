"""PDF processing API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import io

from app.core.database import get_db
from app.services.pdf_processor import PDFProcessor, PDFProcessingError
from app.services.file_storage_service import FileStorageService
from app.api.schemas import (
    PDFUploadResponse,
    PDFStatusResponse,
    PDFExtractionResultsResponse,
)
from app.models.pdf_document import PDFDocument, ProcessingStatus


router = APIRouter(prefix="/api/pdf", tags=["pdf"])


@router.post("/upload", response_model=PDFUploadResponse, status_code=201)
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Upload and process a PDF document.
    
    This endpoint accepts a PDF file, stores it, and initiates text extraction.
    The processing happens synchronously, so the response includes the initial
    processing status.
    
    Requirements: 2.1, 2.2, 2.3
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are accepted."
        )
    
    # Validate content type
    if file.content_type and file.content_type != 'application/pdf':
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Expected application/pdf."
        )
    
    try:
        # Initialize services
        storage_service = FileStorageService()
        processor = PDFProcessor(db, storage_service)
        
        # Ingest the PDF
        pdf_doc = processor.ingest_pdf(
            file=file.file,
            filename=file.filename,
            user_id=user_id,
            process_immediately=True
        )
        
        return PDFUploadResponse(
            id=pdf_doc.id,
            filename=pdf_doc.filename,
            file_size=pdf_doc.file_size,
            processing_status=pdf_doc.processing_status.value,
            message="PDF uploaded and processing initiated successfully"
        )
    
    except ValueError as e:
        # Handle validation errors (invalid file, empty file, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    
    except PDFProcessingError as e:
        # Handle processing errors - file is saved but processing failed
        raise HTTPException(status_code=422, detail=str(e))
    
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{id}/status", response_model=PDFStatusResponse)
def get_pdf_status(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the processing status of a PDF document.
    
    Returns the current processing status and basic metadata about the PDF.
    
    Requirements: 2.1, 2.2
    """
    processor = PDFProcessor(db)
    pdf_doc = processor.get_processing_status(id)
    
    if not pdf_doc:
        raise HTTPException(status_code=404, detail="PDF document not found")
    
    return PDFStatusResponse(
        id=pdf_doc.id,
        filename=pdf_doc.filename,
        file_size=pdf_doc.file_size,
        processing_status=pdf_doc.processing_status.value,
        uploaded_at=pdf_doc.created_at,
        updated_at=pdf_doc.updated_at
    )


@router.get("/{id}/results", response_model=PDFExtractionResultsResponse)
def get_pdf_results(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the extraction results for a processed PDF.
    
    Returns the extracted text and metadata if processing is complete.
    If processing is still in progress or failed, returns the current status.
    
    Requirements: 2.5, 3.1, 4.1
    """
    processor = PDFProcessor(db)
    pdf_doc = processor.get_processing_status(id)
    
    if not pdf_doc:
        raise HTTPException(status_code=404, detail="PDF document not found")
    
    # Check if processing is complete
    if pdf_doc.processing_status == ProcessingStatus.PENDING:
        raise HTTPException(
            status_code=202,
            detail="PDF processing has not started yet"
        )
    
    if pdf_doc.processing_status == ProcessingStatus.PROCESSING:
        raise HTTPException(
            status_code=202,
            detail="PDF is currently being processed"
        )
    
    if pdf_doc.processing_status == ProcessingStatus.FAILED:
        error_message = pdf_doc.extracted_data.get("error", "Unknown error") if pdf_doc.extracted_data else "Unknown error"
        raise HTTPException(
            status_code=422,
            detail=f"PDF processing failed: {error_message}"
        )
    
    # Processing is complete, return results
    extraction_results = processor.get_extraction_results(id)
    
    return PDFExtractionResultsResponse(
        id=pdf_doc.id,
        filename=pdf_doc.filename,
        processing_status=pdf_doc.processing_status.value,
        extracted_data=extraction_results or {},
        confidence_scores=pdf_doc.confidence_scores or {}
    )


@router.get("/{id}/download")
async def download_pdf(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Download the original PDF document.
    
    Returns the original uploaded PDF file as a binary stream.
    
    Requirements: 2.4
    """
    # Get PDF document metadata
    pdf_doc = db.query(PDFDocument).filter(PDFDocument.id == id).first()
    
    if not pdf_doc:
        raise HTTPException(status_code=404, detail="PDF document not found")
    
    try:
        # Retrieve the file from storage
        storage_service = FileStorageService()
        file_content = storage_service.get_pdf(pdf_doc.file_path)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{pdf_doc.filename}"',
                "Content-Length": str(len(file_content))
            }
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="PDF file not found in storage"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve PDF: {str(e)}"
        )



@router.post("/{id}/extract-scholarship", status_code=200)
def extract_scholarship_with_gemini(
    id: UUID,
    db: Session = Depends(get_db)
):
    """
    Extract structured scholarship data from PDF using Gemini AI.
    
    This endpoint uses Gemini to intelligently extract scholarship information
    including eligibility criteria, deadlines, benefits, and application details.
    
    The PDF must be processed (text extracted) before calling this endpoint.
    """
    processor = PDFProcessor(db)
    pdf_doc = processor.get_processing_status(id)
    
    if not pdf_doc:
        raise HTTPException(status_code=404, detail="PDF document not found")
    
    if pdf_doc.processing_status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"PDF must be processed before extracting scholarship data. Current status: {pdf_doc.processing_status.value}"
        )
    
    try:
        scholarship_data = processor.extract_scholarship_data_with_gemini(pdf_doc)
        
        return {
            "id": pdf_doc.id,
            "filename": pdf_doc.filename,
            "scholarship_data": scholarship_data,
            "message": "Scholarship data extracted successfully using Gemini AI"
        }
    
    except PDFProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract scholarship data: {str(e)}"
        )
