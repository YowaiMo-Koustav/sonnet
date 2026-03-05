# Implementation Plan: Sonnet - Smart Scheme & Job Informer

## Overview

This implementation plan breaks down the scholarship discovery system into incremental coding tasks. The system will be built using Python with FastAPI for the backend, PostgreSQL for the database, and a focus on property-based testing using Hypothesis. Each task builds on previous work, with testing integrated throughout to catch errors early.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - Create Python project with virtual environment
  - Set up FastAPI application with basic configuration
  - Configure PostgreSQL database connection
  - Create database migration system (Alembic)
  - Set up testing framework (pytest) and Hypothesis for property-based testing
  - Create project directory structure (models, services, api, tests)
  - _Requirements: All (foundational)_

- [x] 2. Implement location hierarchy data model and service
  - [x] 2.1 Create Location model and database schema
    - Define Location SQLAlchemy model with id, name, type, parent_id, materialized_path, metadata
    - Create database migration for locations table with indexes
    - Implement LocationType enum (COUNTRY, STATE, DISTRICT)
    - _Requirements: 1.1_
  
  - [x] 2.2 Write property test for hierarchical structure integrity
    - **Property 1: Hierarchical Structure Integrity**
    - **Validates: Requirements 1.1**
  
  - [x] 2.3 Implement LocationService with hierarchy operations
    - Write getChildren(location_id) method
    - Write getAncestors(location_id) method using materialized path
    - Write getSchemes(location_id) method (stub for now)
    - Write searchLocations(query) method with fuzzy matching
    - _Requirements: 1.2, 1.3, 1.4, 1.5_
  
  - [x] 2.4 Write property test for parent-child relationship consistency
    - **Property 2: Parent-Child Relationship Consistency**
    - **Validates: Requirements 1.2, 1.3, 1.5**

- [x] 3. Implement scheme data model and basic management
  - [x] 3.1 Create Scheme model and database schema
    - Define Scheme SQLAlchemy model with all fields from design
    - Create EligibilityCriteria and Document embedded models (JSONB)
    - Create database migration for schemes table with indexes
    - Implement SchemeType, SchemeStatus, EducationLevel, Gender enums
    - _Requirements: 3.1, 3.2, 4.1, 4.2_
  
  - [x] 3.2 Implement SchemeService CRUD operations
    - Write createScheme(scheme) method
    - Write updateScheme(id, updates) method
    - Write getScheme(id) method
    - Write listSchemes(filters) method
    - Write deleteScheme(id) method (soft delete)
    - _Requirements: 1.4, 6.2, 6.4_
  
  - [x] 3.3 Write property test for location-scheme association
    - **Property 3: Location-Scheme Association**
    - **Validates: Requirements 1.4**
  
  - [x] 3.4 Write property test for scheme field population
    - **Property 8: Scheme Field Population**
    - **Validates: Requirements 3.1, 4.1**

- [x] 4. Checkpoint - Ensure core data models work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement PDF processing pipeline
  - [x] 5.1 Create PDF document model and storage
    - Define PDFDocument SQLAlchemy model
    - Create database migration for pdf_documents table
    - Implement file storage service for saving uploaded PDFs
    - _Requirements: 2.1, 2.4_
  
  - [x] 5.2 Implement PDF text extraction
    - Create PDFProcessor class with ingestPDF method
    - Implement text extraction using PyPDF2 or pdfplumber
    - Extract text while preserving reading order
    - Store extracted text in processing results
    - _Requirements: 2.1, 2.2, 2.5_
  
  - [x] 5.3 Write property test for PDF upload acceptance
    - **Property 4: PDF Upload Acceptance**
    - **Validates: Requirements 2.1, 2.2**
  
  - [x] 5.4 Write property test for PDF upload error handling
    - **Property 5: PDF Upload Error Handling**
    - **Validates: Requirements 2.3**
  
  - [x] 5.5 Write property test for PDF storage round-trip
    - **Property 6: PDF Storage Round-Trip**
    - **Validates: Requirements 2.4**
  
  - [x] 5.6 Implement field parsing and extraction
    - Create FieldParser class for extracting structured data
    - Implement pattern matching for eligibility criteria (age, income, education)
    - Implement pattern matching for required documents
    - Implement deadline extraction with date parsing
    - Assign confidence scores to extracted fields
    - _Requirements: 3.1, 3.2, 4.1, 4.2, 8.1_
  
  - [x] 5.7 Write property test for low-confidence field flagging
    - **Property 9: Low-Confidence Field Flagging**
    - **Validates: Requirements 3.5, 4.5**
  
  - [x] 5.8 Write unit tests for field extraction edge cases
    - Test extraction with missing eligibility criteria
    - Test extraction with missing required documents
    - Test extraction with ambiguous deadline formats
    - _Requirements: 3.4, 4.4_

