"""
Gemini AI Service for intelligent scholarship processing.

This service provides a unified interface for all AI-powered features:
- PDF extraction and parsing
- Web content extraction
- Eligibility matching
- Personalized recommendations
- Semantic search
- Multi-language support
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai

from app.core.config import get_settings
from app.services.cache_service import CacheService


class GeminiServiceError(Exception):
    """Exception raised when Gemini API calls fail."""
    pass


class GeminiService:
    """Service for all Gemini AI operations."""
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        """
        Initialize the Gemini service.
        
        Args:
            cache_service: Optional cache service for response caching
        """
        # Configure Gemini API
        settings = get_settings()
        api_key = os.getenv("GEMINI_API_KEY") or settings.gemini_api_key
        if not api_key or api_key == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY not configured in environment")
        
        genai.configure(api_key=api_key)
        
        # Initialize models
        self.flash_model = genai.GenerativeModel('gemini-1.5-flash')  # Fast, cheap
        self.pro_model = genai.GenerativeModel('gemini-1.5-pro')      # Powerful, expensive
        
        # Cache service for reducing API calls
        self.cache = cache_service or CacheService()
    
    def _call_gemini(
        self,
        prompt: str,
        use_pro: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: int = 3600
    ) -> str:
        """
        Call Gemini API with caching and error handling.
        
        Args:
            prompt: The prompt to send to Gemini
            use_pro: If True, use Pro model; otherwise use Flash
            cache_key: Optional cache key for response caching
            cache_ttl: Cache TTL in seconds (default: 1 hour)
            
        Returns:
            Gemini response text
            
        Raises:
            GeminiServiceError: If API call fails
        """
        # Check cache first
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            # Select model
            model = self.pro_model if use_pro else self.flash_model
            
            # Generate response
            response = model.generate_content(prompt)
            result = response.text
            
            # Cache the response
            if cache_key:
                self.cache.set(cache_key, result, ttl=cache_ttl)
            
            return result
            
        except Exception as e:
            raise GeminiServiceError(f"Gemini API call failed: {str(e)}")
    
    def extract_scholarship_from_pdf(self, pdf_text: str, filename: str) -> Dict[str, Any]:
        """
        Extract structured scholarship data from PDF text using Gemini.
        
        Args:
            pdf_text: Extracted text from PDF
            filename: Original PDF filename
            
        Returns:
            Dictionary containing extracted scholarship data
        """
        cache_key = f"gemini:pdf:{hash(pdf_text)}"
        
        prompt = f"""
Extract scholarship information from this PDF text and return ONLY valid JSON (no markdown, no code blocks).

PDF Filename: {filename}
PDF Text:
{pdf_text[:8000]}  # Limit to first 8000 chars to avoid token limits

Return JSON with this exact structure:
{{
  "name": "scholarship name",
  "description": "brief description (2-3 sentences)",
  "provider": "organization providing the scholarship",
  "eligibility": {{
    "age_min": null or number,
    "age_max": null or number,
    "income_max": null or number,
    "education_level": "string or null",
    "location": "string or null",
    "category": "string or null (General/SC/ST/OBC/EWS/Minority/PWD)",
    "gender": "string or null (Any/Male/Female/Other)"
  }},
  "documents_required": ["list", "of", "documents"],
  "deadline": "YYYY-MM-DD or null",
  "benefit_amount": "string describing benefit",
  "application_url": "URL or null",
  "application_process": "brief description of how to apply",
  "confidence_score": 0.0 to 1.0
}}

If information is not found, use null. Be accurate and extract only what's clearly stated.
"""
        
        try:
            response = self._call_gemini(
                prompt,
                use_pro=False,  # Flash is good enough for extraction
                cache_key=cache_key,
                cache_ttl=604800  # Cache for 7 days
            )
            
            # Parse JSON response
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            data["extracted_at"] = datetime.utcnow().isoformat()
            data["extraction_method"] = "gemini-1.5-flash"
            
            return data
            
        except json.JSONDecodeError as e:
            raise GeminiServiceError(f"Failed to parse Gemini response as JSON: {str(e)}")
        except Exception as e:
            raise GeminiServiceError(f"PDF extraction failed: {str(e)}")
    
    def match_eligibility(
        self,
        user_profile: Dict[str, Any],
        scheme_eligibility: Dict[str, Any],
        scheme_name: str
    ) -> Dict[str, Any]:
        """
        Match user profile against scholarship eligibility using Gemini.
        
        Args:
            user_profile: User's profile data
            scheme_eligibility: Scholarship eligibility criteria
            scheme_name: Name of the scholarship
            
        Returns:
            Dictionary with match score, eligibility status, and explanations
        """
        cache_key = f"gemini:match:{hash(json.dumps(user_profile))}:{hash(json.dumps(scheme_eligibility))}"
        
        prompt = f"""
Analyze if this user is eligible for the scholarship and return ONLY valid JSON (no markdown, no code blocks).

User Profile:
{json.dumps(user_profile, indent=2)}

Scholarship: {scheme_name}
Eligibility Criteria:
{json.dumps(scheme_eligibility, indent=2)}

Return JSON with this exact structure:
{{
  "match_score": 0-100 (integer),
  "is_eligible": true or false,
  "matched_criteria": ["list", "of", "criteria", "user", "meets"],
  "missing_criteria": ["list", "of", "criteria", "user", "doesn't", "meet"],
  "explanation": "natural language explanation (2-3 sentences)",
  "suggestions": ["list", "of", "suggestions", "to", "improve", "eligibility"],
  "confidence": 0.0 to 1.0
}}

