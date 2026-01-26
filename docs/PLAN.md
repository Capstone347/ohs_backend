# OHS Remote Backend Implementation Plan
## Safety Compliance App - Technical Implementation Strategy

---

## 1. Executive Summary

This implementation plan outlines the backend development strategy for OHS Remote, a web-based safety compliance application that generates customized, branded OHS manual packages for small to medium-sized businesses. The backend will be built using FastAPI (Python) with a focus on modular architecture, scalable design, and phased delivery that enables continuous client feedback and iterative refinement.

The development is structured in four distinct phases, with Phase 1 delivering a functional MVP that demonstrates core workflow capabilities, and subsequent phases adding complexity, AI-powered content generation, administrative tools, and production-grade features.

---

## 2. System Architecture Overview

### 2.1 High-Level Architecture

The backend follows a layered architecture pattern:

**Presentation Layer**: RESTful API endpoints exposed via FastAPI
**Business Logic Layer**: Service modules handling domain-specific operations
**Data Access Layer**: Repository pattern for database interactions
**Infrastructure Layer**: External service integrations (email, storage, payment)

### 2.2 Core Architectural Principles

**Separation of Concerns**: Clear boundaries between API routes, business logic, and data access
**Dependency Injection**: FastAPI's native DI for service and repository management
**Single Responsibility**: Each service module handles one domain concern
**Fail-Fast Validation**: Input validation at API boundary with Pydantic models
**Stateless API Design**: No server-side session management; authentication via tokens
**Idempotency**: Critical operations (payment, document generation) designed for safe retries

### 2.3 Technology Stack

**Core Framework**: FastAPI 0.104+ (async support, automatic OpenAPI documentation)
**Database**: MySQL 8.0+ (relational data with ACID guarantees)
**ORM**: SQLAlchemy 2.0 (async support, type safety)
**Validation**: Pydantic 2.0 (request/response models, configuration)
**Document Generation**: python-docx (DOCX template manipulation)
**Image Processing**: Pillow (logo resizing, format conversion)
**Email**: SMTP via smtplib / aiosmtplib (async email delivery)
**File Storage**: Local filesystem (Phase 1), AWS S3 (Phase 3+)
**Payment Processing**: Stripe SDK (webhook handling)
**Task Queue**: Celery + Redis (Phase 2+, for async document generation)
**Testing**: pytest, pytest-asyncio, httpx (for async endpoint testing)
**Migrations**: Alembic (database schema versioning)

### 2.4 External Dependencies

**Stripe API**: Payment processing and webhook events
**SMTP Server**: Transactional email delivery (SendGrid, Amazon SES, or similar)
**Cloud Storage**: S3-compatible storage for generated documents and uploaded logos
**LLM Provider**: OpenAI API (Phase 2+) for industry-specific content generation

### 2.5 OHS Remote Backend - Project File Structure

#### Complete Directory Layout

