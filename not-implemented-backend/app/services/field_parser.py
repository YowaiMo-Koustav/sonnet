"""
Field Parser Service for extracting structured data from PDF text.

This service uses pattern matching and keyword detection to extract:
- Eligibility criteria (age, income, education, geographic restrictions)
- Required documents (identity proof, certificates, etc.)
- Deadlines with date parsing
- Scheme name and description

Each extracted field includes a confidence score based on pattern match strength,
section header presence, data format validity, and text ambiguity.
"""
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted fields."""
    HIGH = "HIGH"      # > 0.8
    MEDIUM = "MEDIUM"  # 0.5 - 0.8
    LOW = "LOW"        # < 0.5


@dataclass
class ExtractedField:
    """Represents an extracted field with confidence scoring."""
    field_name: str
    value: Any
    confidence: float
    source_location: Optional[str] = None  # Text snippet where found
    requires_review: bool = False
    
    def __post_init__(self):
        """Set requires_review flag based on confidence."""
        self.requires_review = self.confidence < 0.5


class FieldParser:
    """Service for extracting structured data from PDF text content."""
    
    # Section header patterns
    SECTION_PATTERNS = {
        'eligibility': r'(?i)(eligibility|eligible|qualification|who can apply|criteria)',
        'documents': r'(?i)(required documents|documents required|documents needed|necessary documents|documents to be submitted)',
        'deadline': r'(?i)(deadline|last date|closing date|apply by|application deadline)',
        'how_to_apply': r'(?i)(how to apply|application process|apply online)',
        'description': r'(?i)(about|description|overview|introduction|scheme details)'
    }
    
    # Eligibility criteria patterns
    AGE_PATTERNS = [
        r'(?i)age\s*(?:limit|range|criteria)?[:\s]+(\d+)\s*(?:to|-)\s*(\d+)',
        r'(?i)between\s+(\d+)\s+(?:and|to)\s+(\d+)\s+years',
        r'(?i)(\d+)\s*(?:to|-)\s*(\d+)\s+years\s+(?:of\s+)?age',
        r'(?i)aged\s+(\d+)\s*(?:to|-)\s*(\d+)',
        r'(?i)minimum\s+age[:\s]+(\d+)',
        r'(?i)maximum\s+age[:\s]+(\d+)',
    ]
    
    INCOME_PATTERNS = [
        r'(?i)(?:annual\s+)?income\s*(?:limit|criteria)?[:\s]+(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lakhs|l)',
        r'(?i)family\s+income\s*(?:below|less\s+than|up\s+to|should\s+not\s+exceed|not\s+exceed)[:\s]+(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lakhs|l)',
        r'(?i)(?:below|less\s+than|up\s+to|not\s+exceed|should\s+not\s+exceed)\s+(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lakhs|l)',
        r'(?i)(?:rs\.?|₹|inr)\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lakhs|l)\s+(?:per\s+)?(?:annum|year)',
        r'(?i)(?:annual\s+)?income\s*(?:limit|criteria)?[:\s]+(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'(?i)(?:rs\.?|₹|inr)\s*(\d+(?:,\d+)*)',  # Simple Rs. with commas
    ]
    
    EDUCATION_PATTERNS = [
        r'(?i)(10th|tenth|class\s+10|secondary)',
        r'(?i)(12th|twelfth|class\s+12|higher\s+secondary|intermediate)',
        r'(?i)(graduation|graduate|bachelor|undergraduate|ug|b\.?a\.?|b\.?sc\.?|b\.?com\.?|b\.?tech\.?|b\.?e\.?)',
        r'(?i)(post\s*graduate|postgraduate|master|pg|m\.?a\.?|m\.?sc\.?|m\.?com\.?|m\.?tech\.?)',
        r'(?i)(phd|ph\.?d\.?|doctorate)',
    ]
    
    # Document type patterns
    DOCUMENT_PATTERNS = {
        'identity_proof': r'(?i)(identity\s+proof|id\s+proof|aadhar|aadhaar|pan\s+card|voter\s+id|passport)',
        'income_certificate': r'(?i)(income\s+certificate|income\s+proof)',
        'caste_certificate': r'(?i)(caste\s+certificate|community\s+certificate|sc/st\s+certificate)',
        'educational_certificate': r'(?i)(educational\s+certificate|mark\s*sheet|degree\s+certificate|transcript)',
        'photograph': r'(?i)(photograph|photo|passport\s+size\s+photo)',
        'domicile': r'(?i)(domicile\s+certificate|residence\s+proof|address\s+proof)',
        'bank_details': r'(?i)(bank\s+details|bank\s+account|passbook)',
    }
    
    # Date patterns for deadline extraction
    DATE_PATTERNS = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)[,\s]+(\d{4})',
        r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(\d{4})',
    ]
    
    MONTH_MAP = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    def parse_text(self, text: str) -> Dict[str, ExtractedField]:
        """
        Parse text and extract all structured fields.
        
        Args:
            text: Extracted text from PDF document
            
        Returns:
            Dictionary mapping field names to ExtractedField objects
        """
        if not text or not text.strip():
            return {}
        
        results = {}
        
        # Extract eligibility criteria
        eligibility = self.extract_eligibility_criteria(text)
        for field_name, value in eligibility.items():
            results[field_name] = value
        
        # Extract required documents
        documents = self.extract_required_documents(text)
        if documents:
            results['required_documents'] = documents
        
        # Extract deadline
        deadline_field = self.extract_deadline(text)
        if deadline_field:
            results['deadline'] = deadline_field
        
        # Extract scheme name (first significant line or from title section)
        name_field = self._extract_scheme_name(text)
        if name_field:
            results['scheme_name'] = name_field
        
        # Extract description
        description_field = self._extract_description(text)
        if description_field:
            results['description'] = description_field
        
        return results
    
    def extract_eligibility_criteria(self, text: str) -> Dict[str, ExtractedField]:
        """
        Extract eligibility criteria from text.
        
        Extracts:
        - Age limits (min/max)
        - Income requirements
        - Educational qualifications
        - Geographic restrictions
        
        Args:
            text: Text content to parse
            
        Returns:
            Dictionary of extracted eligibility fields
        """
        results = {}
        
        # Find eligibility section
        eligibility_section = self._find_section(text, 'eligibility')
        has_section_header = eligibility_section is not None
        search_text = eligibility_section if eligibility_section else text
        
        # Extract age criteria
        age_data = self._extract_age(search_text)
        if age_data:
            age_min, age_max, confidence, source = age_data
            # Boost confidence if found in eligibility section
            if has_section_header:
                confidence = min(1.0, confidence + 0.15)
            
            if age_min is not None:
                results['age_min'] = ExtractedField(
                    field_name='age_min',
                    value=age_min,
                    confidence=confidence,
                    source_location=source
                )
            if age_max is not None:
                results['age_max'] = ExtractedField(
                    field_name='age_max',
                    value=age_max,
                    confidence=confidence,
                    source_location=source
                )
        
        # Extract income criteria
        income_data = self._extract_income(search_text)
        if income_data:
            income_max, confidence, source = income_data
            if has_section_header:
                confidence = min(1.0, confidence + 0.15)
            
            results['income_max'] = ExtractedField(
                field_name='income_max',
                value=income_max,
                confidence=confidence,
                source_location=source
            )
        
        # Extract education level
        education_data = self._extract_education(search_text)
        if education_data:
            education_levels, confidence, source = education_data
            if has_section_header:
                confidence = min(1.0, confidence + 0.15)
            
            results['education_level'] = ExtractedField(
                field_name='education_level',
                value=education_levels,
                confidence=confidence,
                source_location=source
            )
        
        return results
    
    def extract_required_documents(self, text: str) -> Optional[ExtractedField]:
        """
        Extract required documents from text.
        
        Args:
            text: Text content to parse
            
        Returns:
            ExtractedField containing list of required documents
        """
        # Find documents section
        documents_section = self._find_section(text, 'documents')
        has_section_header = documents_section is not None
        search_text = documents_section if documents_section else text
        
        found_documents = []
        sources = []
        
        # Search for each document type
        for doc_type, pattern in self.DOCUMENT_PATTERNS.items():
            matches = re.finditer(pattern, search_text)
            for match in matches:
                # Extract context around the match
                start = max(0, match.start() - 20)
                end = min(len(search_text), match.end() + 20)
                context = search_text[start:end].strip()
                
                found_documents.append({
                    'name': doc_type.replace('_', ' ').title(),
                    'description': match.group(0),
                    'is_mandatory': True  # Assume mandatory unless stated otherwise
                })
                sources.append(context)
        
        if not found_documents:
            return None
        
        # Calculate confidence based on section header and number of documents found
        confidence = 0.6  # Base confidence
        if has_section_header:
            confidence += 0.25
        if len(found_documents) >= 3:
            confidence += 0.1
        
        confidence = min(1.0, confidence)
        
        return ExtractedField(
            field_name='required_documents',
            value=found_documents,
            confidence=confidence,
            source_location='; '.join(sources[:3])  # First 3 sources
        )
    
    def extract_deadline(self, text: str) -> Optional[ExtractedField]:
        """
        Extract application deadline from text.
        
        Args:
            text: Text content to parse
            
        Returns:
            ExtractedField containing deadline date
        """
        # Find deadline section
        deadline_section = self._find_section(text, 'deadline')
        has_section_header = deadline_section is not None
        search_text = deadline_section if deadline_section else text
        
        # Try each date pattern
        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            for match in matches:
                parsed_date = self._parse_date_match(match)
                if parsed_date:
                    # Extract context
                    start = max(0, match.start() - 30)
                    end = min(len(search_text), match.end() + 30)
                    context = search_text[start:end].strip()
                    
                    # Calculate confidence
                    confidence = 0.7  # Base confidence for valid date
                    if has_section_header:
                        confidence += 0.2
                    if re.search(r'(?i)(deadline|last\s+date|closing)', context):
                        confidence += 0.1
                    
                    confidence = min(1.0, confidence)
                    
                    return ExtractedField(
                        field_name='deadline',
                        value=parsed_date,
                        confidence=confidence,
                        source_location=context
                    )
        
        return None
    
    def calculate_confidence(self, field_name: str, value: Any, context: str) -> float:
        """
        Calculate confidence score for an extracted field.
        
        Factors considered:
        - Pattern match strength
        - Presence of clear section headers
        - Data format validity
        - Ambiguity in the text
        
        Args:
            field_name: Name of the field
            value: Extracted value
            context: Text context where value was found
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Check for section headers in context
        for section_type, pattern in self.SECTION_PATTERNS.items():
            if re.search(pattern, context, re.IGNORECASE):
                confidence += 0.2
                break
        
        # Check data format validity
        if field_name in ['age_min', 'age_max']:
            if isinstance(value, int) and 0 < value < 120:
                confidence += 0.2
        elif field_name == 'income_max':
            if isinstance(value, (int, float)) and value > 0:
                confidence += 0.2
        elif field_name == 'deadline':
            if isinstance(value, date):
                confidence += 0.2
        
        # Check for ambiguity indicators
        ambiguity_patterns = [r'(?i)(may|might|could|approximately|around|about)']
        for pattern in ambiguity_patterns:
            if re.search(pattern, context):
                confidence -= 0.15
                break
        
        return min(1.0, max(0.0, confidence))
    
    def _find_section(self, text: str, section_type: str) -> Optional[str]:
        """
        Find a specific section in the text.
        
        Args:
            text: Full text content
            section_type: Type of section to find (eligibility, documents, deadline, etc.)
            
        Returns:
            Section text or None if not found
        """
        if section_type not in self.SECTION_PATTERNS:
            return None
        
        pattern = self.SECTION_PATTERNS[section_type]
        match = re.search(pattern, text, re.IGNORECASE)
        
        if not match:
            return None
        
        # Extract text from match to next section or end
        start = match.start()
        
        # Find next section header
        end = len(text)
        for other_section, other_pattern in self.SECTION_PATTERNS.items():
            if other_section != section_type:
                next_match = re.search(other_pattern, text[start + len(match.group(0)):], re.IGNORECASE)
                if next_match:
                    potential_end = start + len(match.group(0)) + next_match.start()
                    end = min(end, potential_end)
        
        # Limit section size to avoid too much text
        end = min(end, start + 1000)
        
        return text[start:end]
    
    def _extract_age(self, text: str) -> Optional[Tuple[Optional[int], Optional[int], float, str]]:
        """
        Extract age criteria from text.
        
        Returns:
            Tuple of (age_min, age_max, confidence, source_text) or None
        """
        for pattern in self.AGE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Extract context
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end].strip()
                
                # Parse age values
                age_min = None
                age_max = None
                
                if len(groups) == 2:
                    # Range pattern
                    try:
                        age_min = int(groups[0])
                        age_max = int(groups[1])
                    except ValueError:
                        continue
                elif len(groups) == 1:
                    # Single value (min or max)
                    try:
                        value = int(groups[0])
                        if 'minimum' in match.group(0).lower() or 'min' in match.group(0).lower():
                            age_min = value
                        elif 'maximum' in match.group(0).lower() or 'max' in match.group(0).lower():
                            age_max = value
                        else:
                            age_max = value  # Default to max
                    except ValueError:
                        continue
                
                # Validate age values
                if age_min and (age_min < 0 or age_min > 120):
                    continue
                if age_max and (age_max < 0 or age_max > 120):
                    continue
                if age_min and age_max and age_min > age_max:
                    continue
                
                confidence = 0.75  # Good pattern match
                return age_min, age_max, confidence, context
        
        return None
    
    def _extract_income(self, text: str) -> Optional[Tuple[float, float, str]]:
        """
        Extract income criteria from text.
        
        Returns:
            Tuple of (income_max, confidence, source_text) or None
        """
        for pattern in self.INCOME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract context
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end].strip()
                
                # Parse income value
                try:
                    value_str = match.group(1).replace(',', '')
                    income_value = float(value_str)
                    
                    # Check if value is in lakhs - look at the full match text
                    full_match = match.group(0).lower()
                    if 'lakh' in full_match or ' l' in full_match:
                        income_value = income_value * 100000
                    
                    # Validate income value
                    if income_value < 0 or income_value > 100000000:  # Max 10 crore
                        continue
                    
                    confidence = 0.75
                    return income_value, confidence, context
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_education(self, text: str) -> Optional[Tuple[List[str], float, str]]:
        """
        Extract education level criteria from text.
        
        Returns:
            Tuple of (education_levels, confidence, source_text) or None
        """
        education_levels = []
        sources = []
        
        education_map = {
            0: 'SECONDARY',
            1: 'HIGHER_SECONDARY',
            2: 'UNDERGRADUATE',
            3: 'POSTGRADUATE',
            4: 'POSTGRADUATE',  # PhD maps to postgraduate
        }
        
        for idx, pattern in enumerate(self.EDUCATION_PATTERNS):
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                level = education_map.get(idx)
                if level and level not in education_levels:
                    education_levels.append(level)
                    
                    # Extract context
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    sources.append(text[start:end].strip())
        
        if not education_levels:
            return None
        
        confidence = 0.7
        if len(education_levels) == 1:
            confidence = 0.75  # More confident with single clear level
        
        return education_levels, confidence, '; '.join(sources[:2])
    
    def _extract_scheme_name(self, text: str) -> Optional[ExtractedField]:
        """
        Extract scheme name from text (usually first significant line).
        
        Returns:
            ExtractedField containing scheme name or None
        """
        lines = text.split('\n')
        
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            # Skip empty lines and very short lines
            if len(line) < 10 or len(line) > 200:
                continue
            
            # Skip lines that look like headers or metadata
            if re.match(r'(?i)^(page|date|government|ministry|department)', line):
                continue
            
            # This looks like a title
            confidence = 0.6
            if line.isupper() or line.istitle():
                confidence = 0.75
            
            return ExtractedField(
                field_name='scheme_name',
                value=line,
                confidence=confidence,
                source_location=line
            )
        
        return None
    
    def _extract_description(self, text: str) -> Optional[ExtractedField]:
        """
        Extract scheme description from text.
        
        Returns:
            ExtractedField containing description or None
        """
        # Find description section
        description_section = self._find_section(text, 'description')
        
        if description_section:
            # Clean up the description
            lines = description_section.split('\n')
            description_lines = []
            
            for line in lines[1:]:  # Skip header line
                line = line.strip()
                if len(line) > 20:  # Meaningful content
                    description_lines.append(line)
                if len(description_lines) >= 5:  # Limit to 5 lines
                    break
            
            if description_lines:
                description = ' '.join(description_lines)
                return ExtractedField(
                    field_name='description',
                    value=description,
                    confidence=0.7,
                    source_location=description[:100]
                )
        
        # Fallback: use first paragraph after title
        lines = text.split('\n')
        paragraph_lines = []
        started = False
        
        for line in lines:
            line = line.strip()
            if not started and len(line) > 50:
                started = True
            if started and len(line) > 20:
                paragraph_lines.append(line)
            if len(paragraph_lines) >= 3:
                break
        
        if paragraph_lines:
            description = ' '.join(paragraph_lines)
            return ExtractedField(
                field_name='description',
                value=description,
                confidence=0.5,
                source_location=description[:100]
            )
        
        return None
    
    def _parse_date_match(self, match: re.Match) -> Optional[date]:
        """
        Parse a date from a regex match.
        
        Args:
            match: Regex match object containing date components
            
        Returns:
            Parsed date object or None if invalid
        """
        groups = match.groups()
        
        try:
            # Pattern: DD/MM/YYYY or DD-MM-YYYY or YYYY/MM/DD or YYYY-MM-DD
            if len(groups) == 3 and groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                val1 = int(groups[0])
                val2 = int(groups[1])
                val3 = int(groups[2])
                
                # Determine format based on values
                if val1 > 31:  # YYYY/MM/DD format
                    year, month, day = val1, val2, val3
                elif val3 > 31:  # DD/MM/YYYY format
                    day, month, year = val1, val2, val3
                else:
                    # Ambiguous - try both formats
                    # Prefer DD/MM/YYYY for Indian context
                    day, month, year = val1, val2, val3
                
                return date(year=year, month=month, day=day)
            
            # Pattern: DD Month YYYY or DDth Month YYYY
            elif len(groups) == 3 and groups[1].lower() in self.MONTH_MAP:
                day = int(groups[0])
                month = self.MONTH_MAP[groups[1].lower()]
                year = int(groups[2])
                return date(year=year, month=month, day=day)
            
            # Pattern: Month DD YYYY or Month DDth YYYY
            elif len(groups) == 3 and groups[0].lower() in self.MONTH_MAP:
                month = self.MONTH_MAP[groups[0].lower()]
                day = int(groups[1])
                year = int(groups[2])
                return date(year=year, month=month, day=day)
        
        except (ValueError, IndexError):
            return None
        
        return None
