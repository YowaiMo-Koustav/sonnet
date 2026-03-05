"""Gemini AI-powered API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.services.gemini_service import GeminiService, GeminiServiceError
from app.models.scheme import Scheme


router = APIRouter(prefix="/api/gemini", tags=["gemini"])


# Request/Response Models
class EligibilityMatchRequest(BaseModel):
    user_profile: Dict[str, Any]
    scheme_id: int


class EligibilityMatchResponse(BaseModel):
    match_score: int
    is_eligible: bool
    matched_criteria: List[str]
    missing_criteria: List[str]
    explanation: str
    suggestions: List[str]
    confidence: float


class RecommendationsRequest(BaseModel):
    user_profile: Dict[str, Any]
    limit: int = 5


class RecommendationItem(BaseModel):
    scholarship_id: int
    rank: int
    match_score: int
    reason: str


class SemanticSearchRequest(BaseModel):
    query: str
    user_profile: Dict[str, Any]


class SearchResult(BaseModel):
    scholarship_id: int
    relevance_score: int
    match_reason: str


class SemanticSearchResponse(BaseModel):
    results: List[SearchResult]
    query_understanding: str
    suggested_filters: Dict[str, Any]


class WebExtractionRequest(BaseModel):
    html_content: str
    url: str


@router.post("/match-eligibility", response_model=EligibilityMatchResponse)
def match_eligibility(
    request: EligibilityMatchRequest,
    db: Session = Depends(get_db)
):
    """
    Match user profile against scholarship eligibility using Gemini AI.
    
    Returns detailed eligibility analysis with match score, explanations,
    and suggestions for improvement.
    """
    # Get scheme from database
    scheme = db.query(Scheme).filter(Scheme.id == request.scheme_id).first()
    
    if not scheme:
        raise HTTPException(status_code=404, detail="Scholarship not found")
    
    try:
        gemini_service = GeminiService()
        
        result = gemini_service.match_eligibility(
            user_profile=request.user_profile,
            scheme_eligibility=scheme.eligibility_criteria or {},
            scheme_name=scheme.name
        )
        
        return EligibilityMatchResponse(**result)
    
    except GeminiServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eligibility matching failed: {str(e)}"
        )


@router.post("/recommendations", response_model=List[RecommendationItem])
def get_recommendations(
    request: RecommendationsRequest,
    db: Session = Depends(get_db)
):
    """
    Get personalized scholarship recommendations using Gemini AI.
    
    Returns ranked list of scholarships with match scores and reasons.
    """
    try:
        # Get all active schemes
        schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
        
        if not schemes:
            return []
        
        # Convert to dict format
        scholarships = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "eligibility": s.eligibility_criteria,
                "benefit_amount": s.benefit_amount,
                "deadline": s.deadline.isoformat() if s.deadline else None
            }
            for s in schemes
        ]
        
        gemini_service = GeminiService()
        
        recommendations = gemini_service.generate_recommendations(
            user_profile=request.user_profile,
            scholarships=scholarships,
            limit=request.limit
        )
        
        return [RecommendationItem(**rec) for rec in recommendations]
    
    except GeminiServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation generation failed: {str(e)}"
        )


@router.post("/semantic-search", response_model=SemanticSearchResponse)
def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Perform semantic search on scholarships using Gemini AI.
    
    Understands query intent and ranks scholarships by relevance.
    """
    try:
        # Get all active schemes
        schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
        
        if not schemes:
            return SemanticSearchResponse(
                results=[],
                query_understanding="No scholarships available",
                suggested_filters={}
            )
        
        # Convert to dict format
        scholarships = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "eligibility": s.eligibility_criteria
            }
            for s in schemes
        ]
        
        gemini_service = GeminiService()
        
        result = gemini_service.semantic_search(
            query=request.query,
            user_profile=request.user_profile,
            scholarships=scholarships
        )
        
        return SemanticSearchResponse(
            results=[SearchResult(**r) for r in result.get("results", [])],
            query_understanding=result.get("query_understanding", ""),
            suggested_filters=result.get("suggested_filters", {})
        )
    
    except GeminiServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.post("/extract-from-web")
def extract_from_web(
    request: WebExtractionRequest
):
    """
    Extract scholarship data from web page HTML using Gemini AI.
    
    Returns structured scholarship data extracted from the provided HTML content.
    """
    try:
        gemini_service = GeminiService()
        
        scholarship_data = gemini_service.extract_from_web_content(
            html_content=request.html_content,
            url=request.url
        )
        
        return {
            "scholarship_data": scholarship_data,
            "message": "Scholarship data extracted successfully from web content"
        }
    
    except GeminiServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Web content extraction failed: {str(e)}"
        )
