# Understanding FastAPI and Python Backend Development

This guide explains key concepts used in the OHS Remote backend for developers new to Python backend development.

---

## Table of Contents

- [What is FastAPI?](#what-is-fastapi)
- [Python Type Hints](#python-type-hints)
- [Pydantic Models](#pydantic-models)
- [Dependency Injection](#dependency-injection)
- [Async vs Sync](#async-vs-sync)
- [Database with SQLAlchemy](#database-with-sqlalchemy)
- [API Design Patterns](#api-design-patterns)
- [Error Handling](#error-handling)
- [Testing](#testing)

---

## What is FastAPI?

FastAPI is a modern Python web framework for building APIs. It's similar to Express.js (Node.js) or Flask, but with automatic validation and documentation.

### Key Features

**Automatic API Documentation:**
Visit `/docs` and you get interactive API documentation for free. No need to write OpenAPI specs manually.

**Automatic Validation:**
Define what data you expect with Pydantic models, and FastAPI validates it automatically.

**Type Safety:**
Uses Python type hints for editor autocomplete and error detection before runtime.

**Performance:**
Built on Starlette and Pydantic, it's one of the fastest Python frameworks.

### Simple Example

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.post("/items")
def create_item(item: Item):
    return {"message": f"Created {item.name} for ${item.price}"}
```

That's it! FastAPI will:
- Validate that `name` is a string and `price` is a float
- Return 422 error if validation fails
- Generate API docs showing the expected format

---

## Python Type Hints

Type hints tell Python (and your editor) what type a variable should be. They don't enforce types at runtime, but provide excellent developer experience.

### Basic Types

```python
# Simple types
name: str = "John"
age: int = 25
price: float = 19.99
is_active: bool = True

# Collections
names: list[str] = ["Alice", "Bob"]
scores: dict[str, int] = {"Alice": 95, "Bob": 87}

# Optional values
email: str | None = None  # Can be string or None
```

### Function Signatures

```python
def calculate_total(items: list[OrderItem], tax_rate: float) -> float:
    subtotal = sum(item.price * item.quantity for item in items)
    return subtotal * (1 + tax_rate)
```

This clearly shows:
- `items` must be a list of OrderItem objects
- `tax_rate` must be a float
- Function returns a float

### Why Type Hints Matter

**Editor Autocomplete:**
Your editor knows what methods are available on typed objects.

**Early Error Detection:**
Type checker (mypy) catches errors before running code.

**Self-Documenting:**
Function signature shows exactly what it expects and returns.

**Refactoring Safety:**
When you change a type, your editor shows all places that need updating.

---

## Pydantic Models

Pydantic is a data validation library. Think of it as defining a contract for what data should look like.

### Basic Model

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=18, le=120)
```

This model:
- Validates email format with regex
- Ensures name is 1-100 characters
- Ensures age is between 18 and 120

### Validation Example

```python
# Valid data
user = User(
    email="john@example.com",
    full_name="John Doe",
    age=25
)

# Invalid data - raises ValidationError
user = User(
    email="not-an-email",  # Fails regex
    full_name="",  # Too short
    age=200  # Too high
)
```

### In FastAPI Endpoints

```python
@router.post("/users")
def create_user(user: User):
    # By the time we're here, FastAPI has validated:
    # - email format is correct
    # - full_name is 1-100 chars
    # - age is 18-120
    return {"message": f"Created user {user.email}"}
```

If validation fails, FastAPI automatically returns:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "string does not match regex pattern",
      "type": "value_error.str.regex"
    }
  ]
}
```

### Advanced Features

**Nested Models:**
```python
class Address(BaseModel):
    street: str
    city: str
    postal_code: str

class Company(BaseModel):
    name: str
    address: Address
```

**Validators:**
```python
from pydantic import validator

class Order(BaseModel):
    quantity: int
    
    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('quantity must be positive')
        return v
```

**Config Options:**
```python
class Order(BaseModel):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # Works with SQLAlchemy models
```

---

## Dependency Injection

Dependency injection is a pattern where functions receive their dependencies as parameters rather than creating them internally.

### Without Dependency Injection (Bad)

```python
@router.get("/orders/{order_id}")
def get_order(order_id: str):
    # Creates dependencies inside function
    db = create_db_connection()
    repository = OrderRepository(db)
    order = repository.get(order_id)
    return order
```

Problems:
- Hard to test (can't mock database)
- Repeated code in every endpoint
- Tight coupling to database implementation

### With Dependency Injection (Good)

```python
def get_order_repository() -> OrderRepository:
    db = create_db_connection()
    return OrderRepository(db)

@router.get("/orders/{order_id}")
def get_order(
    order_id: str,
    repository: OrderRepository = Depends(get_order_repository)
):
    order = repository.get(order_id)
    return order
```

Benefits:
- Easy to test (inject mock repository)
- No repeated setup code
- Can change implementation in one place

### Testing with DI

```python
def test_get_order():
    # Create mock repository
    mock_repo = MockOrderRepository()
    mock_repo.get = lambda id: Order(id=id, status="pending")
    
    # Inject mock
    response = get_order("123", repository=mock_repo)
    
    assert response.id == "123"
```

### Dependency Hierarchy

Dependencies can depend on other dependencies:

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)

def get_order_service(
    repo: OrderRepository = Depends(get_order_repository)
) -> OrderService:
    return OrderService(repo)

@router.post("/orders")
def create_order(
    request: OrderCreateRequest,
    service: OrderService = Depends(get_order_service)
):
    return service.create_order(request)
```

FastAPI automatically resolves the dependency chain:
1. Creates database session
2. Creates repository with session
3. Creates service with repository
4. Injects service into endpoint

---

## Async vs Sync

Python supports both synchronous (blocking) and asynchronous (non-blocking) code.

### Synchronous (Sync)

```python
@router.get("/orders/{order_id}")
def get_order(order_id: str):
    # This blocks until query completes
    order = db.query(Order).filter(Order.id == order_id).first()
    return order
```

While waiting for database, this thread does nothing. If many requests come in, you need many threads.

### Asynchronous (Async)

```python
@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    # This yields control while waiting
    order = await db.get(Order, order_id)
    return order
```

While waiting for database, this can handle other requests. One thread can handle many concurrent requests.

### When to Use Each

**Use `def` (sync) when:**
- Using sync libraries (like most SQLAlchemy operations)
- Doing CPU-intensive work (document generation)
- Simple CRUD operations with no external calls

**Use `async def` when:**
- Making external API calls
- Using async database drivers
- File I/O operations
- Multiple concurrent operations

### Important Rule

**Never block in async functions:**

```python
# BAD - blocks the event loop
async def bad_endpoint():
    time.sleep(5)  # Blocks entire server!
    return "done"

# GOOD - yields control
async def good_endpoint():
    await asyncio.sleep(5)  # Other requests can be processed
    return "done"
```

### Our Approach

In OHS Remote, we use sync for most operations because:
- SQLAlchemy (our ORM) is primarily synchronous
- Document generation is CPU-bound
- Simpler code for team to understand

We use async only for:
- Email sending (aiosmtplib)
- External API calls (httpx with async)

---

## Database with SQLAlchemy

SQLAlchemy is an ORM (Object-Relational Mapper) that lets you work with databases using Python objects instead of SQL strings.

### Models Define Tables

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
```

This creates the `orders` table with those columns.

### CRUD Operations

**Create:**
```python
order = Order(
    user_email="john@example.com",
    status="pending",
    created_at=datetime.now(timezone.utc)
)
db.add(order)
db.commit()
db.refresh(order)  # Get generated ID
```

**Read:**
```python
# Get by ID
order = db.query(Order).filter(Order.id == 123).first()

# Get all
orders = db.query(Order).all()

# Filter
pending_orders = db.query(Order).filter(Order.status == "pending").all()
```

**Update:**
```python
order = db.query(Order).filter(Order.id == 123).first()
order.status = "paid"
db.commit()
```

**Delete:**
```python
order = db.query(Order).filter(Order.id == 123).first()
db.delete(order)
db.commit()
```

### Relationships

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    orders = relationship("Order", back_populates="user")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="orders")

# Access related data
user = db.query(User).first()
user_orders = user.orders  # SQLAlchemy loads related orders
```

### Repository Pattern

We wrap SQLAlchemy operations in repository classes:

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
```

This provides:
- Abstraction over database operations
- Easier testing (mock repositories)
- Centralized query logic

---

## API Design Patterns

### RESTful Conventions

**Resource-based URLs:**
```
GET    /api/v1/orders          # List orders
POST   /api/v1/orders          # Create order
GET    /api/v1/orders/123      # Get specific order
PATCH  /api/v1/orders/123      # Update order
DELETE /api/v1/orders/123      # Delete order
```

**Use HTTP Methods Correctly:**
- `GET` - Retrieve data (no side effects)
- `POST` - Create new resource
- `PATCH` - Partial update
- `PUT` - Full replacement
- `DELETE` - Remove resource

**Status Codes:**
- `200 OK` - Successful GET/PATCH/DELETE
- `201 Created` - Successful POST
- `400 Bad Request` - Validation error
- `404 Not Found` - Resource doesn't exist
- `500 Internal Server Error` - Server error

### Request/Response Pattern

```python
# Request model
class OrderCreateRequest(BaseModel):
    plan_id: str
    user_email: str

# Response model
class OrderResponse(BaseModel):
    order_id: str
    status: str
    created_at: datetime

# Endpoint
@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(request: OrderCreateRequest) -> OrderResponse:
    order = order_service.create_order(request)
    return OrderResponse.from_orm(order)
```

### Error Response Format

All errors follow consistent structure:

```json
{
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "Order 123 does not exist"
  }
}
```

### Pagination

For list endpoints:

```python
class PaginatedResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int

@router.get("/orders", response_model=PaginatedResponse)
def list_orders(page: int = 1, page_size: int = 20):
    # Implementation
    pass
```

---

## Error Handling

### Exception Hierarchy

Define domain-specific exceptions:

```python
class OHSRemoteException(Exception):
    """Base exception"""
    pass

class ValidationError(OHSRemoteException):
    """Invalid input data"""
    pass

class OrderNotFoundError(OHSRemoteException):
    """Order doesn't exist"""
    pass
```

### Raising Exceptions

```python
def get_order(order_id: str) -> Order:
    if not order_id:
        raise ValueError("order_id is required")
    
    order = order_repository.get(order_id)
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    
    return order
```

### Handling at API Level

```python
@app.exception_handler(OrderNotFoundError)
async def order_not_found_handler(request: Request, exc: OrderNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "ORDER_NOT_FOUND",
                "message": str(exc)
            }
        }
    )
```

### Never Catch Too Broadly

```python
# BAD - hides all errors
try:
    process_order()
except Exception:
    pass

# GOOD - catch specific errors
try:
    process_order()
except OrderNotFoundError:
    # Handle missing order
    pass
except PaymentProcessingError:
    # Handle payment failure
    pass
# Let other exceptions bubble up
```

---

## Testing

### Test Structure

```python
import pytest
from fastapi.testclient import TestClient

def test_create_order_success():
    # Arrange - set up test data
    client = TestClient(app)
    request_data = {
        "plan_id": "basic",
        "user_email": "test@example.com"
    }
    
    # Act - perform the operation
    response = client.post("/api/v1/orders", json=request_data)
    
    # Assert - verify results
    assert response.status_code == 201
    data = response.json()
    assert "order_id" in data
    assert data["status"] == "pending"
```

### Unit Tests

Test individual functions in isolation:

```python
def test_calculate_total():
    items = [
        OrderItem(price=10.00, quantity=2),
        OrderItem(price=5.00, quantity=3)
    ]
    
    total = calculate_total(items)
    
    assert total == 35.00  # (10*2) + (5*3)
```

### Integration Tests

Test multiple components together:

```python
def test_order_creation_flow(db_session):
    # Create order
    order = order_service.create_order(request_data)
    
    # Verify in database
    db_order = db_session.query(Order).filter(Order.id == order.id).first()
    assert db_order is not None
    assert db_order.status == "pending"
```

### Mocking

Replace real dependencies with test doubles:

```python
from unittest.mock import Mock

def test_order_service_with_mock():
    # Create mock repository
    mock_repo = Mock()
    mock_repo.create.return_value = Order(id=123, status="pending")
    
    # Inject mock
    service = OrderService(order_repo=mock_repo)
    
    # Test
    order = service.create_order(request_data)
    
    # Verify mock was called
    mock_repo.create.assert_called_once()
```

### Fixtures

Reusable test setup:

```python
@pytest.fixture
def test_db():
    # Setup
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    
    yield session
    
    # Teardown
    session.close()

def test_with_fixture(test_db):
    # test_db is automatically provided
    order = Order(user_email="test@example.com")
    test_db.add(order)
    test_db.commit()
```

---

## Summary

**FastAPI:**
- Modern framework with automatic validation and docs
- Built on type hints and Pydantic

**Type Hints:**
- Document what types functions expect
- Enable autocomplete and early error detection

**Pydantic:**
- Validate data using Python classes
- Automatic error messages for invalid data

**Dependency Injection:**
- Functions receive dependencies as parameters
- Makes testing easy and reduces coupling

**SQLAlchemy:**
- Work with databases using Python objects
- Abstracts SQL queries behind ORM

**Testing:**
- Unit tests for individual functions
- Integration tests for component interaction
- Mock external dependencies

Ready to dive deeper? Check out the official documentation:
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
