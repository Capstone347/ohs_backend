# AI Coding Agent Instructions - OHS Remote Backend

This document guides AI coding agents in contributing effectively to the OHS Remote backend codebase.

## Project Overview

**OHS Remote** is a FastAPI-based backend for a Health & Safety compliance manual generation platform. It handles order management, document generation, payment processing (Stripe), and email delivery. The system targets small to medium-sized businesses needing customized OHS manuals.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, MySQL 8.0, Alembic migrations, Pydantic 2.0

---

## Architecture Principles

The codebase strictly follows **4-layer architecture** with clear separation of concerns. **This is non-negotiable.**

```
API Layer (endpoints) → Service Layer (business logic) → Repository Layer (data) → Models (schema)
```

### Layer Responsibilities

**API Layer** ([app/api/v1/endpoints/](app/api/v1/endpoints/))
- Handle HTTP requests/responses only
- Validate input with Pydantic schemas
- Call services (never touch database directly)
- Keep endpoints thin (3-5 lines logic)
- Example: [app/api/v1/endpoints/health.py](app/api/v1/endpoints/health.py)

**Service Layer** ([app/services/](app/services/))
- Implement business logic and validation
- Orchestrate across multiple repositories
- Handle transaction boundaries
- Raise domain-specific exceptions
- **Never** touch FastAPI/HTTP concepts

**Repository Layer** ([app/repositories/](app/repositories/))
- Pure CRUD operations and queries
- Return SQLAlchemy ORM models
- Handle database sessions
- **Never** contain business logic

**Model Layer** ([app/models/](app/models/))
- SQLAlchemy table definitions only
- Enums for status types → extract to [app/core/enums.py](app/core/enums.py)
- Relationships and constraints
- Example: [app/models/user.py](app/models/user.py)

---

## Critical Patterns

### Exception Handling

Use domain-specific exceptions from [app/core/exceptions.py](app/core/exceptions.py):

```python
from app.core.exceptions import ValidationError, OrderNotFoundError

# In service layer - raise domain exceptions
if not order:
    raise OrderNotFoundError(f"Order {order_id} not found")

# In endpoint - FastAPI auto-converts OHSRemoteException to 400 status
@app.exception_handler(OHSRemoteException)
async def handler(request, exc):
    return JSONResponse(status_code=400, content={"error": {...}})
```

### Dependency Injection

FastAPI's `Depends()` provides services to endpoints:

```python
# Endpoint receives service instance
@router.post("/orders")
def create_order(
    request: OrderCreateRequest,
    order_service: OrderService = Depends(get_order_service)
):
    return order_service.create_order(request)
```

Create provider functions in `app/dependencies.py` (if needed). See [app/main.py](app/main.py) for lifespan management.

### Pydantic Schemas

- **Request schemas** in [app/schemas/](app/schemas/) validate input
- **Response schemas** define API output
- Use `ConfigDict(from_attributes=True)` for ORM model conversion
- Reference: [app/schemas/common.py](app/schemas/common.py)

---

## Development Workflow

### Database Migrations

Always use Alembic for schema changes:

```bash
# Create migration
alembic revision --autogenerate -m "describe change"

# Apply migration
alembic upgrade head
```

Migrations live in [alembic/versions/](alembic/versions/). Review auto-generated migrations for accuracy.

### Testing

**Run tests:**
```bash
pytest                    # All tests with coverage
pytest tests/unit        # Unit tests only
pytest -v --tb=short    # Verbose output
```

**Test structure:**
- [tests/unit/](tests/unit/) - service/repo tests (mock database)
- [tests/integration/](tests/integration/) - endpoint tests (real TestClient)
- Use [tests/conftest.py](tests/conftest.py) fixtures

**Configuration** in [pyproject.toml](pyproject.toml):
- Coverage threshold: see `addopts`
- Type checking: mypy strict mode enabled
- Linting: Ruff with isort integration

### Running Locally

**Option 1: Docker (recommended for database)**
```bash
docker-compose up -d
# App runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

**Option 2: Local + Docker database**
```bash
# Start database
docker-compose up mysql -d

# Run app locally with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Environment variables in `.env` file (see [app/config.py](app/config.py) for all settings).

---