- [x] 6. Implement user profile and eligibility matching
  - [x] 6.1 Create User and UserProfile models
    - Define User SQLAlchemy model
    - Create UserProfile embedded model (JSONB) with age, gender, education, income, location
    - Create database migration for users table
    - _Requirements: 9.1_
  
  - [x] 6.2 Write property test for profile creation completeness
    - **Property 22: Profile Creation Completeness**
    - **Validates: Requirements 9.1**
  
  - [x] 6.3 Implement EligibilityMatchingEngine
    - Create MatchResult class with match_percentage, is_eligible, failed_criteria
    - Implement computeMatchScore(profile, criteria) method following design algorithm
    - Implement matchUser(user_id, scheme_id) method
    - Implement findMatchingSchemes(user_id, filters) method with ranking
    - Implement explainMatch(user_id, scheme_id) method
    - _Requirements: 9.2, 9.3, 9.4_
  
  - [x] 6.4 Write property test for eligibility match computation
    - **Property 23: Eligibility Match Computation**
    - **Validates: Requirements 9.2, 9.3**
  
  - [x] 6.5 Write property test for eligible scheme prioritization
    - **Property 24: Eligible Scheme Prioritization**
    - **Validates: Requirements 9.4**
  
  - [x] 6.6 Write property test for profile update persistence
    - **Property 25: Profile Update Persistence**
    - **Validates: Requirements 9.5**

- [x] 7. Implement application tracking system
  - [x] 7.1 Create Application model and database schema
    - Define Application SQLAlchemy model with status and status_history
    - Create ApplicationStatus enum
    - Create StatusChange embedded model
    - Create database migration for applications table with unique constraint on (user_id, scheme_id)
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 7.2 Implement ApplicationTrackerService
    - Write createApplication(user_id, scheme_id) method
    - Write updateStatus(application_id, new_status, notes) method
    - Write getUserApplications(user_id) method
    - Write getApplicationsByStatus(user_id, status) method
    - Write getApplicationHistory(application_id) method
    - _Requirements: 5.1, 5.2, 5.3, 5.5_
  
  - [x] 7.3 Write property test for application creation
    - **Property 10: Application Creation**
    - **Validates: Requirements 5.1**
  
  - [x] 7.4 Write property test for application status transitions
    - **Property 11: Application Status Transitions**
    - **Validates: Requirements 5.2**
  
  - [x] 7.5 Write property test for status history recording
    - **Property 12: Status History Recording**
    - **Validates: Requirements 5.3**
  
  - [x] 7.6 Write property test for application data completeness
    - **Property 13: Application Data Completeness**
    - **Validates: Requirements 5.5**

