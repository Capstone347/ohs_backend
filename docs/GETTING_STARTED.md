# Getting Started with OHS Remote Backend

Welcome to the OHS Remote backend project! This guide will help you understand the project structure and get your development environment set up.

---

## Table of Contents

- [What is OHS Remote?](#what-is-ohs-remote)
- [Quick Start](#quick-start)
- [Understanding the Project Structure](#understanding-the-project-structure)
- [Key Concepts](#key-concepts)
- [Your First Changes](#your-first-changes)
- [Common Development Tasks](#common-development-tasks)
- [Getting Help](#getting-help)

---

## What is OHS Remote?

OHS Remote is a web application that generates customized Health & Safety compliance manuals for businesses. Think of it as a document generator that:

1. Takes company information (name, logo, industry codes)
2. Applies it to professional templates
3. Generates branded, downloadable safety manuals

The backend (what you're working on) handles:
- **API endpoints** - Frontend talks to these
- **Database operations** - Store and retrieve data
- **Document generation** - Create the actual manuals
- **Payment processing** - Handle Stripe payments
- **Email delivery** - Send documents to customers

---

## Quick Start

### Prerequisites

Make sure you have installed:
- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)
- **Git** - [Download here](https://git-scm.com/downloads)
- **VS Code** (recommended) - [Download here](https://code.visualstudio.com/)

### Setup Steps

1. **Clone the repository** (if you haven't already)
   ```bash
   cd ~/Developer/University
   git clone <repository-url> ohs_remote
   cd ohs_remote
   ```

2. **Create your environment file**
   ```bash
   cp .env.example .env
   ```
   
   For now, the defaults work fine for local development. You'll need to update SMTP settings later if you want to test email functionality.

3. **Start the application**
   ```bash
   docker-compose up
   ```
   
   This will:
   - Download MySQL database image
   - Build the FastAPI application
   - Start both services
   - Run database migrations
   
   **First run takes 3-5 minutes** as Docker downloads images.

4. **Verify it's working**
   
   Open your browser and visit:
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health
   
   You should see the Swagger UI (interactive API documentation) and a JSON response with `"status": "healthy"`.

### Stopping the Application

```bash
# Stop with Ctrl+C in the terminal, or:
docker-compose down
```

---

## Understanding the Project Structure

The project follows a **layered architecture** - think of it like a cake with distinct layers, each with its own responsibility.

```
ohs_remote/
├── app/                    # Main application code
│   ├── api/                # API endpoints (what the frontend calls)
│   ├── services/           # Business logic (the "brain" of operations)
│   ├── repositories/       # Database access (talks to MySQL)
│   ├── models/             # Database table definitions
│   ├── schemas/            # Request/response formats (Pydantic models)
│   ├── core/               # Shared utilities (errors, security)
│   ├── config.py           # Application settings
│   └── main.py             # Application entry point
├── templates/              # Document and email templates
├── data/                   # Local file storage (gitignored)
├── tests/                  # Test suite
├── docker/                 # Docker configuration
└── docs/                   # Documentation
```

### The Layers Explained

Think of a customer order flowing through the system:

1. **API Layer** ([app/api/v1/endpoints](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/api/v1/endpoints:0:0-0:0))
   - Receives HTTP requests from frontend
   - Validates input using Pydantic schemas
   - Calls service layer to do the work
   - Returns HTTP responses
   
   **Example:** `POST /api/v1/orders` endpoint receives order creation request

2. **Service Layer** ([app/services](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/services:0:0-0:0))
   - Contains business logic
   - Orchestrates operations across multiple repositories
   - Validates business rules
   - No direct database access
   
   **Example:** `OrderService` validates order data, checks plan availability, calculates total

3. **Repository Layer** ([app/repositories](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/repositories:0:0-0:0))
   - Abstracts database operations
   - CRUD operations (Create, Read, Update, Delete)
   - Custom queries for specific needs
   
   **Example:** `OrderRepository.create()` inserts order into database

4. **Models** ([app/models](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/models:0:0-0:0))
   - Define database tables using SQLAlchemy
   - Relationships between tables
   - Used only by repositories
   
   **Example:** `Order` model defines orders table structure

5. **Schemas** ([app/schemas](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/schemas:0:0-0:0))
   - Define API request and response formats
   - Automatic validation using Pydantic
   - Type safety and documentation
   
   **Example:** `OrderCreateRequest` validates incoming order data

---

## Key Concepts

### 1. Pydantic for Validation

Pydantic is a library that validates data using Python type hints. It's like having a contract for what data should look like.

**Example:**
```python
from pydantic import BaseModel, Field

class OrderCreateRequest(BaseModel):
    plan_id: str
    user_email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    company_name: str = Field(..., min_length=1)
```

This says:
- `plan_id` must be a string
- `user_email` must match email pattern
- `company_name` must be at least 1 character

If someone sends invalid data, Pydantic automatically returns a 422 error with details.

### 2. Dependency Injection

FastAPI has a powerful dependency injection system. Think of it like automatically getting tools you need.

**Example:**
```python
from fastapi import Depends

def get_order_service() -> OrderService:
    return OrderService(order_repository=OrderRepository())

@router.post("/orders")
def create_order(
    request: OrderCreateRequest,
    order_service: OrderService = Depends(get_order_service)
):
    return order_service.create_order(request)
```

FastAPI automatically calls `get_order_service()` and passes the result to your endpoint function.

### 3. Type Hints

Python 3.11+ has excellent type hints. We use them everywhere for clarity and error prevention.

**Example:**
```python
def calculate_total(items: list[OrderItem]) -> Decimal:
    return sum(item.price * item.quantity for item in items)
```

This clearly shows:
- Input: list of OrderItem objects
- Output: Decimal number

Your IDE will warn you if you pass wrong types!

### 4. Fail Fast Principle

Always validate inputs before processing. If something is wrong, raise an error immediately.

**Good:**
```python
def process_order(order_id: str) -> Order:
    if not order_id:
        raise ValueError("order_id is required")
    
    order = order_repository.get(order_id)
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    
    # Now safe to process
    return finalize_order(order)
```

**Bad:**
```python
def process_order(order_id: str) -> Order:
    # Start processing without checks
    order = order_repository.get(order_id)
    # Fails later with cryptic error if order_id was None
```

### 5. Environment-Based Configuration

All configuration comes from environment variables (`.env` file). Never hardcode secrets or URLs.

**Example:**
```python
from app.config import settings

# Good - uses config
smtp_host = settings.smtp_host

# Bad - hardcoded
smtp_host = "smtp.gmail.com"
```

---

## Your First Changes

Let's walk through adding a simple endpoint to practice the flow.

### Task: Add a "ping" endpoint

**Goal:** Create `GET /api/v1/ping` that returns `{"message": "pong"}`

**Step 1: Create response schema**

Create [app/schemas/common.py](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/schemas/common.py:0:0-0:0) (if it doesn't exist):
```python
from pydantic import BaseModel

class PingResponse(BaseModel):
    message: str
```

**Step 2: Create endpoint**

Edit [app/api/v1/endpoints/health.py](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/api/v1/endpoints/health.py:0:0-0:0):
```python
@router.get("/ping", response_model=PingResponse)
def ping() -> PingResponse:
    return PingResponse(message="pong")
```

**Step 3: Test it**

1. Restart the application: `docker-compose restart app`
2. Visit: http://localhost:8000/docs
3. Find the `/api/v1/ping` endpoint
4. Click "Try it out" → "Execute"
5. You should see: `{"message": "pong"}`

**Congratulations! You just created your first endpoint!**

---

## Common Development Tasks

### View Application Logs

```bash
# Follow logs in real-time
docker-compose logs -f app

# View last 100 lines
docker-compose logs --tail=100 app
```

### Access MySQL Database

```bash
# Connect to MySQL
docker-compose exec mysql mysql -u ohs_user -pohs_password ohs_remote

# List tables
SHOW TABLES;

# View table structure
DESCRIBE orders;

# Exit MySQL
EXIT;
```

### Run Database Migrations

```bash
# Apply all pending migrations
docker-compose exec app alembic upgrade head

# Rollback last migration
docker-compose exec app alembic downgrade -1

# Create new migration
docker-compose exec app alembic revision -m "add new table"
```

### Run Tests

```bash
# Run all tests
docker-compose exec app pytest

# Run with coverage
docker-compose exec app pytest --cov=app

# Run specific test file
docker-compose exec app pytest tests/api/test_health.py
```

### Restart Application

```bash
# Restart just the app (after code changes)
docker-compose restart app

# Rebuild and restart (after dependency changes)
docker-compose up --build
```

### Clean Everything

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (deletes database data!)
docker-compose down -v
```

---

## Getting Help

### Documentation

- **README.md** - Project overview and setup
- **PLAN.md** - Detailed implementation plan
- **coding_guide.instructions.md** - Coding standards

### API Documentation

Visit http://localhost:8000/docs when the app is running for:
- Complete endpoint list
- Request/response schemas
- Interactive testing

### Common Issues

**Port already in use:**
```
ERROR: port is already allocated
```
Solution: Stop other applications using port 8000 or 3306

**Database connection failed:**
```
Can't connect to MySQL server
```
Solution: Wait for MySQL to fully start (takes ~30 seconds on first run)

**Module not found:**
```
ModuleNotFoundError: No module named 'app'
```
Solution: Rebuild container: `docker-compose up --build`

### Ask Questions

- Check existing documentation first
- Review similar code in the codebase
- Ask team members in Slack/Discord
- Create GitHub issues for bugs

---

## Next Steps

Now that you understand the basics:

1. **Explore the codebase** - Look at existing endpoints and services
2. **Read the coding guide** - Learn our standards and best practices
3. **Pick a task** - Start with small, well-defined tasks
4. **Write tests** - Test-driven development is encouraged
5. **Ask questions** - No question is too small!

Welcome to the team! 🚀
