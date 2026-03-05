# Requirements Document: Sonnet - Smart Scheme & Job Informer

## Introduction

Sonnet is a scholarship and job discovery system designed to help students in rural districts find and apply for relevant opportunities. The system uses a hierarchical, location-first organization to make discovery intuitive, ingests PDF documents to extract eligibility criteria and required documents, and tracks application progress to help students manage their applications effectively.

## Glossary

- **System**: The Sonnet scholarship and job informer application
- **User**: A student searching for scholarships or jobs
- **Scheme**: A scholarship, grant, or job opportunity available to students
- **Location_Hierarchy**: The organizational structure of Country → State → District → Schemes
- **PDF_Processor**: The component that ingests and extracts information from PDF documents
- **Eligibility_Criteria**: The requirements a student must meet to qualify for a scheme
- **Required_Documents**: The documents a student must submit for a scheme application
- **Application_Tracker**: The component that monitors and displays application progress
- **Administrator**: A user who manages scheme data and system configuration

## Requirements

### Requirement 1: Hierarchical Location-Based Organization

**User Story:** As a student, I want to browse schemes organized by location hierarchy, so that I can quickly find opportunities relevant to my geographic area.

#### Acceptance Criteria

1. THE System SHALL organize schemes in a hierarchical structure: Country → State → District → Schemes
2. WHEN a user selects a country, THE System SHALL display all available states within that country
3. WHEN a user selects a state, THE System SHALL display all available districts within that state
4. WHEN a user selects a district, THE System SHALL display all schemes available in that district
5. THE System SHALL allow users to navigate back up the hierarchy to explore different locations

### Requirement 2: PDF Document Ingestion

**User Story:** As an administrator, I want to upload PDF documents containing scheme information, so that the system can automatically extract and organize scheme details.

#### Acceptance Criteria

1. WHEN an administrator uploads a PDF document, THE PDF_Processor SHALL accept the file and begin processing
2. THE PDF_Processor SHALL support common PDF formats and encodings
3. WHEN a PDF upload fails, THE System SHALL provide a descriptive error message to the administrator
4. THE System SHALL store the original PDF document for reference
5. WHEN processing a PDF, THE System SHALL extract text content while preserving document structure

### Requirement 3: Eligibility Criteria Extraction

**User Story:** As a student, I want to see clear eligibility criteria for each scheme, so that I can determine if I qualify before applying.

#### Acceptance Criteria

1. WHEN the PDF_Processor processes a scheme document, THE System SHALL extract eligibility criteria information
2. THE System SHALL identify and extract criteria including age limits, income requirements, educational qualifications, and geographic restrictions
3. WHEN eligibility criteria are displayed, THE System SHALL present them in a structured, readable format
4. THE System SHALL handle cases where eligibility criteria are not clearly specified in the source document
5. WHEN eligibility information is ambiguous, THE System SHALL flag it for administrator review

### Requirement 4: Required Documents Extraction

**User Story:** As a student, I want to see a list of required documents for each scheme, so that I can prepare my application materials in advance.

#### Acceptance Criteria

1. WHEN the PDF_Processor processes a scheme document, THE System SHALL extract required documents information
2. THE System SHALL identify document types such as identity proof, income certificates, educational certificates, and photographs
3. WHEN required documents are displayed, THE System SHALL present them as a checklist
4. THE System SHALL handle cases where required documents are not clearly specified in the source document
5. WHEN document requirements are ambiguous, THE System SHALL flag them for administrator review

### Requirement 5: Application Progress Tracking

**User Story:** As a student, I want to track the progress of my applications, so that I can stay organized and follow up when necessary.

#### Acceptance Criteria

1. WHEN a user marks a scheme as "applied", THE Application_Tracker SHALL create a new application record
2. THE Application_Tracker SHALL support multiple status states including "interested", "in progress", "submitted", "under review", "accepted", and "rejected"
3. WHEN a user updates an application status, THE System SHALL record the timestamp of the change
4. THE System SHALL display all tracked applications in a centralized dashboard
5. WHEN viewing an application, THE System SHALL show the current status, submission date, and scheme details

### Requirement 6: Search and Filter Functionality

**User Story:** As a student, I want to search and filter schemes by various criteria, so that I can quickly find opportunities that match my profile.

#### Acceptance Criteria

1. THE System SHALL provide a search interface that accepts text queries
2. WHEN a user enters a search query, THE System SHALL return schemes matching the query in name, description, or eligibility criteria
3. THE System SHALL provide filters for location, eligibility criteria, deadline dates, and scheme type
4. WHEN multiple filters are applied, THE System SHALL return schemes matching all selected criteria
5. THE System SHALL display search results with relevant scheme information including name, location, and deadline

### Requirement 7: Accessibility for Rural Users

**User Story:** As a student in a rural area with limited internet connectivity, I want the system to work efficiently on low-bandwidth connections, so that I can access scheme information reliably.

#### Acceptance Criteria

1. THE System SHALL optimize page load times to function on low-bandwidth connections
2. THE System SHALL provide a simplified interface option with minimal graphics
3. WHEN network connectivity is poor, THE System SHALL display cached scheme information when available
4. THE System SHALL support offline viewing of previously accessed scheme details
5. THE System SHALL use responsive design to function on mobile devices with small screens

### Requirement 8: Scheme Deadline Management

**User Story:** As a student, I want to see application deadlines clearly displayed, so that I don't miss opportunities.

#### Acceptance Criteria

1. WHEN the PDF_Processor processes a scheme document, THE System SHALL extract deadline information
2. THE System SHALL display deadlines prominently on scheme detail pages
3. WHEN a scheme deadline is approaching (within 7 days), THE System SHALL highlight it with a visual indicator
4. THE System SHALL sort schemes by deadline when requested by the user
5. WHEN a scheme deadline has passed, THE System SHALL mark the scheme as closed

### Requirement 9: User Profile and Eligibility Matching

**User Story:** As a student, I want to create a profile with my details, so that the system can recommend schemes I'm eligible for.

#### Acceptance Criteria

1. THE System SHALL allow users to create a profile with personal information including age, location, education level, and family income
2. WHEN a user profile is complete, THE System SHALL compare profile data against scheme eligibility criteria
3. THE System SHALL display a compatibility indicator for each scheme showing how well the user matches eligibility requirements
4. WHEN viewing schemes, THE System SHALL prioritize displaying schemes the user is eligible for
5. THE System SHALL allow users to update their profile information at any time

### Requirement 10: Data Validation and Quality

**User Story:** As an administrator, I want to review and correct extracted scheme information, so that students receive accurate details.

#### Acceptance Criteria

1. THE System SHALL provide an administrator interface for reviewing extracted scheme data
2. WHEN extraction confidence is low, THE System SHALL flag fields for manual review
3. THE System SHALL allow administrators to edit any extracted field including eligibility criteria, required documents, and deadlines
4. WHEN an administrator makes corrections, THE System SHALL update the scheme information immediately
5. THE System SHALL maintain an audit log of all administrator changes to scheme data