```
ohs-remote-backend/
│
├── alembic/                          # Database migrations
│   ├── versions/                     # Migration version files
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_company_logos.py
│   │   └── 003_add_email_logs.py
│   ├── env.py                        # Alembic environment configuration
│   └── script.py.mako                # Migration template
│
├── app/                              # Main application package
│   ├── __init__.py
│   │
│   ├── main.py                       # FastAPI application entry point
│   ├── config.py                     # Configuration management (env vars, settings)
│   ├── dependencies.py               # Dependency injection providers
│   │
│   ├── api/                          # API layer
│   │   ├── __init__.py
│   │   ├── v1/                       # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # Main API router aggregator
│   │   │   │
│   │   │   └── endpoints/            # Individual endpoint modules
│   │   │       ├── __init__.py
│   │   │       ├── orders.py         # Order creation and management endpoints
│   │   │       ├── documents.py      # Document preview and download endpoints
│   │   │       ├── payments.py       # Payment processing endpoints
│   │   │       ├── legal.py          # Legal disclaimer endpoints
│   │   │       ├── webhooks.py       # External webhook handlers (Stripe)
│   │   │       ├── auth.py           # Authentication endpoints (Phase 2+)
│   │   │       └── admin.py          # Admin management endpoints (Phase 3+)
│   │   │
│   │   └── middleware/               # Custom middleware
│   │       ├── __init__.py
│   │       ├── error_handler.py      # Global error handling
│   │       ├── logging.py            # Request/response logging
│   │       └── rate_limiter.py       # Rate limiting middleware
│   │
│   ├── core/                         # Core business logic
│   │   ├── __init__.py
│   │   ├── security.py               # Security utilities (hashing, tokens)
│   │   ├── exceptions.py             # Custom exception definitions
│   │   └── constants.py              # Application-wide constants
│   │
│   ├── services/                     # Service layer (business logic)
│   │   ├── __init__.py
│   │   ├── order_service.py          # Order lifecycle management
│   │   ├── document_generation_service.py  # Document creation logic
│   │   ├── file_storage_service.py   # File upload and storage handling
│   │   ├── email_service.py          # Email delivery and tracking
│   │   ├── payment_service.py        # Payment processing (Stripe integration)
│   │   ├── validation_service.py     # Input validation and business rules
│   │   ├── preview_service.py        # Preview document generation
│   │   ├── auth_service.py           # Authentication logic (Phase 2+)
│   │   └── ai_content_service.py     # LLM integration (Phase 2+)
│   │
│   ├── repositories/                 # Data access layer
│   │   ├── __init__.py
│   │   ├── base_repository.py        # Base repository with common CRUD operations
│   │   ├── user_repository.py        # User data access
│   │   ├── order_repository.py       # Order data access
│   │   ├── company_repository.py     # Company data access
│   │   ├── document_repository.py    # Document data access
│   │   ├── plan_repository.py        # Plan data access
│   │   ├── email_log_repository.py   # Email log data access
│   │   └── legal_repository.py       # Legal acknowledgment data access
│   │
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                   # Base model with common fields
│   │   ├── user.py                   # User model
│   │   ├── admin_user.py             # Admin user model
│   │   ├── company.py                # Company model
│   │   ├── order.py                  # Order model
│   │   ├── order_status.py           # Order status model
│   │   ├── document.py               # Document model
│   │   ├── plan.py                   # Plan model
│   │   ├── legal_acknowledgment.py   # Legal acknowledgment model
│   │   ├── email_log.py              # Email log model
│   │   ├── company_logo.py           # Company logo model
│   │   ├── naics_user_content.py     # NAICS content mapping model
│   │   └── system_log.py             # System log model
│   │
│   ├── schemas/                      # Pydantic schemas (request/response models)
│   │   ├── __init__.py
│   │   ├── order.py                  # Order-related schemas
│   │   ├── company.py                # Company-related schemas
│   │   ├── document.py               # Document-related schemas
│   │   ├── payment.py                # Payment-related schemas
│   │   ├── legal.py                  # Legal disclaimer schemas
│   │   ├── user.py                   # User schemas
│   │   ├── plan.py                   # Plan schemas
│   │   ├── email.py                  # Email schemas
│   │   └── common.py                 # Common/shared schemas (error responses, pagination)
│   │
│   ├── database/                     # Database configuration
│   │   ├── __init__.py
│   │   ├── session.py                # Database session management
│   │   ├── connection.py             # Database connection setup
│   │   └── base.py                   # Declarative base for models
│   │
│   ├── utils/                        # Utility functions
│   │   ├── __init__.py
│   │   ├── file_helpers.py           # File manipulation utilities
│   │   ├── image_processor.py        # Image resizing and format conversion
│   │   ├── naics_validator.py        # NAICS code validation logic
│   │   ├── date_helpers.py           # Date/time formatting utilities
│   │   ├── string_helpers.py         # String manipulation utilities
│   │   └── logger.py                 # Logging configuration and utilities
│   │
│   └── workers/                      # Background task workers (Phase 2+)
│       ├── __init__.py
│       ├── celery_app.py             # Celery application configuration
│       ├── document_tasks.py         # Async document generation tasks
│       └── email_tasks.py            # Async email delivery tasks
│
├── templates/                        # Document and email templates
│   ├── documents/                    # DOCX templates
│   │   ├── basic_manual_template.docx
│   │   ├── comprehensive_manual_template.docx
│   │   └── industry_specific_template.docx
│   │
│   └── emails/                       # Email HTML templates (Jinja2)
│       ├── order_confirmation.html
│       ├── document_delivery.html
│       ├── otp_authentication.html
│       └── payment_receipt.html
│
├── data/                             # Local data storage (Phase 1)
│   ├── uploads/                      # Uploaded files
│   │   └── logos/                    # Company logos
│   │
│   └── documents/                    # Generated documents
│       ├── generated/                # Full documents
│       └── previews/                 # Preview versions
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Pytest configuration and fixtures
│   │
│   ├── unit/                         # Unit tests
│   │   ├── __init__.py
│   │   ├── services/                 # Service layer tests
│   │   │   ├── test_order_service.py
│   │   │   ├── test_document_generation_service.py
│   │   │   ├── test_file_storage_service.py
│   │   │   ├── test_email_service.py
│   │   │   └── test_validation_service.py
│   │   │
│   │   ├── repositories/             # Repository tests
│   │   │   ├── test_order_repository.py
│   │   │   └── test_document_repository.py
│   │   │
│   │   └── utils/                    # Utility function tests
│   │       ├── test_naics_validator.py
│   │       └── test_image_processor.py
│   │
│   ├── integration/                  # Integration tests
│   │   ├── __init__.py
│   │   ├── test_order_flow.py        # End-to-end order workflow tests
│   │   ├── test_document_generation.py
│   │   ├── test_payment_flow.py
│   │   └── test_email_delivery.py
│   │
│   └── api/                          # API endpoint tests
│       ├── __init__.py
│       ├── test_orders_endpoints.py
│       ├── test_documents_endpoints.py
│       ├── test_payments_endpoints.py
│       └── test_webhooks.py
│
├── scripts/                          # Utility scripts
│   ├── seed_database.py              # Seed initial data (plans, legal disclaimers)
│   ├── migrate_to_s3.py              # File migration script (Phase 3)
│   ├── generate_test_order.py        # Create test order for development
│   └── cleanup_old_files.py          # Cleanup script for expired documents
│
├── docs/                             # Additional documentation
│   ├── architecture.md               # Architecture overview
│   ├── api_guide.md                  # API usage guide
│   ├── deployment.md                 # Deployment instructions
│   ├── database_schema.md            # Database schema documentation
│   └── troubleshooting.md            # Common issues and solutions
│
├── .github/                          # GitHub specific files
│   └── workflows/                    # CI/CD workflows
│       ├── test.yml                  # Run tests on PR
│       ├── lint.yml                  # Linting and type checking
│       └── deploy.yml                # Deployment workflow
│
├── docker/                           # Docker configuration
│   ├── Dockerfile                    # Application container
│   ├── Dockerfile.worker             # Celery worker container (Phase 2+)
│   └── docker-compose.yml            # Local development stack
│
├── .env.example                      # Example environment variables
├── .env.development                  # Development environment config (git-ignored)
├── .env.staging                      # Staging environment config (git-ignored)
├── .env.production                   # Production environment config (git-ignored)
│
├── .gitignore                        # Git ignore rules
├── .dockerignore                     # Docker ignore rules
│
├── requirements.txt                  # Python dependencies
├── requirements-dev.txt              # Development dependencies (pytest, mypy, ruff)
│
├── alembic.ini                       # Alembic configuration
├── pyproject.toml                    # Python project metadata and tool configs
├── pytest.ini                        # Pytest configuration
├── mypy.ini                          # Type checking configuration
├── ruff.toml                         # Linting configuration
│
├── README.md                         # Project overview and setup instructions
├── CONTRIBUTING.md                   # Contribution guidelines
├── CHANGELOG.md                      # Version history
└── LICENSE                           # Software license
```