## Code Organization Standards

### Imports
- **First-party imports** use absolute paths: `from app.services import OrderService`
- Configured in [pyproject.toml](pyproject.toml): `known-first-party = ["app"]`
- Ruff auto-sorts imports on save

### File Naming
- Models: singular (`user.py`, not `users.py`)
- Services: `{entity}_service.py`
- Repositories: `{entity}_repository.py`
- Endpoints: descriptive plural (`orders.py`, `documents.py`)

### Type Hints
- **Mandatory:** All functions must have return type hints (mypy strict mode)
- Use `Optional[T]` or `T | None` (Python 3.10+)
- Use `list[T]` instead of `List[T]`

### Configuration
All environment-based settings in [app/config.py](app/config.py) using `pydantic-settings`. Access via:
```python
from app.config import settings
settings.database_url
settings.max_logo_size_mb
```

---

## Common Tasks

### Adding a New Endpoint

1. Create schema in [app/schemas/](app/schemas/): `OrderCreateRequest`, `OrderResponse`
2. Create service method in `app/services/{entity}_service.py`
3. Create repository method in `app/repositories/{entity}_repository.py`
4. Add endpoint in `app/api/v1/endpoints/{entity}.py`, register in [app/api/v1/router.py](app/api/v1/router.py)
5. Add tests in `tests/unit/services/` and `tests/integration/`
6. If schema changes: `alembic revision --autogenerate -m "add field"`

### Adding a New Service

- Inject dependencies via `__init__`
- Raise domain exceptions from [app/core/exceptions.py](app/core/exceptions.py)
- Keep methods focused: one responsibility per method
- Example structure:
  ```python
  class OrderService:
      def __init__(self, order_repo: OrderRepository, payment_repo: PaymentRepository):
          self.order_repo = order_repo
          self.payment_repo = payment_repo
      
      def create_order(self, request: OrderCreateRequest) -> Order:
          # Validate, orchestrate, return
  ```

### External Integrations

- **Stripe**: [app/services/](app/services/) contains payment service
- **Email (SMTP)**: Jinja2 templates configured in settings
- **Document Generation**: python-docx for .docx files
- **File Storage**: Local or S3 (configured via `use_s3` setting)

---

## Validation & Quality

### Before Committing
```bash
# Format and lint
ruff format .
ruff check . --fix

# Type check
mypy app/

# Test with coverage
pytest --cov=app --cov-report=term-missing

# Check for unused imports
python -m ruff check . --select=F401
```

### Error Recovery

1. **Tests fail**: Run specific test with `-vv` flag for detailed output
2. **Migration issues**: Check [alembic/env.py](alembic/env.py) and `alembic current`
3. **Import errors**: Ensure absolute paths use `app.` prefix; run Ruff import check
4. **Type errors**: Run `mypy app/` to see all violations

---

## What NOT to Do

❌ **Don't** put business logic in endpoints  
❌ **Don't** do direct database queries outside repositories  
❌ **Don't** mix HTTP concerns with service logic  
❌ **Don't** use relative imports  
❌ **Don't** skip type hints  
❌ **Don't** bypass Alembic for schema changes  
❌ **Don't** add dependencies without updating requirements.txt and pyproject.toml  

---

## File Reference

| File | Purpose |
|------|---------|
| [app/main.py](app/main.py) | FastAPI app setup, middleware, exception handlers |
| [app/config.py](app/config.py) | Environment settings (all external config here) |
| [app/core/exceptions.py](app/core/exceptions.py) | Domain-specific exceptions |
| [app/database/session.py](app/database/session.py) | Database session management |
| [app/schemas/common.py](app/schemas/common.py) | Shared Pydantic models |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed architectural rationale |
| [pyproject.toml](pyproject.toml) | Dependencies, linting, testing config |
| [alembic.ini](alembic.ini) | Database migration settings |

---

## Questions to Ask Before Coding

- [ ] Does this belong in a service (business logic) or endpoint (HTTP)?
- [ ] Will this need a database migration?
- [ ] Are all functions type-hinted?
- [ ] Is this operation testable without hitting the database?
- [ ] Do I need a new schema, repository, or service?
- [ ] Have I reviewed the relevant layer pattern?
