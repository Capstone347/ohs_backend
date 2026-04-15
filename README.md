# OHS Remote Backend

FastAPI backend for **OHS Remote**, a platform that generates legally-compliant Health & Safety documents for small and medium businesses in Ontario (and other Canadian jurisdictions).

The backend handles the full order lifecycle: plan selection, company intake, AI-assisted Safe Job Procedure (SJP) generation, Stripe payments, document generation from DOCX templates, and email delivery. The frontend lives in a separate repository and consumes this API.

---

## New here? Start with these three docs

1. **[GETTING_STARTED.md](GETTING_STARTED.md)** — The step-by-step onboarding guide. Follow it in order. It tells you exactly which accounts to create (Google / ngrok / Stripe / OpenAI), how to fill in every required environment variable, and how to bring the full Docker stack up for the first time.
2. **[docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md)** — How the Docker stack is wired together and the day-to-day commands you'll need (logs, shelling in, running tests, running migrations).
3. **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — Common failures and how to fix them. Check here *before* asking for help.

> **Docker is the only supported development path.** The project has a precise environment (MySQL version, Python version, system libraries for `python-docx` and the MySQL driver) and Docker Compose pins all of it. Running outside Docker is possible but unsupported — if you try it, you are on your own.

---

## Documentation map

### Setup & day-to-day work
| Doc | What it covers |
|---|---|
| [GETTING_STARTED.md](GETTING_STARTED.md) | First-time onboarding — accounts, env vars, running the stack |
| [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) | Docker services, common commands, dev workflow |
| [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | Cheat sheet for daily commands |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Symptom → fix for the common failure modes |

### Understanding the codebase
| Doc | What it covers |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layered architecture (API → Service → Repository → Model), design patterns, error handling |
| [docs/PYTHON_BACKEND_CONCEPTS.md](docs/PYTHON_BACKEND_CONCEPTS.md) | FastAPI / Pydantic / SQLAlchemy primer for developers new to Python backends |
| [CLAUDE.md](CLAUDE.md) | Project-wide coding standards (also read by AI coding agents) |

### API reference
| Doc | What it covers |
|---|---|
| [docs/API_OVERVIEW.md](docs/API_OVERVIEW.md) | High-level map of every endpoint, the full order flow, auth model, status enums |
| [docs/ADMIN_API.md](docs/ADMIN_API.md) | Admin endpoints (separate auth, order management, review workflow) |
| [docs/SJP_FRONTEND_GUIDE.md](docs/SJP_FRONTEND_GUIDE.md) | Safe Job Procedure generation feature — async job flow, polling, delivery |
| http://localhost:8000/docs | Swagger UI with live schemas — **this is the source of truth for request/response bodies** |

### History & design notes
| Doc | What it covers |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [docs/erd.drawio](docs/erd.drawio) | Database ERD (open with draw.io / diagrams.net) |

---

## Tech stack at a glance

| Layer | Technology |
|---|---|
| Web framework | FastAPI (Python 3.11) |
| Data | MySQL 8.0 via SQLAlchemy 2.x + Alembic migrations |
| Validation | Pydantic v2 |
| Documents | `python-docx` + Jinja2 DOCX templates in `templates/documents/` |
| Email | SMTP (Gmail in dev) with Jinja2 HTML templates in `templates/emails/` |
| Payments | Stripe Checkout (test mode in dev), webhook-driven status transitions |
| AI | OpenAI API for SJP content generation (`gpt-5-mini` by default) |
| Dev networking | ngrok tunnel so Stripe webhooks reach your local machine |
| Container runtime | Docker + Docker Compose |

## Repository layout

```
ohs_remote/
├── app/
│   ├── api/v1/endpoints/    FastAPI routers (one file per resource)
│   ├── services/            Business logic — the real work lives here
│   ├── repositories/        SQLAlchemy data access
│   ├── models/              ORM table definitions
│   ├── schemas/             Pydantic request / response models
│   ├── core/                Exceptions, logging, security primitives
│   ├── database/            Session + engine setup
│   ├── config.py            Pydantic Settings (reads .env / .env.docker)
│   └── main.py              FastAPI app factory, CORS, middleware, lifespan
├── alembic/                 Database migrations
├── docker/                  Dockerfile + MySQL init SQL
├── docker-compose.yml       mysql + app + ngrok
├── templates/
│   ├── documents/           DOCX templates (basic, comprehensive, SJP)
│   └── emails/              HTML email templates
├── scripts/                 seed_plans.py, template preprocessing
├── tests/                   pytest unit / integration / api tests
├── data/                    Runtime file storage (logos, generated docs) — gitignored
└── docs/                    Everything in the documentation map above
```

## First-run checklist

Before you can bring the stack up you will need:

- [ ] Docker Desktop installed and running
- [ ] A Google account with 2-Step Verification enabled (for a Gmail App Password)
- [ ] An ngrok account (free tier is fine) with an auth token
- [ ] Access to the shared Stripe project in **Test mode**
- [ ] An OpenAI API key with credit on it (the SJP feature will not run without it)
- [ ] `.env.docker` populated — see [GETTING_STARTED.md](GETTING_STARTED.md)

Then:

```bash
git clone <repo-url>
cd ohs_remote
cp .env.docker.example .env.docker   # then fill in values per GETTING_STARTED.md
docker-compose up --build
```

The app will be on http://localhost:8000, Swagger on http://localhost:8000/docs, the ngrok dashboard on http://localhost:4040.

## Contact

- **Project lead:** Gustavo (team Capstone347)
- **Client:** Jennifer Murray

For bugs and feature requests, open an issue on GitHub with a clear description, reproduction steps, and any relevant logs.