---

#### Key Directory Explanations

##### `/app` - Main Application Package
The core application code organized by architectural layers. All business logic, API endpoints, and data access code resides here.

##### `/app/api/v1/endpoints` - API Endpoints
Each file represents a logical grouping of related endpoints. For example, `orders.py` contains all order-related endpoints (create, update, retrieve summary). This structure allows for easy endpoint discovery and maintains single responsibility principle.

##### `/app/services` - Business Logic Layer
Services encapsulate business rules and orchestrate operations across multiple repositories. They are the primary entry point for API endpoints and contain no direct database access. This separation enables easy testing through mocking and promotes code reuse.

##### `/app/repositories` - Data Access Layer
Repositories provide an abstraction over database operations. Each repository corresponds to a database entity and provides CRUD operations plus domain-specific queries. This pattern isolates SQL logic and makes it easier to change database implementations.

##### `/app/models` - SQLAlchemy ORM Models
Database table definitions using SQLAlchemy's declarative syntax. These models define relationships, constraints, and table structure. They are used exclusively by repositories and never exposed directly to API endpoints.

##### `/app/schemas` - Pydantic Schemas
Request and response models for API validation. These schemas define what data the API accepts and returns, providing automatic validation, serialization, and OpenAPI documentation generation. They act as a contract between frontend and backend.

##### `/templates` - Document and Email Templates
DOCX templates for document generation and Jinja2 HTML templates for email rendering. Templates are versioned and stored under version control to track changes over time.

##### `/data` - Local File Storage (Phase 1 Only)
Temporary storage for uploaded logos and generated documents during Phase 1 development. This directory is git-ignored and will be replaced by S3 in Phase 3.

##### `/tests` - Test Suite
Organized by test type (unit, integration, API). Test files mirror the structure of `/app` for easy navigation. Fixtures and test utilities are centralized in `conftest.py`.

##### `/scripts` - Operational Scripts
One-off scripts for database seeding, data migration, and maintenance tasks. These scripts use the same application code (services, repositories) to ensure consistency with production logic.

##### `/docker` - Containerization
Dockerfile for application container and docker-compose configuration for local development stack (application + MySQL + Redis). Separate Dockerfile for Celery workers in Phase 2+.

---

## 3. Data Architecture

### 3.1 Database Design Philosophy

The database schema follows normalization principles while maintaining pragmatic denormalization where read performance is critical. The ERD provided in the SRS serves as the foundation, with adjustments based on implementation realities discovered during development.

### 3.2 Core Entities

**users**: Customer accounts (email, full_name, company_name, created_at, last_login)
**admin_users**: Administrative access (username, password_hash, role, created_at)
**company**: Company profiles linked to orders (company_name, logo, province, NAICS codes)
**orders**: Purchase records (user, plan, jurisdiction, NAICS, total_amount, order_status, created_at, completed_at)
**order_status**: Status tracking (order_id, status, currency, payment_provider, payment_status)
**documents**: Generated files (order, document_id, content, file_path, format, is_ai_created, access_token, generated_at, last_downloaded)
**plans**: Package definitions (plan_id, plan_name, plan_slug, description, base_price, requires_admin_approval, is_ai_enhanced, is_available)
**legal_acknowledgments**: Signed disclaimers (ack_id, plan, jurisdiction, content, version, effective_date)
**email_logs**: Delivery tracking (email_id, order, recipient_email, subject, status, sent_at, failure_reason)
**naics_user_content**: Custom industry content mapping (order, NAICS code, suggested_sections, procedures)
**company_logos**: Uploaded branding assets (logo_id, order, company, file_path, created_at)
**system_logs**: Operational logging (log_id, source, log_level, message, metadata, created_at)

