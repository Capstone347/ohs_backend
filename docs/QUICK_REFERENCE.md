# Quick Reference

Cheat sheet for daily work on the OHS Remote backend. Assumes you have already been through [GETTING_STARTED.md](../GETTING_STARTED.md) and have a working `.env.docker`.

---

## Daily workflow

```bash
cd ~/Developer/University/ohs_remote
docker-compose up                              # start everything, follow logs
open http://localhost:8000/docs                # Swagger UI
# ... edit code — app auto-reloads on save ...
docker-compose exec app pytest                 # run tests
docker-compose down                            # stop at end of day
```

---

## Docker

```bash
docker-compose up                  # start (foreground)
docker-compose up -d               # start in background
docker-compose up --build          # rebuild (after requirements.txt change)
docker-compose down                # stop, keep DB
docker-compose down -v             # stop and wipe DB volume
docker-compose ps                  # service status + health
docker-compose logs -f app         # follow app logs
docker-compose logs -f ngrok       # shows current public ngrok URL
docker-compose exec app bash       # shell inside the app container
```

---

## Testing & code quality

```bash
docker-compose exec app pytest
docker-compose exec app pytest tests/unit/
docker-compose exec app pytest tests/api/test_health.py
docker-compose exec app pytest -k "test_create_order"
docker-compose exec app pytest --cov=app --cov-report=html

docker-compose exec app ruff check app/
docker-compose exec app ruff check app/ --fix
docker-compose exec app mypy app/
```

---

## Database

The Docker stack auto-runs `alembic upgrade head` on startup. Run these only when creating or debugging migrations.

```bash
docker-compose exec app alembic current
docker-compose exec app alembic upgrade head
docker-compose exec app alembic downgrade -1
docker-compose exec app alembic revision -m "add column to orders"

# MySQL shell (from inside the stack — uses internal creds)
docker-compose exec mysql mysql -u ohs_dev_user -pohs_dev_password ohs_remote_dev

# MySQL shell (from your host via the mapped port)
mysql -h 127.0.0.1 -P 3307 -u ohs_dev_user -pohs_dev_password ohs_remote_dev
```

Seed the plans table (only needed once per fresh DB):

```bash
docker-compose exec app python scripts/seed_plans.py
```

---

## Useful URLs

| URL | Purpose |
|---|---|
| http://localhost:8000/docs | Swagger UI — live API reference, try endpoints here |
| http://localhost:8000/redoc | ReDoc — alternative API reference |
| http://localhost:8000/openapi.json | Raw OpenAPI schema |
| http://localhost:8000/api/v1/health | Health check |
| http://localhost:4040 | ngrok dashboard — shows your current public HTTPS URL |

---

## Project layout

```
app/
├── api/v1/endpoints/    FastAPI routers (one file per resource)
├── api/v1/router.py     Registers every router under /api/v1
├── api/dependencies.py  FastAPI Depends() wiring for services & repos
├── services/            Business logic
├── repositories/        SQLAlchemy data access
├── models/              ORM table definitions
├── schemas/             Pydantic request / response models
├── core/                Exceptions, logging, security
├── database/            Engine + session setup
├── config.py            Pydantic Settings (env var schema)
└── main.py              FastAPI app factory, CORS, middleware
```

## How to add things

### A new endpoint
1. Create the request/response schemas under `app/schemas/`.
2. Add or extend a service in `app/services/` with the business logic.
3. Add a router function in the right `app/api/v1/endpoints/*.py` file. Keep it thin — parse, delegate, return.
4. Wire any new services/repositories in `app/api/dependencies.py`.
5. If it's a new router file, register it in `app/api/v1/router.py`.
6. Add a test under `tests/api/`.

### A new database table
1. Add the model in `app/models/`.
2. Create a migration: `docker-compose exec app alembic revision -m "add foo table"`.
3. Edit the file under `alembic/versions/` — fill in **both** `upgrade()` and `downgrade()`.
4. The next `docker-compose up` applies it automatically, or run `alembic upgrade head` manually.
5. Add a repository in `app/repositories/` for data access.

### A new dependency
1. Add to `requirements.txt` (or `requirements-dev.txt` for test/lint tooling).
2. `docker-compose up --build` — a plain restart is not enough.

---

## Config reminders

- `app/config.py` is the authoritative list of every environment variable. Required values use `Field(...)` with no default — the app fails to start if they are missing. Check that file when you want to know the full env-var surface area.
- Required in all environments: `SECRET_KEY`, `DATABASE_URL`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `STRIPE_API_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `OPENAI_API_KEY`.
- After changing `.env.docker`, restart the app container for the changes to take effect: `docker-compose restart app`.

---

## Code patterns

### Endpoint (thin)
```python
@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    request: OrderCreateRequest,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = service.create_order(request)
    return OrderResponse.model_validate(order)
```

### Service
```python
class OrderService:
    def __init__(self, order_repo: OrderRepository, plan_repo: PlanRepository):
        self.order_repo = order_repo
        self.plan_repo = plan_repo

    def create_order(self, request: OrderCreateRequest) -> Order:
        plan = self.plan_repo.get_by_id(request.plan_id)
        if plan is None:
            raise PlanNotFoundError(request.plan_id)
        order = Order(plan_id=plan.id, user_email=request.user_email, ...)
        return self.order_repo.create(order)
```

### Repository
```python
class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()
```

---

## Pointers to deeper docs

- **Architecture & layering** — [ARCHITECTURE.md](ARCHITECTURE.md)
- **Python / FastAPI primer** — [PYTHON_BACKEND_CONCEPTS.md](PYTHON_BACKEND_CONCEPTS.md)
- **Docker internals** — [DOCKER_GUIDE.md](DOCKER_GUIDE.md)
- **API reference** — [API_OVERVIEW.md](API_OVERVIEW.md), [ADMIN_API.md](ADMIN_API.md), [SJP_FRONTEND_GUIDE.md](SJP_FRONTEND_GUIDE.md)
- **When something breaks** — [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Coding standards** — [../CLAUDE.md](../CLAUDE.md)
