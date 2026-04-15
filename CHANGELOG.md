# Changelog

All notable changes to the OHS Remote Backend project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

This section reflects work merged on top of `0.1.0` but not yet cut into a tagged release. Granular history is in `git log`; this is a human-readable summary of the headline changes.

### Added
- **Order lifecycle and persistence** — Orders, plans, companies, NAICS associations, documents, and status history modeled with SQLAlchemy + Alembic migrations.
- **Full order-creation API flow** — Plan listing, order creation, company details + logo upload, industry intake questions, document preview generation.
- **Document generation** — DOCX template rendering via `python-docx`, preview generation, secure token-protected download. Templates: `basic_manual`, `comprehensive_manual`, `SJP-Template`.
- **Stripe Checkout integration** — Real Stripe payments (no more mocked phase-1 flow). Checkout session creation, webhook handler at `/api/v1/payments/webhook` that drives order status transitions, automatic document generation and email delivery on successful payment.
- **Email delivery** — SMTP sender with Jinja2 HTML templates (`document_delivery.html`, `sjp_delivery.html`, `otp_request.html`).
- **End-user authentication** — Email OTP + httpOnly session cookie, with per-email / per-IP rate limits and lockout.
- **User dashboard API** — `GET /orders`, `GET /orders/{id}`, document listing, expired-token refresh.
- **Admin API** — Separate admin auth, admin order management, admin stats. See `docs/ADMIN_API.md`.
- **SJP (Safe Job Procedure) generation** — Async LLM-powered generation pipeline using OpenAI, jurisdiction-specific prompt packs, table-of-contents + content generation, DB-backed job tracking, progress polling endpoint, auto-resume of stuck jobs on app startup. LLM usage logging for cost monitoring. See `docs/SJP_FRONTEND_GUIDE.md`.
- **Industry-specific standalone plan** — New plan type for customers who only want SJP content.
- **ngrok tunnel** added to `docker-compose.yml` so Stripe webhooks can reach a developer's laptop during development.
- **OpenAI configuration** — New required env var `OPENAI_API_KEY`, plus optional `LLM_*` tuning knobs.

### Changed
- **Required environment variables expanded** — `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `OPENAI_API_KEY`, and the SMTP quartet are now all required. `app/config.py` is the authoritative list.
- **Documentation formalized** — `README.md` rewritten as a lean router into `docs/`, `GETTING_STARTED.md` updated with full account-creation walkthrough, new `docs/TROUBLESHOOTING.md`, stale docs removed.

### Planned
- Production deployment configuration (currently no production stack is checked in)
- S3 file storage (toggle already exists as `USE_S3` but no implementation)

---

## [0.1.0] - 2026-01-26

### Added
- **Project Foundation Setup**
  - Complete directory structure following implementation plan
  - FastAPI application with modular architecture
  - Pydantic Settings for configuration management
  - Docker and docker-compose setup for local development
  - MySQL database service configuration
  - Health check endpoint (`GET /api/v1/health`)
  - Custom exception hierarchy for error handling
  - CORS middleware configuration
  - Automatic directory creation on startup
  
- **Configuration Management**
  - Environment-based configuration with Pydantic
  - `.env.example` with comprehensive documentation
  - Support for development, staging, and production environments
  - Type-safe settings with validation
  - Computed properties for common config patterns
  
- **Docker Infrastructure**
  - Multi-service docker-compose setup
  - Application container with Python 3.11
  - MySQL 8.0 database container with health checks
  - Volume mounting for local development
  - Hot reload support for development
  - Network isolation between services
  
- **Developer Documentation**
  - `GETTING_STARTED.md` - Onboarding guide for new developers
  - `PYTHON_BACKEND_CONCEPTS.md` - FastAPI and Python backend fundamentals
  - `ARCHITECTURE.md` - Detailed architecture and design patterns
  - Comprehensive README with setup instructions
  - Inline code comments and examples
  
- **Development Tools**
  - Python dependencies (FastAPI, SQLAlchemy, Pydantic, etc.)
  - Development dependencies (pytest, mypy, ruff, black)
  - `.gitignore` configuration for Python projects
  - `.dockerignore` for optimized Docker builds
  
- **Code Quality Setup**
  - Type hints on all functions
  - Pydantic models for validation
  - Custom exception handling
  - Consistent import organization
  - Fail-fast validation patterns

### Project Structure
```
ohs_remote/
├── app/                    # Main application package
│   ├── api/                # API endpoints
│   ├── core/               # Core utilities and exceptions
│   ├── services/           # Business logic (empty, ready for implementation)
│   ├── repositories/       # Data access (empty, ready for implementation)
│   ├── models/             # Database models (empty, ready for implementation)
│   ├── schemas/            # Pydantic schemas
│   ├── database/           # Database configuration (empty, ready for implementation)
│   ├── utils/              # Utility functions (empty, ready for implementation)
│   ├── config.py           # Settings management
│   └── main.py             # Application entry point
├── templates/              # Document and email templates
├── data/                   # Local file storage
├── tests/                  # Test suite (empty, ready for implementation)
├── docs/                   # Documentation
├── docker/                 # Docker configuration
└── scripts/                # Utility scripts (empty, ready for implementation)
```

### Development Environment
- **Python**: 3.11
- **FastAPI**: 0.109.0
- **Pydantic**: 2.5.3
- **SQLAlchemy**: 2.0.25
- **MySQL**: 8.0
- **Docker**: Multi-container setup with docker-compose

### Notes
This release establishes the foundational structure for the OHS Remote backend. All core patterns and architectural decisions are in place, ready for feature implementation.

**Next Steps:**
1. Set up database migrations with Alembic
2. Implement database models and schemas
3. Create order management endpoints
4. Implement document generation service

---

## Version History

- **0.1.0** - 2026-01-26 - Initial project foundation setup

---

## How to Read This Changelog

- **Added** - New features or functionality
- **Changed** - Changes to existing functionality
- **Deprecated** - Features marked for removal
- **Removed** - Features that have been removed
- **Fixed** - Bug fixes
- **Security** - Security-related changes

---

## Contributing

When making changes, update this changelog following these guidelines:

1. Add entry under **[Unreleased]** section
2. Use appropriate category (Added, Changed, Fixed, etc.)
3. Write clear, concise descriptions
4. Include relevant issue/PR numbers when applicable
5. Update version number when releasing

### Example Entry Format

```markdown
### Added
- Brief description of feature [#123](link-to-issue)
- Another feature with context and details

### Fixed
- Bug fix description [#456](link-to-issue)
```

---

## Release Process

1. Update version in changelog
2. Move unreleased changes to new version section
3. Add release date
4. Update version in [app/main.py](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/main.py:0:0-0:0)
5. Commit with message: "Release v{version}"
6. Create git tag: `git tag -a v{version} -m "Version {version}"`
7. Push with tags: `git push --follow-tags`