### 3.3 Indexing Strategy

**Primary Keys**: Auto-increment integers on all tables
**Foreign Keys**: Properly indexed relationships (user_id, order_id, company_id)
**Search Indexes**: email (users), order_status (orders), NAICS code (naics_user_content)
**Composite Indexes**: (order_id, created_at) for order history queries

### 3.4 Data Lifecycle

**User Data Retention**: Indefinite for purchased orders; cleanup policy TBD for abandoned carts
**Document Storage**: Generated documents retained for 90 days post-purchase, then archived to cold storage
**Log Retention**: System logs retained for 30 days in hot storage, 1 year in cold storage
**Audit Trail**: Order status changes, payment events, and document access logged immutably

---

## 4. API Endpoint Specification

### 4.1 Endpoint Design Principles

**RESTful Conventions**: Resource-based URLs, appropriate HTTP methods
**Versioning**: URL path versioning (`/api/v1/`) for future compatibility
**Consistent Response Format**: Standardized success/error response structures
**Pagination**: Cursor-based pagination for list endpoints
**Rate Limiting**: Per-IP and per-user rate limits to prevent abuse

### 4.2 Phase 1 Endpoints (MVP)

#### 4.2.1 Order Creation and Configuration

**POST /api/v1/orders**
Purpose: Initialize new order with plan selection
Request Body: plan_id, user_email, company_name
Response: order_id, order_summary, next_step_url
Database Operations: Insert into orders, users (if new), company

**PATCH /api/v1/orders/{order_id}/company-details**
Purpose: Update company information and upload logo
Request Body: province, naics_codes (array), logo (multipart file upload)
Response: order_id, company_data, validation_status
Database Operations: Update company, insert company_logos, validate NAICS format
File Operations: Save uploaded logo to temporary storage, resize if needed

**GET /api/v1/orders/{order_id}/summary**
Purpose: Retrieve current order state for frontend Order Summary component
Response: order_id, selected_plan, province, naics_codes, total_amount, completion_status
Database Operations: Join orders, plans, company tables

#### 4.2.2 Document Preview Generation

**POST /api/v1/orders/{order_id}/generate-preview**
Purpose: Create blurred preview document for frontend display
Request Body: None (uses existing order data)
Response: preview_url, table_of_contents (array), estimated_page_count
Database Operations: Fetch order, company, plan data; insert documents record
Document Operations: Generate DOCX from template, inject variables and logo, create preview version
File Operations: Save full document to secure storage, create blurred preview variant

**GET /api/v1/documents/{document_id}/preview**
Purpose: Serve preview document file
Response: Binary file stream (DOCX)
Security: Validate document belongs to requesting order, apply access token validation

#### 4.2.3 Legal Acknowledgment

**GET /api/v1/legal-disclaimers/{plan_id}/{jurisdiction}**
Purpose: Retrieve applicable legal disclaimer text
Response: disclaimer_text, version, effective_date
Database Operations: Query legal_acknowledgments

**POST /api/v1/orders/{order_id}/acknowledge-terms**
Purpose: Record user's acceptance of legal terms
Request Body: signature_text, acknowledged_at (timestamp)
Response: acknowledgment_id, status
Database Operations: Insert into legal_acknowledgments junction table with order

#### 4.2.4 Payment Processing (Mocked in Phase 1)

**POST /api/v1/orders/{order_id}/payment-intent**
Purpose: Initialize payment flow (mocked response in Phase 1)
Request Body: None (amount derived from order)
Response: mock_payment_token, amount, currency, status: "succeeded"
Database Operations: Update order_status to "payment_initiated"
Note: Phase 1 always returns successful mock payment; no actual Stripe integration

**POST /api/v1/webhooks/payment-confirmation**
Purpose: Receive payment confirmation (simulated in Phase 1)
Request Body: order_id, payment_status, transaction_id
Response: status: "processed"
Database Operations: Update order_status to "paid", set completed_at timestamp
Triggers: Document finalization, email delivery

#### 4.2.5 Document Delivery

**POST /api/v1/orders/{order_id}/deliver**
Purpose: Trigger email delivery of final documents (internal call after payment)
Request Body: None
Response: email_sent: true, delivery_status
Database Operations: Insert email_logs record
Email Operations: Send transactional email with document attachment or secure download link
File Operations: Retrieve final document from storage

**GET /api/v1/documents/{document_id}/download**
Purpose: Secure download of purchased document
Query Parameters: access_token (for authentication)
Response: Binary file stream (DOCX)
Security: Validate access_token matches document record, check order payment status
Database Operations: Log download event in documents table (last_downloaded)

### 4.3 Phase 2+ Endpoints (Future Iterations)

