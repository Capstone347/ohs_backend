# Project Architecture Guide

This document explains the architectural decisions and patterns used in the OHS Remote backend.

---

## Table of Contents

- [Architectural Overview](#architectural-overview)
- [Layered Architecture](#layered-architecture)
- [Design Patterns](#design-patterns)
- [Code Organization](#code-organization)
- [Configuration Management](#configuration-management)
- [Error Handling Strategy](#error-handling-strategy)
- [Security Considerations](#security-considerations)

---

## Architectural Overview

The OHS Remote backend follows a **layered architecture** with clear separation of concerns. Each layer has a specific responsibility and communicates only with adjacent layers.

```
┌─────────────────────────────────────┐
│     API Layer (FastAPI Routes)      │  ← HTTP Requests/Responses
├─────────────────────────────────────┤
│     Service Layer (Business Logic)  │  ← Orchestration & Rules
├─────────────────────────────────────┤
│     Repository Layer (Data Access)  │  ← Database Operations
├─────────────────────────────────────┤
│     Model Layer (Database Schema)   │  ← Table Definitions
└─────────────────────────────────────┘
```

### Why Layered Architecture?

**Separation of Concerns:**
Each layer has one job. API layer handles HTTP, services handle business logic, repositories handle data.

**Testability:**
Mock one layer to test another. Test business logic without touching the database.

**Maintainability:**
Change database? Only update repositories. Change business rules? Only update services.

**Scalability:**
Clear boundaries make it easy to extract services to separate microservices later.

---

## Layered Architecture

### 1. API Layer ([app/api/v1/endpoints](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/api/v1/endpoints:0:0-0:0))

**Responsibilities:**
- Handle HTTP requests and responses
- Validate input using Pydantic schemas
- Call service layer to perform operations
- Transform service responses to API format
- Handle HTTP-specific concerns (status codes, headers)

**What it should NOT do:**
- Business logic calculations
- Direct database access
- Complex validation beyond format checking

**Example:**
```python
@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    request: OrderCreateRequest,
    order_service: OrderService = Depends(get_order_service)
) -> OrderResponse:
    order = order_service.create_order(request)
    return OrderResponse.from_orm(order)
```

Notice:
- Thin endpoint (4 lines of logic)
- Delegates to service
- Returns typed response

### 2. Service Layer ([app/services](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/services:0:0-0:0))

**Responsibilities:**
- Implement business logic
- Validate business rules
- Orchestrate operations across multiple repositories
- Handle transaction boundaries
- Emit events or trigger side effects

**What it should NOT do:**
- Direct SQL queries or database operations
- HTTP-specific logic (status codes, headers)
- Parse request bodies or format responses

**Example:**
```python
class OrderService:
    def __init__(self, order_repo: OrderRepository, plan_repo: PlanRepository):
        self.order_repo = order_repo
        self.plan_repo = plan_repo
    
    def create_order(self, request: OrderCreateRequest) -> Order:
        # Business logic: Validate plan exists and is available
        plan = self.plan_repo.get_by_id(request.plan_id)
        if not plan:
            raise ValidationError(f"Plan {request.plan_id} not found")
        
        if not plan.is_available:
            raise ValidationError(f"Plan {request.plan_id} is not available")
        
        # Business logic: Calculate total amount
        total_amount = self._calculate_order_total(plan)
        
        # Create order via repository
        order = Order(
            user_email=request.user_email,
            plan_id=request.plan_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING
        )
        
        return self.order_repo.create(order)
```

Notice:
- No HTTP logic
- No direct database queries
- Validates business rules
- Orchestrates multiple operations

### 3. Repository Layer ([app/repositories](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/repositories:0:0-0:0))

**Responsibilities:**
- Abstract database operations
- Provide CRUD methods
- Execute queries and return models
- Handle database sessions
- Provide domain-specific queries

**What it should NOT do:**
- Business logic or validation
- Transform data formats (that's service layer)
- Handle HTTP concerns

**Example:**
```python
class OrderRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, order_id: int) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def get_by_user_email(self, email: str) -> list[Order]:
        return self.db.query(Order).filter(Order.user_email == email).all()
```

Notice:
- Pure database operations
- No business logic
- Returns ORM models

### 4. Model Layer ([app/models](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/models:0:0-0:0))

**Responsibilities:**
- Define database table structure
- Define relationships between tables
- Provide column constraints

**What it should NOT do:**
- Business logic
- Validation logic (that's in Pydantic schemas)
- Database operations (that's in repositories)

**Example:**
```python
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    total_amount = Column(Integer, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    
    # Relationships
    plan = relationship("Plan")
    documents = relationship("Document", back_populates="order")
```

---

## Design Patterns

### Repository Pattern

Abstracts data access behind an interface. Instead of scattering SQL queries throughout the codebase, centralize them in repositories.

**Benefits:**
- Easy to test (mock repositories)
- Easy to change database (rewrite repositories)
- Queries reusable across services

**Implementation:**
```python
# Base repository with common operations
class BaseRepository:
    def __init__(self, db: Session, model: Type[Base]):
        self.db = db
        self.model = model
    
    def get_by_id(self, id: int):
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self):
        return self.db.query(self.model).all()

# Specific repository extends base
class OrderRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, Order)
    
    def get_pending_orders(self):
        return self.db.query(Order).filter(Order.status == OrderStatus.PENDING).all()
```

### Dependency Injection

Functions receive dependencies as parameters rather than creating them. Enables testing and decouples components.

**Implementation:**
```python
# Dependency providers
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)

def get_order_service(repo: OrderRepository = Depends(get_order_repository)) -> OrderService:
    return OrderService(repo)

# Usage in endpoints
@router.post("/orders")
def create_order(
    request: OrderCreateRequest,
    service: OrderService = Depends(get_order_service)
):
    return service.create_order(request)
```

### Service Layer Pattern

Business logic lives in service classes, not in endpoints or repositories. Services orchestrate operations and enforce business rules.

**Benefits:**
- Reusable business logic
- Testable without HTTP layer
- Clear location for business rules

### Schema Pattern (Pydantic)

Define data contracts using Pydantic models. Separate concerns:
- **Request schemas** - What API accepts
- **Response schemas** - What API returns
- **ORM models** - Database structure

**Example:**
```python
# Request schema (API input)
class OrderCreateRequest(BaseModel):
    plan_id: str
    user_email: str

# Response schema (API output)
class OrderResponse(BaseModel):
    order_id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ORM model (database)
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    # ...
```

---

## Code Organization

### File Naming

Files are named after what they contain:
- `order_service.py` - OrderService class
- `order_repository.py` - OrderRepository class
- `orders.py` - Order-related endpoints

### Module Structure

Each module is self-contained:
```
app/services/
├── __init__.py
├── order_service.py
├── document_generation_service.py
├── email_service.py
└── payment_service.py
```

### Import Organization

Three groups, blank line separated:

```python
# Standard library
import json
from datetime import datetime, timezone

# Third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Local application
from app.config import settings
from app.models.order import Order
from app.services.order_service import OrderService
```

### Function Size

Keep functions small and focused:
- One function, one purpose
- If function is too long, extract helper functions
- Aim for functions readable in under 20 lines

**Example of extracting functions:**
```python
# Before - too long
def create_order(request):
    # Validate plan
    plan = db.query(Plan).filter(Plan.id == request.plan_id).first()
    if not plan:
        raise ValueError("Plan not found")
    
    # Calculate total
    total = plan.base_price
    if request.add_ons:
        for addon in request.add_ons:
            total += addon.price
    
    # Create order
    order = Order(plan_id=request.plan_id, total=total)
    db.add(order)
    db.commit()
    
    # Send email
    # ... 20 more lines

# After - extracted
def create_order(request: OrderCreateRequest) -> Order:
    plan = validate_and_get_plan(request.plan_id)
    total = calculate_order_total(plan, request.add_ons)
    order = persist_order(request, total)
    send_confirmation_email(order)
    return order
```

---

## Configuration Management

All configuration comes from environment variables, managed through Pydantic Settings.

### Config Structure ([app/config.py](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/config.py:0:0-0:0))

```python
class Settings(BaseSettings):
    # Required fields (no default)
    database_url: str = Field(...)
    secret_key: str = Field(...)
    
    # Optional fields (with defaults)
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    
    # Computed properties
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

# Single settings instance
settings = Settings()
```

### Environment-Specific Config

The repository ships two environment-file templates:

- `.env.example` — template for running the app **outside** Docker (unsupported, reference only).
- `.env.docker.example` — template for running the full stack via `docker-compose` (the supported path). Copy to `.env.docker` and fill in the required values.

For production, every required variable should be injected by your deployment platform's secret store. See [../GETTING_STARTED.md](../GETTING_STARTED.md) for the full first-run checklist.

### Usage

```python
from app.config import settings

# Access config
smtp_host = settings.smtp_host

# Environment checks
if settings.is_production:
    # Production-specific logic
    pass
```

### Validation

Pydantic validates on application startup. If required config is missing, app fails immediately with clear error:

```
ValidationError: 1 validation error for Settings
database_url
  field required (type=value_error.missing)
```

This follows the **fail fast** principle - catch configuration errors before any request is processed.

---

## Error Handling Strategy

### Exception Hierarchy

Define custom exceptions for different error types:

```python
class OHSRemoteException(Exception):
    """Base exception for all application errors"""
    pass

class ValidationError(OHSRemoteException):
    """User input validation failed"""
    pass

class OrderNotFoundError(OHSRemoteException):
    """Order does not exist"""
    pass
```

### Where to Raise

Raise exceptions close to where error is detected:

```python
def get_order(order_id: str) -> Order:
    if not order_id:
        raise ValueError("order_id is required")
    
    order = order_repository.get(order_id)
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    
    return order
```

### Where to Catch

Catch exceptions at API layer only:

```python
@app.exception_handler(OrderNotFoundError)
async def order_not_found_handler(request: Request, exc: OrderNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "ORDER_NOT_FOUND", "message": str(exc)}}
    )
```

### Let Exceptions Bubble

Don't catch exceptions in services or repositories - let them bubble to API layer:

```python
# Bad - catches too early
def create_order(request):
    try:
        return order_service.create(request)
    except Exception as e:
        return {"error": str(e)}  # Lost type information!

# Good - let it bubble
def create_order(request):
    return order_service.create(request)  # Exception handled by FastAPI
```

---

## Security Considerations

### Input Validation

All input validated at API boundary using Pydantic schemas. Never trust user input.

### SQL Injection Prevention

Use SQLAlchemy ORM, never raw SQL with string concatenation:

```python
# Vulnerable to SQL injection
query = f"SELECT * FROM orders WHERE id = {order_id}"

# Safe with ORM
order = db.query(Order).filter(Order.id == order_id).first()
```

### Authentication & Authorization

The backend uses an **email OTP + session cookie** scheme for end users:

1. `POST /api/v1/auth/request-otp` sends a one-time code to the user's email via SMTP.
2. `POST /api/v1/auth/verify-otp` verifies the code and sets an httpOnly `auth_session` cookie.
3. Protected endpoints (e.g. `GET /api/v1/orders` for the user dashboard) read the cookie on every request.

Rate limits on OTP request and verify are enforced by config knobs in `app/config.py` (`auth_otp_*`).

The unauthenticated part of the order-creation flow is public on purpose — see [API_OVERVIEW.md](API_OVERVIEW.md) for the full list of which endpoints require a session. Admin endpoints use a separate auth flow documented in [ADMIN_API.md](ADMIN_API.md).

### Secrets Management

Never commit secrets to version control:
- Use `.env` file (gitignored)
- In production, use secret management service (AWS Secrets Manager, etc.)

### CORS Configuration

Restrict allowed origins to known frontend URLs:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Never use ["*"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## Summary

**Layered Architecture:**
- Clear separation between API, services, repositories, and models
- Each layer has specific responsibilities

**Design Patterns:**
- Repository pattern for data access
- Dependency injection for testability
- Service layer for business logic

**Configuration:**
- Pydantic Settings for type-safe config
- Environment variables for all configuration
- Fail fast on missing required config

**Error Handling:**
- Custom exception hierarchy
- Raise early, catch late
- Consistent error response format

**Security:**
- Input validation with Pydantic
- ORM for SQL injection prevention
- Secrets in environment variables

This architecture provides a solid foundation that scales from MVP to production while maintaining code quality and testability.