- [x] 8. Checkpoint - Ensure business logic works correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement search and filter functionality
  - [x] 9.1 Create SearchService with filtering
    - Implement SchemeFilters class for filter parameters
    - Write filter(filters) method with multi-criteria filtering
    - Implement location filtering using location hierarchy
    - Implement deadline range filtering
    - Implement scheme type and education level filtering
    - _Requirements: 6.3, 6.4_
  
  - [x] 9.2 Write property test for multi-filter conjunction
    - **Property 15: Multi-Filter Conjunction**
    - **Validates: Requirements 6.4**
  
  - [x] 9.3 Implement full-text search
    - Add PostgreSQL full-text search index on scheme name and description
    - Write search(query, filters) method using full-text search
    - Implement fuzzy matching for typo tolerance
    - Rank results by relevance score
    - _Requirements: 6.1, 6.2_
  
  - [x] 9.4 Write property test for search result matching
    - **Property 14: Search Result Matching**
    - **Validates: Requirements 6.2**
  
  - [x] 9.5 Write property test for search result completeness
    - **Property 16: Search Result Completeness**
    - **Validates: Requirements 6.5**
  
  - [x] 9.6 Implement autocomplete suggestions
    - Write getSuggestions(partial) method
    - Use trigram similarity for fuzzy matching
    - _Requirements: 6.1_

- [x] 10. Implement deadline management features
  - [x] 10.1 Add deadline-related business logic
    - Implement method to check if deadline is approaching (within 7 days)
    - Implement method to mark expired schemes as CLOSED
    - Add deadline sorting to SchemeService.listSchemes
    - _Requirements: 8.3, 8.4, 8.5_
  
  - [x] 10.2 Write property test for deadline extraction
    - **Property 18: Deadline Extraction**
    - **Validates: Requirements 8.1**
  
  - [x] 10.3 Write property test for approaching deadline detection
    - **Property 19: Approaching Deadline Detection**
    - **Validates: Requirements 8.3**
  
  - [x] 10.4 Write property test for deadline sorting
    - **Property 20: Deadline Sorting**
    - **Validates: Requirements 8.4**
  
  - [x] 10.5 Write property test for expired scheme status
    - **Property 21: Expired Scheme Status**
    - **Validates: Requirements 8.5**
  
  - [x] 10.6 Create background job for deadline processing
    - Set up Celery or APScheduler for scheduled tasks
    - Create daily job to mark expired schemes as CLOSED
    - _Requirements: 8.5_

- [x] 11. Implement administrator features and audit logging
  - [x] 11.1 Create audit log model and service
    - Define AuditLog SQLAlchemy model with admin_id, scheme_id, field_name, old_value, new_value, timestamp
    - Create database migration for audit_logs table
    - _Requirements: 10.5_
  
  - [x] 11.2 Add admin review and edit functionality
    - Extend SchemeService.updateScheme to record audit logs
    - Add method to flag low-confidence fields for review
    - Add method to get schemes requiring review
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [x] 11.3 Write property test for admin edit persistence
    - **Property 26: Admin Edit Persistence**
    - **Validates: Requirements 10.3, 10.4**
  
  - [x] 11.4 Write property test for audit log recording
    - **Property 27: Audit Log Recording**
    - **Validates: Requirements 10.5**