**POST /api/v1/orders/{order_id}/generate-industry-content**
Purpose: AI-powered SJP and JHA generation based on NAICS codes
Request Body: selected_procedures (array), customization_options
Response: generated_content_preview, estimated_completion_time
AI Integration: Call OpenAI API with RAG-enhanced prompts using jurisdiction and industry context

**POST /api/v1/auth/login**
Purpose: User authentication for order re-access
Request Body: email
Response: otp_sent: true
Security: Generate and email one-time password

**POST /api/v1/auth/verify-otp**
Purpose: Validate OTP and issue access token
Request Body: email, otp_code
Response: access_token, user_orders (array)
Security: JWT token generation with short expiration

**Admin Endpoints (Phase 3)**:
- POST /api/v1/admin/templates (upload/update document templates)
- PATCH /api/v1/admin/plans/{plan_id} (modify pricing and plan details)
- GET /api/v1/admin/orders (paginated order management)
- POST /api/v1/admin/naics-mappings (manage industry content mappings)

---

## 5. Service Layer Architecture

### 5.1 Service Modules

**OrderService**: Order lifecycle management (creation, updates, status transitions)
**DocumentGenerationService**: Template processing, variable injection, DOCX manipulation
**FileStorageService**: Upload handling, file persistence, retrieval, temporary file cleanup
**EmailService**: SMTP integration, template rendering, delivery tracking
**PaymentService**: Stripe integration, webhook processing, payment verification
**ValidationService**: NAICS format validation, input sanitization, business rule enforcement
**AuthenticationService**: OTP generation, token management (Phase 2+)
**AIContentService**: LLM integration for industry-specific content generation (Phase 2+)

### 5.2 Service Interaction Patterns

Services communicate through well-defined interfaces and avoid direct database access. Each service receives repository dependencies via dependency injection.

Example Flow (Order to Document Delivery):
1. OrderService creates order, delegates logo handling to FileStorageService
2. DocumentGenerationService receives order data, calls FileStorageService for logo, generates document
3. PaymentService processes payment, notifies OrderService of success
4. OrderService triggers DocumentGenerationService for final document
5. EmailService retrieves document from FileStorageService, sends delivery email

### 5.3 Error Handling Strategy

**Validation Errors**: Return 400 Bad Request with detailed field-level errors
**Authentication Errors**: Return 401 Unauthorized with generic message (prevent user enumeration)
**Authorization Errors**: Return 403 Forbidden
**Resource Not Found**: Return 404 Not Found
**Server Errors**: Return 500 Internal Server Error, log full stack trace, return sanitized message to client
**External Service Failures**: Retry with exponential backoff for transient errors, return 503 Service Unavailable for persistent failures

All errors follow consistent JSON structure:
```
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {...}
  }
}
```

---

## 6. Document Generation Strategy

### 6.1 Phase 1 Approach (Template-Based)

**Template Storage**: Pre-authored DOCX templates stored in `/templates` directory with placeholder variables
**Variable Syntax**: Use double braces for replacement `{{company_name}}`, `{{province}}`, `{{naics_codes}}`
**Logo Injection**: python-docx library to insert logo image at designated placeholder location
**Table of Contents**: Generate programmatically based on selected plan's section structure
**Preview Generation**: Full document generated first, then create blurred/watermarked version for preview

**Template Structure**:
- Header section with logo placeholder
- Policy statement with company name and jurisdiction variables
- Section placeholders for roles, responsibilities, procedures
- Footer with generation date and disclaimer

### 6.2 Phase 2+ Approach (AI-Enhanced)

**RAG Implementation**: Maintain vector database of jurisdiction-specific regulations and industry best practices
**Prompt Engineering**: Structured prompts that include NAICS context, jurisdiction requirements, company details
**Content Validation**: Human-in-the-loop review for AI-generated procedures before customer delivery (admin approval workflow)
**Fallback Mechanism**: If AI generation fails or produces low-quality output, revert to template-based sections

### 6.3 Document Versioning

Each generated document includes:
- Generation timestamp
- Template version identifier
- NAICS codes used for customization
- Jurisdiction applied
- Hash of input parameters (for reproducing identical document if needed)

---

## 7. File Handling and Storage

### 7.1 Phase 1 (Local Filesystem)

**Directory Structure**:
```
/data
  /uploads
    /logos
      /{order_id}_logo.png
  /documents
    /generated
      /{order_id}_{document_id}.docx
    /previews
      /{order_id}_{document_id}_preview.docx
  /templates
    basic_manual.docx
    comprehensive_manual.docx
```

**File Naming Convention**: `{order_id}_{timestamp}_{file_type}.{extension}`
**Access Control**: Files served through API endpoints with access token validation, not direct filesystem access
**Cleanup Policy**: Temporary preview files deleted after 24 hours, generated documents archived after 90 days

### 7.2 Phase 3+ (Cloud Storage)

**S3 Bucket Structure**:
- `ohs-remote-uploads/logos/`
- `ohs-remote-documents/generated/`
- `ohs-remote-documents/previews/`
- `ohs-remote-documents/archived/`

**Signed URLs**: Generate time-limited pre-signed URLs for secure document downloads
**CDN Integration**: CloudFront distribution for preview document delivery
**Redundancy**: Cross-region replication for generated documents, single-region for temporary files

