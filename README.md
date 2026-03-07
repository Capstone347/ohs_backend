# OHS Remote Backend

**Safety Compliance App - Backend Service**

Professional Health & Safety manual generation platform that enables small to medium-sized businesses to obtain customized, branded, and editable OHS manual packages through a guided workflow.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Database Management](#database-management)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Development Workflow](#development-workflow)
- [Code Style & Standards](#code-style--standards)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

OHS Remote is a web-based application that generates professional Health & Safety compliance manuals tailored to specific industries and jurisdictions. The backend provides a RESTful API that handles:

- Order creation and management
- Company branding (logo upload and integration)
- NAICS-based industry classification
- Document generation from templates
- Payment processing (Stripe integration)
- Email delivery of final documents
- Secure document download with access tokens

**Current Phase:** MVP (Phase 1)  
**Status:** Active Development  
**Version:** 1.0.0

---

## Tech Stack

| Category | Technology | Version |
|----------|-----------|---------|
| **Framework** | FastAPI | 0.104+ |
| **Language** | Python | 3.11+ |
| **Database** | MySQL | 8.0+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Validation** | Pydantic | 2.0+ |
| **Migrations** | Alembic | 1.12+ |
| **Document Processing** | python-docx | 1.1+ |
| **Image Processing** | Pillow | 10.0+ |
| **Email Templates** | Jinja2 | 3.1+ |
| **Testing** | pytest | 7.4+ |
| **Containerization** | Docker & Docker Compose | - |

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Docker & Docker Compose** - [Download](https://www.docker.com/products/docker-desktop)
- **Git** - [Download](https://git-scm.com/downloads)

Optional but recommended:
- **Make** - For using Makefile commands
- **Postman** - For API testing

---

## Getting Started

### Quick Start Options

Choose your development approach:

#### Option 1: Docker Development (Recommended for Beginners)
- Everything runs in containers (app + database)
- Zero local configuration needed
- Database automatically created
- Best for: First-time setup, team consistency

#### Option 2: Local Development (Recommended for Active Development)
- App runs locally with hot reload
- Database runs in Docker
- Faster iteration cycle
- Best for: Active feature development, debugging

---

### Option 1: Docker Development Setup

**Complete containerized environment - database is automatically created**

1. **Clone the repository**
```bash
git clone https://github.com/your-org/ohs-remote-backend.git
cd ohs-remote-backend
```

2. **Start all services**
```bash
docker-compose up --build
```

The `.env.docker` file is already configured with:
- MySQL database: `ohs_remote_dev`
- User: `ohs_dev_user` / Password: `ohs_dev_password`
- Database is automatically created on first run

3. **Access the application**
- API: http://localhost:8000
- Health Check: http://localhost:8000/api/v1/health
- API Docs: http://localhost:8000/docs
- Database: localhost:3307 (external access)

4. **View logs**
```bash
docker-compose logs -f app
```

5. **Stop services**
```bash
docker-compose down
```

---

### Option 2: Local Development Setup

**App runs locally, database in Docker - faster development cycle**

1. **Clone the repository**
```bash
git clone https://github.com/your-org/ohs-remote-backend.git
cd ohs-remote-backend
```

2. **Start only the database**
```bash
docker-compose up mysql
```

The database will be available at `localhost:3307` with:
- Database: `ohs_remote_dev` (automatically created)
- Root password: `root_password`
- Port: 3307 (mapped from container's 3306)

3. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Configure environment**
```bash
cp .env.example .env
```

The default `.env` is already configured to connect to the Docker MySQL on port 3307.

5. **Run the application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the application**
- API: http://localhost:8000
- Health Check: http://localhost:8000/api/v1/health
- API Docs: http://localhost:8000/docs
- Database: localhost:3307

---

### Production Configuration

For production deployments:

1. **Set required environment variables** in your deployment platform:
   - `ENVIRONMENT=production`
   - `DEBUG=false`
   - `SECRET_KEY` - Generate with: `openssl rand -hex 32`
   - `DATABASE_URL` - Your cloud database connection string
   - All SMTP credentials for email delivery
   - Stripe API keys (production keys)

2. **Never use default values** for:
   - SECRET_KEY
   - Database passwords
   - API keys

3. **Use secrets management**:
   - AWS Secrets Manager
   - Google Cloud Secret Manager
   - Azure Key Vault
   - Environment variables in your CI/CD platform

---

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/ohs-remote-backend.git
cd ohs-remote-backend
```

### 2. Environment Configuration

Create environment file from template:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see [Environment Variables](#environment-variables) section).

### 3. Start with Docker (Recommended)

```bash
docker-compose up --build
```

This will:
- Build the FastAPI application container
- Start MySQL database container
- Create necessary data directories
- Run database migrations automatically
- Start the application on `http://localhost:8000`

### 4. Alternative: Local Development Setup

If you prefer running without Docker:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed initial data
python scripts/seed_database.py

# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify Installation

Visit `http://localhost:8000/docs` to access the interactive API documentation (Swagger UI).

Health check endpoint: `GET http://localhost:8000/health`

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Project Structure

```
ohs-remote-backend/
├── alembic/                     # Database migrations
│   └── versions/                # Migration files
├── app/                         # Main application package
│   ├── api/                     # API layer
│   │   ├── v1/endpoints/        # API endpoints by version
│   │   └── middleware/          # Custom middleware
│   ├── core/                    # Core utilities (security, exceptions)
│   ├── database/                # Database configuration
│   ├── models/                  # SQLAlchemy ORM models
│   ├── repositories/            # Data access layer
│   ├── schemas/                 # Pydantic request/response models
│   ├── services/                # Business logic layer
│   ├── utils/                   # Utility functions
│   ├── config.py                # Application configuration
│   └── main.py                  # FastAPI application entry point
├── data/                        # Local file storage (Phase 1)
│   ├── uploads/logos/           # Uploaded company logos
│   └── documents/               # Generated documents
│       ├── generated/           # Full documents
│       └── previews/            # Preview documents
├── templates/                   # Document and email templates
│   ├── documents/               # DOCX templates
│   └── emails/                  # HTML email templates
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── api/                     # API endpoint tests
├── scripts/                     # Utility scripts
├── docs/                        # Additional documentation
├── docker/                      # Docker configuration
├── .env.example                 # Environment variables template
├── docker-compose.yml           # Docker Compose configuration
├── requirements.txt             # Python dependencies
├── alembic.ini                  # Alembic configuration
├── pytest.ini                   # Pytest configuration
└── README.md                    # This file
```

---

## Environment Variables

### Required Variables

Create a `.env` file in the project root with the following variables:

```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here-change-in-production

# Database
DATABASE_URL=mysql+pymysql://ohs_user:ohs_password@localhost:3306/ohs_remote

# File Storage
DATA_DIR=/app/data
USE_S3=false

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Stripe (Phase 1: Not Used - Mocked)
STRIPE_API_KEY=sk_test_mock_key
STRIPE_WEBHOOK_SECRET=whsec_mock_secret

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Logging
LOG_LEVEL=INFO
```

### Optional Variables (Phase 2+)

```env
# AWS S3 (Phase 3+)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=ohs-remote-documents
AWS_REGION=us-east-1

# Redis (Phase 2+ for Celery)
REDIS_URL=redis://localhost:6379/0

# OpenAI (Phase 2+ for AI content generation)
OPENAI_API_KEY=sk-your-openai-key
```

### Docker Compose Variables

When using Docker Compose, database credentials are defined in `docker-compose.yml`:

```yaml
MYSQL_DATABASE=ohs_remote
MYSQL_USER=ohs_user
MYSQL_PASSWORD=ohs_password
MYSQL_ROOT_PASSWORD=root_password
```

---

## Database Management

### Running Migrations

Apply all pending migrations:

```bash
alembic upgrade head
```

Rollback to previous migration:

```bash
alembic downgrade -1
```

Rollback all migrations:

```bash
alembic downgrade base
```

### Creating New Migrations

After modifying models:

```bash
alembic revision -m "descriptive message about change"
```

Edit the generated file in `alembic/versions/` to add your migration logic.

### Seeding Initial Data

Populate database with plan data:

```bash
python scripts/seed_database.py
```

This creates:
- Basic Plan ($99 CAD)
- Comprehensive Plan ($199 CAD)
- Industry-Specific Plan ($299 CAD)

### Database Backup (Production)

```bash
# Backup
docker-compose exec mysql mysqldump -u ohs_user -p ohs_remote > backup.sql

# Restore
docker-compose exec -T mysql mysql -u ohs_user -p ohs_remote < backup.sql
```

---

## Running the Application

### Development Mode (with hot reload)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker Compose

```bash
# Start services
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build
```

### Accessing the Application

- **API Base URL:** `http://localhost:8000`
- **Interactive Docs (Swagger):** `http://localhost:8000/docs`
- **Alternative Docs (ReDoc):** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Testing

### Running All Tests

```bash
pytest
```

### Running Specific Test Types

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# API tests only
pytest tests/api/

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/services/test_order_service.py

# Run tests matching pattern
pytest -k "test_create_order"
```

### Test Coverage

View coverage report:

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

Target coverage: **80%** for service layer and business logic.

### Running Tests in Docker

```bash
docker-compose exec app pytest
```

---

## API Documentation

### Interactive Documentation

Access Swagger UI at `http://localhost:8000/docs` for:
- Complete API endpoint listing
- Request/response schemas
- Interactive testing interface
- Example requests and responses

### Postman Collection

Import the Postman collection from `docs/postman_collection.json`:

1. Open Postman
2. Click "Import"
3. Select `docs/postman_collection.json`
4. Configure environment variables (base URL, order_id)

### API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/orders` | POST | Create new order |
| `/api/v1/orders/{order_id}/company-details` | PATCH | Update company details and upload logo |
| `/api/v1/orders/{order_id}/summary` | GET | Retrieve order summary |
| `/api/v1/orders/{order_id}/generate-preview` | POST | Generate document preview |
| `/api/v1/documents/{document_id}/preview` | GET | Download preview document |
| `/api/v1/documents/{document_id}/download` | GET | Download full document (requires token) |
| `/api/v1/legal-disclaimers/{plan_id}/{jurisdiction}` | GET | Get legal disclaimer text |
| `/api/v1/orders/{order_id}/acknowledge-terms` | POST | Record legal acknowledgment |
| `/api/v1/orders/{order_id}/payment-intent` | POST | Initialize payment (mocked in Phase 1) |
| `/api/v1/webhooks/payment-confirmation` | POST | Handle payment webhook |

For detailed API documentation, see `docs/api_guide.md`.

---

## Development Workflow

### Branch Strategy

```
main              # Production-ready code
├── develop       # Integration branch
│   ├── feature/add-document-preview
│   ├── feature/implement-payment-flow
│   ├── bugfix/fix-logo-upload
│   └── refactor/extract-email-service
```

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Committing Changes

Follow conventional commit messages:

```bash
git add .
git commit -m "Add document preview generation endpoint"
git push origin feature/your-feature-name
```

Good commit messages:
- `Add OrderStatus enum for order state management`
- `Implement document generation service with template processing`
- `Fix NAICS code validation regex pattern`
- `Refactor file storage service to support S3`

### Code Review Checklist

Before submitting a PR:

- [ ] All tests pass (`pytest`)
- [ ] Code follows style guidelines (see `docs/coding_agent_instructions.md`)
- [ ] No commented-out code or TODOs without issues
- [ ] Type hints on all function signatures
- [ ] Pydantic models used instead of dictionaries
- [ ] Proper error handling with custom exceptions
- [ ] Documentation updated if adding new features
- [ ] Database migrations included if schema changed

---

## Code Style & Standards

This project follows strict coding standards defined in `docs/coding_agent_instructions.md`.

### Key Principles

1. **No dictionaries for structured data** - Use Pydantic models
2. **Single responsibility** - One function, one purpose
3. **Fail fast** - Validate inputs before processing
4. **No default values** - Required config must be explicit
5. **Type hints everywhere** - All functions fully typed
6. **Self-documenting code** - No comments or docstrings needed

### Linting and Formatting

```bash
# Run linter
ruff check app/

# Auto-fix issues
ruff check app/ --fix

# Type checking
mypy app/
```

### Import Organization

```python
# Standard library
import json
from datetime import datetime, timezone

# Third-party
from fastapi import APIRouter
from pydantic import BaseModel

# Local
from app.models.order import Order
from app.services.order_service import OrderService
```

---

## Deployment

### Docker Deployment

#### Build Production Image

```bash
docker build -t ohs-remote-backend:latest -f docker/Dockerfile .
```

#### Run Production Container

```bash
docker run -d \
  --name ohs-remote-backend \
  -p 8000:8000 \
  --env-file .env.production \
  ohs-remote-backend:latest
```

### Environment-Specific Deployment

#### Staging

```bash
docker-compose -f docker-compose.staging.yml up -d
```

#### Production

```bash
docker-compose -f docker-compose.production.yml up -d
```

### Cloud Deployment (Phase 3+)

Deployment targets:
- **AWS ECS** with RDS MySQL and S3
- **Google Cloud Run** with Cloud SQL and Cloud Storage
- **Azure Container Apps** with Azure Database and Blob Storage

Detailed deployment instructions: `docs/deployment.md`

---

## Troubleshooting

### Common Issues

#### Database Connection Error

**Problem:** `Can't connect to MySQL server on 'localhost'`

**Solution:**
```bash
# Check if MySQL container is running
docker-compose ps

# Restart database service
docker-compose restart mysql

# Verify DATABASE_URL in .env
```

#### Migration Conflicts

**Problem:** `Target database is not up to date`

**Solution:**
```bash
# Check current migration status
alembic current

# Stamp database with current head
alembic stamp head

# Or rollback and reapply
alembic downgrade base
alembic upgrade head
```

#### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### File Upload Fails

**Problem:** `FileStorageError: Cannot save logo`

**Solution:**
```bash
# Ensure data directories exist
mkdir -p data/uploads/logos
mkdir -p data/documents/generated
mkdir -p data/documents/previews

# Check directory permissions
chmod -R 755 data/
```

#### Email Not Sending

**Problem:** `EmailDeliveryError: Connection refused`

**Solution:**
```bash
# Verify SMTP credentials in .env
# For Gmail, use App Password not account password
# Enable "Less secure app access" if needed

# Test SMTP connection
python scripts/test_email.py
```

### Logs and Debugging

#### View Application Logs

```bash
# Docker
docker-compose logs -f app

# Local
tail -f logs/app.log
```

#### Enable Debug Mode

In `.env`:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

#### Database Query Logging

In `.env`:
```env
SQLALCHEMY_ECHO=true
```

For more troubleshooting, see `docs/troubleshooting.md`.

---

## Contributing

We welcome contributions! Please follow these guidelines:

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/ohs-remote-backend.git
```

### 2. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes

Follow coding standards in `docs/coding_agent_instructions.md`.

### 4. Write Tests

Add unit and integration tests for new functionality.

### 5. Submit Pull Request

- Ensure all tests pass
- Provide clear description of changes
- Reference related issues

### Code of Conduct

- Be respectful and professional
- Provide constructive feedback
- Follow project conventions
- Document significant changes

---

## License

This project is proprietary software owned by [Your Company Name].

Copyright © 2026 [Your Company Name]. All rights reserved.

Unauthorized copying, modification, distribution, or use of this software is strictly prohibited.

---

## Support

### Documentation

- [Implementation Plan](docs/implementation_plan.md)
- [API Guide](docs/api_guide.md)
- [Deployment Guide](docs/deployment.md)
- [Coding Standards](docs/coding_agent_instructions.md)
- [Troubleshooting](docs/troubleshooting.md)

### Contact

- **Project Lead:** Gustavo
- **Team:** Capstone347
- **Client:** Jennifer Murray (jmurray5077@gmail.com)

### Reporting Issues

For bugs or feature requests, create an issue on GitHub with:
- Clear description
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)

---

## Changelog

### Version 1.0.0 (Phase 1 MVP) - [Date]

**Added:**
- Complete order management workflow
- Document generation from templates
- Company logo upload and integration
- NAICS code validation
- Mocked payment processing
- Email delivery with attachments
- Secure document download with tokens

**In Progress:**
- Phase 2: AI-powered industry-specific content
- Phase 2: Async document generation with Celery
- Phase 3: Stripe payment integration
- Phase 3: AWS S3 file storage

---

## Acknowledgments

- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - Python SQL toolkit and ORM
- **Pydantic** - Data validation using Python type annotations
- **python-docx** - Document generation library
- **Alembic** - Database migration tool

---

**Built with ❤️ by Capstone347**