- [x] 12. Implement REST API endpoints
  - [x] 12.1 Create location API endpoints
    - POST /api/locations (create location)
    - GET /api/locations/{id} (get location details)
    - GET /api/locations/{id}/children (get child locations)
    - GET /api/locations/{id}/ancestors (get ancestor path)
    - GET /api/locations/{id}/schemes (get schemes for location)
    - GET /api/locations/search?q={query} (search locations)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 12.2 Create scheme API endpoints
    - POST /api/schemes (create scheme)
    - GET /api/schemes/{id} (get scheme details)
    - PUT /api/schemes/{id} (update scheme)
    - DELETE /api/schemes/{id} (delete scheme)
    - GET /api/schemes (list/filter schemes)
    - GET /api/schemes/search?q={query} (search schemes)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 12.3 Create PDF processing API endpoints
    - POST /api/pdf/upload (upload and process PDF)
    - GET /api/pdf/{id}/status (get processing status)
    - GET /api/pdf/{id}/results (get extraction results)
    - GET /api/pdf/{id}/download (download original PDF)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 12.4 Create user profile API endpoints
    - POST /api/users (create user)
    - GET /api/users/{id} (get user profile)
    - PUT /api/users/{id}/profile (update profile)
    - GET /api/users/{id}/matching-schemes (get eligible schemes)
    - GET /api/users/{id}/match/{scheme_id} (get match explanation)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [x] 12.5 Create application tracking API endpoints
    - POST /api/applications (create application)
    - GET /api/applications/{id} (get application details)
    - PUT /api/applications/{id}/status (update status)
    - GET /api/users/{id}/applications (get user applications)
    - GET /api/applications/{id}/history (get status history)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 12.6 Create admin API endpoints
    - GET /api/admin/schemes/review (get schemes needing review)
    - PUT /api/admin/schemes/{id} (admin edit with audit logging)
    - GET /api/admin/audit-logs (get audit log entries)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [x] 12.7 Write integration tests for API endpoints
    - Test authentication and authorization
    - Test request validation and error responses
    - Test successful request flows
    - _Requirements: All_

- [x] 13. Implement caching and offline support
  - [x] 13.1 Set up Redis caching layer
    - Configure Redis connection
    - Implement cache decorator for frequently accessed data
    - Cache location hierarchies (rarely change)
    - Cache popular schemes with TTL
    - _Requirements: 7.1, 7.3, 7.4_
  
  - [x] 13.2 Implement offline data access
    - Add cache-first strategy for scheme retrieval
    - Store accessed schemes in browser local storage (frontend task, but prepare API)
    - Add API endpoint to return cached scheme IDs for a user
    - _Requirements: 7.3, 7.4_
  
  - [x] 13.3 Write property test for offline data access
    - **Property 17: Offline Data Access**
    - **Validates: Requirements 7.3, 7.4**

- [-] 14. Implement accessibility and performance optimizations
  - [x] 14.1 Add database query optimizations
    - Review and optimize all database queries
    - Add missing indexes based on query patterns
    - Implement pagination for list endpoints (limit to 20-50 items)
    - Use eager loading to avoid N+1 queries
    - _Requirements: 7.1_
  
  - [x] 14.2 Add API response optimizations
    - Implement response compression (gzip)
    - Add ETag support for caching
    - Minimize response payload sizes
    - Add API rate limiting
    - _Requirements: 7.1_
  
  - [-] 14.3 Add simplified API mode
    - Create /api/lite/* endpoints with minimal data
    - Remove unnecessary fields from responses
    - Optimize for low-bandwidth connections
    - _Requirements: 7.2_

- [ ] 15. Implement error handling and validation
  - [ ] 15.1 Add comprehensive input validation
    - Validate all API request bodies using Pydantic models
    - Add field-level validation with descriptive error messages
    - Validate foreign key references before operations
    - _Requirements: All_
  
  - [x] 15.2 Implement error handling middleware
    - Create global exception handler for FastAPI
    - Return consistent error response format
    - Log all errors with request context
    - Implement retry logic for transient failures
    - _Requirements: All_
  
  - [ ] 15.3 Write unit tests for error conditions
    - Test invalid input handling
    - Test missing required fields
    - Test constraint violations
    - Test system error scenarios
    - _Requirements: 2.3, 3.4, 3.5, 4.4, 4.5_

- [x] 16. Final checkpoint - Integration and end-to-end validation
  - Ensure all tests pass (unit, property, and integration tests)
  - Verify all API endpoints work correctly
  - Test complete user flows (browse → search → apply → track)
  - Test admin flows (upload PDF → review → edit → approve)
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- Integration tests validate API endpoints and complete flows
- The implementation uses Python with FastAPI, PostgreSQL, and Hypothesis for property-based testing
- Background jobs for deadline processing can use Celery or APScheduler
- Caching uses Redis for performance optimization
- All API endpoints should include proper authentication and authorization (implementation details TBD based on requirements)