---

## 8. Email Delivery System

### 8.1 Email Templates

**Order Confirmation**: Sent after payment success, includes order summary and document download link
**Document Delivery**: Sent after document generation, includes DOCX attachment (if under 10MB) or secure download link
**OTP Authentication** (Phase 2): Sent when user requests order re-access
**Admin Notifications** (Phase 3): Alert admins of failed document generations or payment issues

### 8.2 Delivery Mechanism

**SMTP Configuration**: Environment variables for SMTP host, port, username, password
**Retry Logic**: Three attempts with exponential backoff (0s, 30s, 120s) for transient failures
**Failure Tracking**: Log all failures in email_logs table with failure_reason for debugging
**Rate Limiting**: Respect SMTP provider limits (e.g., 100 emails/hour for development tier)

### 8.3 Content Rendering

**HTML Templates**: Use Jinja2 for dynamic email template rendering
**Plain Text Fallback**: Always include plain text version for email clients that don't support HTML
**Attachment Handling**: DOCX files attached with correct MIME type `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

---

## 9. Security Considerations

### 9.1 Input Validation

**NAICS Code Format**: Regex validation for 6-digit format, cross-reference against official NAICS database
**Email Validation**: RFC 5322 compliant email format validation
**File Upload Restrictions**: Whitelist allowed MIME types (image/png, image/jpeg, image/svg+xml), max file size 5MB
**SQL Injection Prevention**: Parameterized queries via SQLAlchemy ORM, no raw SQL string concatenation
**XSS Prevention**: Output encoding for any user input reflected in generated documents or emails

### 9.2 Authentication and Authorization

**Phase 1**: No authentication (stateless order creation by order ID + email validation implicit through payment email)
**Phase 2**: OTP-based authentication for order re-access, JWT tokens with 1-hour expiration
**Phase 3**: Admin authentication via password hash (bcrypt), role-based access control (RBAC)

### 9.3 Data Protection

**At-Rest Encryption**: Database encryption enabled at MySQL layer, filesystem encryption for document storage
**In-Transit Encryption**: HTTPS/TLS 1.3 for all API traffic, SMTP over TLS for email delivery
**PII Handling**: Email addresses and company names treated as PII, access logged and audited
**Payment Data**: No credit card data stored in database, all payment processing delegated to Stripe (PCI DSS compliance)

### 9.4 Rate Limiting

**API Endpoints**: 100 requests/minute per IP address for anonymous endpoints, 500 requests/minute for authenticated users
**Document Generation**: Max 5 preview generations per order to prevent resource exhaustion
**File Uploads**: Max 10 uploads per IP address per hour

---

## 10. Testing Strategy

### 10.1 Unit Testing

**Coverage Target**: Minimum 80% code coverage for service layer and business logic
**Test Framework**: pytest with pytest-asyncio for async function testing
**Mocking**: Mock external dependencies (Stripe API, SMTP, file system) using pytest fixtures
**Test Data**: Factory pattern for generating test entities (users, orders, documents)

**Critical Test Cases**:
- Order creation with valid and invalid inputs
- NAICS code validation edge cases
- Document generation with missing template files
- Logo upload with oversized files and unsupported formats
- Payment webhook processing with various status codes
- Email delivery retry logic on transient failures

### 10.2 Integration Testing

**Database Testing**: Use test database with identical schema, seed with fixture data before each test run
**API Testing**: httpx client to simulate HTTP requests, validate response status codes and payloads
**End-to-End Flows**: Test complete order-to-delivery workflow with mocked external services

**Test Scenarios**:
- Happy path: Order creation → logo upload → preview generation → payment → email delivery
- Error path: Invalid NAICS code rejection, payment failure handling, document generation timeout
- Idempotency: Retry payment webhook processing, verify no duplicate emails sent

### 10.3 Performance Testing

**Load Testing**: Apache JMeter or Locust to simulate 100 concurrent users placing orders
**Benchmarks**: Document generation under 30 seconds for Basic plan, under 60 seconds for Comprehensive
**Database Queries**: All queries optimized to execute under 100ms, use EXPLAIN ANALYZE for slow query debugging

### 10.4 Security Testing

**OWASP Top 10**: Validate protection against SQL injection, XSS, CSRF, insecure deserialization
**Dependency Scanning**: Safety or Snyk to scan for known vulnerabilities in Python packages
**Secret Management**: Verify no hardcoded secrets in codebase, all credentials in environment variables

---

## 11. Phased Implementation Plan

### Phase 1: MVP - Core Workflow (4-6 weeks)

**Objective**: Deliver functional demo with end-to-end order-to-document flow using template-based generation and mocked payment.

**Deliverables**:
- FastAPI project structure with environment configuration
- MySQL database schema with Alembic migrations
- API endpoints for order creation, company details, document preview, legal acknowledgment, mocked payment
- Template-based document generation with variable injection and logo embedding
- Preview document generation (blurred variant)
- Email delivery system with DOCX attachment
- Local filesystem storage for uploads and generated documents
- Unit tests for critical service methods
- Postman collection for API testing

**Success Criteria**:
- Frontend can complete full workflow from landing page to order confirmation
- Generated DOCX contains company name, logo, and jurisdiction-specific content
- Email delivered to test inbox with correct attachment
- No errors logged during happy path execution

**Technical Debt Accepted**:
- No authentication or user re-access functionality
- Mocked payment always succeeds
- Local filesystem storage instead of cloud
- Synchronous document generation (may block API response)
- Minimal error handling for edge cases
- No admin interface

---

### Phase 2: AI Integration and Asynchronous Processing (6-8 weeks)

**Objective**: Add industry-specific content generation using LLM, implement async task processing to improve responsiveness, and enable user authentication for order re-access.

**Deliverables**:
- Celery task queue with Redis broker for async document generation
- OpenAI API integration for SJP and JHA generation
- RAG pipeline with vector database (Pinecone or Weaviate) for jurisdiction-specific regulations
- OTP-based authentication system with JWT tokens
- Endpoint for order re-access and document re-download
- Enhanced API endpoints for industry-specific content customization
- Improved error handling and retry logic for LLM API failures
- Performance monitoring dashboard (optional: New Relic or Datadog)

**Success Criteria**:
- Document generation returns immediately with "processing" status, frontend polls for completion
- Industry-Specific plan generates 5+ tailored SJPs based on NAICS code
- Users can re-access past orders via email + OTP flow
- AI-generated content passes quality threshold (human review required in Phase 3)
- API response times under 200ms for all synchronous endpoints

**Technical Debt Addressed**:
- Move document generation to background tasks
- Implement proper authentication for sensitive operations
- Add structured logging for debugging async workflows

---

### Phase 3: Admin Tools and Production Readiness (4-6 weeks)

**Objective**: Build administrative interface for content management, migrate to cloud infrastructure, implement production-grade security and monitoring.

**Deliverables**:
- Admin authentication with role-based access control
- Admin endpoints for template management, plan pricing updates, NAICS mapping configuration
- Order management dashboard (view orders, resend emails, regenerate documents)
- Migration to AWS S3 for file storage with CloudFront CDN
- Stripe payment integration with webhook signature verification
- CI/CD pipeline (GitHub Actions or GitLab CI)
- Production deployment on AWS ECS or similar container orchestration
- Comprehensive API documentation (auto-generated by FastAPI + Swagger UI)
- Load testing results and performance tuning

**Success Criteria**:
- Admins can update pricing without code deployment
- Documents served via CDN with 95th percentile latency under 500ms
- Stripe webhooks processed securely with signature validation
- Zero downtime deployment achieved via blue-green or rolling update strategy
- Application scales horizontally to handle 1000 concurrent users

**Technical Debt Addressed**:
- Replace local filesystem with S3
- Implement actual payment processing with Stripe
- Add monitoring and alerting for production issues

---

### Phase 4: Advanced Features and Optimization (Ongoing)

**Objective**: Continuous improvement based on user feedback, compliance updates, and emerging requirements.

**Future Enhancements**:
- Multi-language support for bilingual jurisdictions (e.g., Quebec)
- Document versioning system for tracking template changes over time
- Bulk order discounts and enterprise licensing
- API webhooks for third-party integrations
- Mobile-optimized document previews (PDF conversion)
- Advanced analytics dashboard for admin (order volume, revenue trends, popular plans)
- Automated compliance monitoring (track changes in OHS regulations, notify of required template updates)
- White-label deployment for enterprise clients

---

## 12. Development Workflow

### 12.1 Version Control

**Repository Structure**: Monorepo with `/backend` and `/frontend` directories (or separate repos if preferred)
**Branching Strategy**: GitFlow with `main` (production), `develop` (staging), feature branches (`feature/order-creation`)
**Commit Convention**: Conventional Commits (feat, fix, docs, chore) for automated changelog generation
**Code Review**: All changes require peer review via pull requests before merging to `develop`

### 12.2 Environment Management

**Development**: Local MySQL, local file storage, mocked external services
**Staging**: Cloud-hosted database (AWS RDS), S3 storage, Stripe test mode, production-like infrastructure
**Production**: Multi-AZ database, S3 with versioning, Stripe live mode, auto-scaling enabled

**Configuration**: Environment-specific `.env` files managed via python-dotenv, secrets stored in AWS Secrets Manager (production)

### 12.3 Deployment Process

**Phase 1-2**: Manual deployment via SSH or Docker Compose on single EC2 instance
**Phase 3+**: Automated deployment via CI/CD pipeline:
1. Code pushed to `develop` branch
2. CI runs linting (ruff), type checking (mypy), unit tests
3. Build Docker image, push to container registry
4. Deploy to staging environment, run integration tests
5. Manual approval gate for production deployment
6. Blue-green deployment to production, health check validation
7. Rollback automation if health checks fail

---

## 13. Monitoring and Observability

### 13.1 Logging Strategy

**Structured Logging**: JSON-formatted logs with contextual metadata (request_id, user_id, order_id)
**Log Levels**: DEBUG (development only), INFO (significant events), WARNING (recoverable errors), ERROR (unhandled exceptions)
**Sensitive Data**: Never log passwords, payment tokens, or full credit card numbers; redact PII from logs
**Log Aggregation** (Phase 3+): CloudWatch Logs or ELK stack for centralized log management

### 13.2 Metrics and Alerting

**Key Metrics**:
- Request rate and error rate per endpoint
- Document generation latency (p50, p95, p99)
- Email delivery success rate
- Database query performance
- External API call latency (Stripe, OpenAI)
- Disk space usage for document storage

**Alerts**:
- Error rate exceeds 5% over 5-minute window
- Document generation latency p95 exceeds 2 minutes
- Database connection pool exhaustion
- Email delivery failures exceed 10% over 1 hour

---

## 14. Database Migration Strategy

### 14.1 Schema Evolution

**Alembic Migrations**: All schema changes tracked in version-controlled migration files
**Migration Testing**: Test migrations on copy of production data before applying to live database
**Rollback Plan**: Every migration includes downgrade function for safe rollback
**Zero-Downtime Changes**: Additive changes (new columns, tables) deployed first, removal of deprecated columns in subsequent release

### 14.2 Data Migration

**Backfill Strategy**: For new required columns, run data migration scripts before enforcing NOT NULL constraints
**Performance**: Large table migrations executed during low-traffic windows, use batching to avoid locking

---

## 15. API Documentation

### 15.1 OpenAPI Specification

FastAPI auto-generates OpenAPI 3.0 schema available at `/docs` (Swagger UI) and `/redoc` (ReDoc interface).

**Documentation Requirements**:
- All endpoints include summary and description
- Request/response models documented with field descriptions and examples
- Authentication requirements clearly indicated
- Error responses documented with example payloads

### 15.2 Developer Onboarding

**README**: Project setup instructions, dependency installation, database initialization
**Architecture Diagram**: Mermaid diagram in repository showing service interactions
**API Tutorial**: Step-by-step guide for completing order workflow using curl or Postman
**Troubleshooting Guide**: Common errors and solutions for local development

---

## 16. Risk Management

### 16.1 Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM API rate limits or cost overruns | High | Medium | Implement caching, set cost alerts, fallback to template-based generation |
| Document generation timeout | High | Medium | Async processing with timeout handling, notify user via email when ready |
| Stripe webhook delivery failure | High | Low | Idempotent webhook processing, manual reconciliation tool for admins |
| Database performance degradation | Medium | Medium | Query optimization, connection pooling, read replicas if needed |
| File storage capacity limits | Medium | Low | Monitor disk usage, implement archival policy, migrate to S3 early |

### 16.2 Business Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| AI-generated content quality issues | High | Medium | Human review workflow, customer feedback mechanism, template fallback |
| Jurisdictional compliance changes | Medium | Medium | Track regulatory updates, version templates, notify admins of required changes |
| Payment processing disputes | Medium | Low | Detailed order logs, customer support email response process |

---

## 17. Success Metrics

### 17.1 Technical Metrics

**Phase 1 MVP**:
- 100% uptime during demo sessions
- Document generation completes within 30 seconds
- Zero critical bugs reported during client testing

**Phase 2 AI Integration**:
- 95% of AI-generated content approved without edits
- Average document generation latency under 60 seconds
- 99% email delivery success rate

**Phase 3 Production**:
- 99.5% uptime SLA
- Support 100 concurrent orders without performance degradation
- Database query latency p95 under 100ms

### 17.2 Business Metrics

- Order completion rate (users who start vs. complete purchase)
- Average order value
- Customer satisfaction score (post-purchase survey)
- Support ticket volume related to document quality

---

## 18. Handoff and Maintenance

### 18.1 Documentation Deliverables

**Technical Documentation**:
- Architecture decision records (ADRs) for major design choices
- API reference guide (auto-generated + supplemental docs)
- Database schema documentation
- Deployment runbook

**Operational Documentation**:
- Monitoring dashboard guide
- Incident response playbook
- Backup and recovery procedures
- Disaster recovery plan

### 18.2 Knowledge Transfer

**Developer Onboarding**:
- Pair programming sessions for first feature implementation
- Code review process walkthrough
- Troubleshooting workshop for common issues

**Client Training** (if applicable):
- Admin interface user guide
- Content management best practices
- Support escalation procedures

---

## 19. Conclusion

This implementation plan provides a structured roadmap for building the OHS Remote backend from initial MVP through production deployment and ongoing enhancement. The phased approach allows for early validation of core functionality while deferring complex features (AI integration, cloud infrastructure) until business value is proven.

The architecture prioritizes maintainability through clear separation of concerns, testability through dependency injection and mocking, and scalability through async processing and cloud-native design patterns. Security and compliance considerations are integrated from the outset rather than retrofitted.

Development teams should treat this document as a living specification, updating it as implementation realities surface new requirements or constraints. Regular reviews with stakeholders ensure alignment between technical execution and business objectives.

With diligent execution of Phase 1, the team will deliver a compelling MVP that demonstrates end-to-end workflow capabilities and provides a solid foundation for subsequent iterations. The modular design ensures that enhancements in later phases integrate seamlessly without requiring significant refactoring of core systems.