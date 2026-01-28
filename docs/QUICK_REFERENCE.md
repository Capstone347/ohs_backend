# Quick Reference Guide

Quick commands and tips for daily development on OHS Remote backend.

---

## Daily Workflow

```bash
# 1. Start your day
cd ~/Developer/University/ohs_remote
docker-compose up

# 2. View API docs
open http://localhost:8000/docs

# 3. Make code changes
# Files auto-reload - no restart needed!

# 4. Run tests before committing
docker-compose exec app pytest

# 5. End your day
docker-compose down
```

---

## Essential Commands

### Application

```bash
# Start application
docker-compose up

# Start in background
docker-compose up -d

# Stop application
docker-compose down

# Restart after dependency change
docker-compose up --build

# View logs
docker-compose logs -f app

# Access container shell
docker-compose exec app bash
```

### Testing

```bash
# Run all tests
docker-compose exec app pytest

# Run with coverage
docker-compose exec app pytest --cov=app

# Run specific test file
docker-compose exec app pytest tests/api/test_health.py

# Run tests matching pattern
docker-compose exec app pytest -k "test_health"
```

### Database

```bash
# Access MySQL
docker-compose exec mysql mysql -u ohs_user -pohs_password ohs_remote

# Run migrations
docker-compose exec app alembic upgrade head

# Rollback migration
docker-compose exec app alembic downgrade -1

# Create new migration
docker-compose exec app alembic revision -m "description"

# Check migration status
docker-compose exec app alembic current
```

### Code Quality

```bash
# Run linter
docker-compose exec app ruff check app/

# Auto-fix linting issues
docker-compose exec app ruff check app/ --fix

# Type checking
docker-compose exec app mypy app/

# Format code
docker-compose exec app black app/
```

---

## Important URLs

- **API Documentation (Swagger):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/v1/health
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Project Structure Quick Map

```
app/
├── api/v1/endpoints/     → Add new API endpoints here
├── services/             → Add business logic here
├── repositories/         → Add database queries here
├── models/               → Add database tables here
├── schemas/              → Add request/response models here
├── core/                 → Shared utilities (exceptions, security)
├── config.py             → Application settings
└── main.py               → Application entry point (rarely touched)
```

---

## Common Tasks

### Add New Endpoint

1. Create schema in [app/schemas](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/schemas:0:0-0:0)
2. Create endpoint in [app/api/v1/endpoints](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/api/v1/endpoints:0:0-0:0)
3. Register in [app/api/v1/router.py](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/api/v1/router.py:0:0-0:0)
4. Write test in `tests/api/`

### Add Service

1. Create service class in [app/services](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/services:0:0-0:0)
2. Add dependency provider
3. Inject into endpoints with `Depends()`
4. Write tests in `tests/unit/services/`

### Add Database Table

1. Create model in [app/models](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/app/models:0:0-0:0)
2. Create migration: `docker-compose exec app alembic revision -m "add table"`
3. Edit migration file in `alembic/versions/`
4. Apply migration: `docker-compose exec app alembic upgrade head`

### Add New Dependency

1. Add to `requirements.txt`
2. Rebuild: `docker-compose up --build`

---

## Environment Variables

Key variables in `.env`:

```bash
# Required
DATABASE_URL=mysql+pymysql://ohs_user:ohs_password@mysql:3306/ohs_remote
SECRET_KEY=your-secret-key
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional
DEBUG=true
LOG_LEVEL=INFO
```

---

## Git Workflow

```bash
# Start feature
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# Commit changes
git add .
git commit -m "Clear description of change"

# Push
git push origin feature/your-feature-name

# Create PR on GitHub
```

### Commit Message Examples

Good:
- `Add order creation endpoint`
- `Implement document generation service`
- `Fix NAICS code validation regex`

Bad:
- `Updates`
- `Fixed stuff`
- `Changes`

---

## Debugging

### View Application Logs

```bash
# Real-time logs
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app

# Search logs
docker-compose logs app | grep "error"
```

### Enable Debug Logging

In `.env`:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

Then restart:
```bash
docker-compose restart app
```

### Access Python Shell

```bash
docker-compose exec app python

>>> from app.config import settings
>>> print(settings.database_url)
>>> exit()
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process
lsof -i :8000

# Kill it
kill -9 <PID>
```

### Container Won't Start

```bash
# Clean rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Database Connection Error

```bash
# Check MySQL is running
docker-compose ps

# Wait 30 seconds after first start
# MySQL needs time to initialize

# Restart MySQL
docker-compose restart mysql
```

### Changes Not Reflecting

```bash
# Restart app service
docker-compose restart app

# Check logs for auto-reload
docker-compose logs -f app
# Should see "Reloading..." when you save
```

---

## Code Patterns

### Endpoint Pattern

```python
@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    request: OrderCreateRequest,
    service: OrderService = Depends(get_order_service)
) -> OrderResponse:
    order = service.create_order(request)
    return OrderResponse.from_orm(order)
```

### Service Pattern

```python
class OrderService:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo
    
    def create_order(self, request: OrderCreateRequest) -> Order:
        if not request.order_id:
            raise ValueError("order_id is required")
        
        order = Order(...)
        return self.order_repo.create(order)
```

### Repository Pattern

```python
class OrderRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, order_id: int) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()
```

---

## Testing Patterns

### Endpoint Test

```python
def test_create_order(client):
    response = client.post("/api/v1/orders", json={
        "plan_id": "basic",
        "user_email": "test@example.com"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "order_id" in data
```

### Service Test

```python
def test_order_service_validates_plan(mock_repo):
    service = OrderService(mock_repo)
    
    with pytest.raises(ValidationError):
        service.create_order(invalid_request)
```

---

## Documentation

- **Getting Started:** [docs/GETTING_STARTED.md](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/docs/GETTING_STARTED.md:0:0-0:0)
- **Python Concepts:** [docs/PYTHON_BACKEND_CONCEPTS.md](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/docs/PYTHON_BACKEND_CONCEPTS.md:0:0-0:0)
- **Architecture:** [docs/ARCHITECTURE.md](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/docs/ARCHITECTURE.md:0:0-0:0)
- **Docker Guide:** [docs/DOCKER_GUIDE.md](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/docs/DOCKER_GUIDE.md:0:0-0:0)
- **Coding Standards:** [.github/instructions/coding_guide.instructions.md](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/.github/instructions/coding_guide.instructions.md:0:0-0:0)

---

## Need Help?

1. Check logs: `docker-compose logs -f app`
2. Search documentation in `docs/`
3. Review similar code in the codebase
4. Ask team members
5. Create GitHub issue

---

## Keyboard Shortcuts (VS Code)

- `Cmd+P` - Quick file open
- `Cmd+Shift+F` - Search across files
- `F12` - Go to definition
- `Cmd+Click` - Follow symbol
- `Cmd+/` - Toggle comment
- `Cmd+Shift+P` - Command palette

---

Keep this guide handy for quick reference! 🚀