Be strict but fair in your analysis. Consider all criteria carefully.
"""
        
        try:
            response = self._call_gemini(
                prompt,
                use_pro=True,  # Use Pro for better reasoning
                cache_key=cache_key,
                cache_ttl=3600  # Cache for 1 hour
            )
            
            # Parse JSON response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            data["analyzed_at"] = datetime.utcnow().isoformat()
            
            return data
            
        except json.JSONDecodeError as e:
            raise GeminiServiceError(f"Failed to parse Gemini response as JSON: {str(e)}")
        except Exception as e:
            raise GeminiServiceError(f"Eligibility matching failed: {str(e)}")
    
    def generate_recommendations(
        self,
        user_profile: Dict[str, Any],
        scholarships: List[Dict[str, Any]],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized scholarship recommendations using Gemini.
        
        Args:
            user_profile: User's profile data
            scholarships: List of available scholarships
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended scholarships with reasons
        """
        cache_key = f"gemini:recommend:{hash(json.dumps(user_profile))}:{len(scholarships)}"
        
        # Simplify scholarships for prompt (reduce token usage)
        simplified_scholarships = [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "description": s.get("description", "")[:200],
                "eligibility": s.get("eligibility", {}),
                "benefit_amount": s.get("benefit_amount")
            }
            for s in scholarships[:50]  # Limit to 50 scholarships
        ]
        
        prompt = f"""
Recommend the top {limit} scholarships for this user and return ONLY valid JSON (no markdown, no code blocks).

User Profile:
{json.dumps(user_profile, indent=2)}

Available Scholarships:
{json.dumps(simplified_scholarships, indent=2)}

Return JSON with this exact structure:
{{
  "recommendations": [
    {{
      "scholarship_id": "id",
      "rank": 1,
      "match_score": 0-100,
      "reason": "why this scholarship is recommended (1-2 sentences)"
    }}
  ]
}}

Rank by relevance to user profile, eligibility, benefit amount, and deadlines.
"""
        
        try:
            response = self._call_gemini(
                prompt,
                use_pro=True,  # Use Pro for better ranking
                cache_key=cache_key,
                cache_ttl=3600  # Cache for 1 hour
            )
            
            # Parse JSON response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            return data.get("recommendations", [])
            
        except json.JSONDecodeError as e:
            raise GeminiServiceError(f"Failed to parse Gemini response as JSON: {str(e)}")
        except Exception as e:
            raise GeminiServiceError(f"Recommendation generation failed: {str(e)}")
    
    def semantic_search(
        self,
        query: str,
        user_profile: Dict[str, Any],
        scholarships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform semantic search on scholarships using Gemini.
        
        Args:
            query: User's search query
            user_profile: User's profile data
            scholarships: List of available scholarships
            
        Returns:
            Dictionary with ranked results and query understanding
        """
        cache_key = f"gemini:search:{hash(query)}:{hash(json.dumps(user_profile))}"
        
        # Simplify scholarships for prompt
        simplified_scholarships = [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "description": s.get("description", "")[:200],
                "eligibility": s.get("eligibility", {})
            }
            for s in scholarships[:50]
        ]
        
        prompt = f"""
Search for scholarships matching this query and return ONLY valid JSON (no markdown, no code blocks).

User Query: "{query}"
User Profile:
{json.dumps(user_profile, indent=2)}

Available Scholarships:
{json.dumps(simplified_scholarships, indent=2)}

Return JSON with this exact structure:
{{
  "results": [
    {{
      "scholarship_id": "id",
      "relevance_score": 0-100,
      "match_reason": "why this matches the query"
    }}
  ],
  "query_understanding": "what you understood from the query",
  "suggested_filters": {{"key": "value"}}
}}

Rank by relevance to query and user profile.
"""
        
        try:
            response = self._call_gemini(
                prompt,
                use_pro=False,  # Flash is good enough for search
                cache_key=cache_key,
                cache_ttl=1800  # Cache for 30 minutes
            )
            
            # Parse JSON response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            return data
            
        except json.JSONDecodeError as e:
            raise GeminiServiceError(f"Failed to parse Gemini response as JSON: {str(e)}")
        except Exception as e:
            raise GeminiServiceError(f"Semantic search failed: {str(e)}")
    
    def extract_from_web_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extract scholarship data from web page HTML using Gemini.
        
        Args:
            html_content: HTML content of the web page
            url: URL of the web page
            
        Returns:
            Dictionary containing extracted scholarship data
        """
        cache_key = f"gemini:web:{hash(html_content)}"
        
        # Limit HTML content to avoid token limits
        html_content = html_content[:10000]
        
        prompt = f"""
Extract scholarship information from this web page and return ONLY valid JSON (no markdown, no code blocks).

URL: {url}
HTML Content:
{html_content}

Return JSON with this exact structure:
{{
  "name": "scholarship name",
  "description": "brief description",
  "provider": "organization",
  "eligibility": {{
    "age_min": null or number,
    "age_max": null or number,
    "income_max": null or number,
    "education_level": "string or null",
    "location": "string or null",
    "category": "string or null",
    "gender": "string or null"
  }},
  "documents_required": ["list"],
  "deadline": "YYYY-MM-DD or null",
  "benefit_amount": "string",
  "application_url": "URL or null",
  "confidence_score": 0.0 to 1.0
}}

Extract only what's clearly stated. Use null for missing information.
"""
        
        try:
            response = self._call_gemini(
                prompt,
                use_pro=False,
                cache_key=cache_key,
                cache_ttl=86400  # Cache for 1 day
            )
            
            # Parse JSON response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            data["extracted_at"] = datetime.utcnow().isoformat()
            data["source_url"] = url
            
            return data
            
        except json.JSONDecodeError as e:
            raise GeminiServiceError(f"Failed to parse Gemini response as JSON: {str(e)}")
        except Exception as e:
            raise GeminiServiceError(f"Web content extraction failed: {str(e)}")
