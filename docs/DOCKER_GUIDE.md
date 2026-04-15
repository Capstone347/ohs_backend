# Docker Guide

This guide explains how the Docker Compose stack is wired together and the day-to-day commands you need to work with it. **Docker is the only supported development path for this project** — if you are setting up for the first time, read [GETTING_STARTED.md](../GETTING_STARTED.md) first and come back here when you have the stack running.

---

## What is Docker, briefly

- **Image** — a built, immutable blueprint for a container (created from a `Dockerfile`).
- **Container** — a running instance of an image. Isolated from your host OS.
- **Volume** — persistent storage managed by Docker. Our MySQL data lives in a volume so it survives container restarts.
- **Bind mount** — a host directory exposed inside a container. We use bind mounts so code edits on your laptop take effect inside the running app container immediately.
- **docker-compose** — describes and starts multiple containers at once from a single YAML file.

If you are new to Docker, these are the only concepts you need to be productive here.

---

## The stack

`docker-compose.yml` defines three services on a private network called `ohs-network-dev`:

| Service | Image | Host port | Purpose |
|---|---|---|---|
| `mysql` | `mysql:8.0` | `3307` | MySQL database. Data persisted in the `mysql_dev_data` volume. |
| `app` | built from `docker/Dockerfile` | `8000` | FastAPI app. Runs `alembic upgrade head` then `uvicorn` with `--reload`. |
| `ngrok` | `ngrok/ngrok:latest` | `4040` | Public HTTPS tunnel to `app:8000` so Stripe can deliver webhooks. |

### Key configuration points

- **Database credentials** (defined in `docker-compose.yml`, used inside the Docker network):
  - Database: `ohs_remote_dev`
  - User: `ohs_dev_user` / password: `ohs_dev_password`
  - Root password: `root_password`
  - Host (from inside the `app` container): `mysql`
  - Host (from your laptop, e.g. MySQL Workbench): `localhost` on port `3307`
- **Healthchecks** — `mysql` has a `mysqladmin ping` healthcheck. The `app` service waits for `mysql` to be `healthy` before starting, so you will not see "can't connect to MySQL" on startup unless something is genuinely wrong.
- **Bind mounts** — `./app`, `./alembic`, `./scripts`, `./data`, and `./templates` are mounted into the `app` container. Edits to Python code on your laptop are picked up by the uvicorn reloader instantly, no rebuild required.
- **Env file** — the `app` service reads `.env.docker`. The `ngrok` service reads `NGROK_AUTHTOKEN` directly from the host environment (which also comes from `.env.docker` because docker-compose auto-loads it).
- **Migrations on startup** — the `app` container's command runs `alembic upgrade head` before launching uvicorn. You do not need to run migrations manually unless you are creating a new one.

### Where ports come from

- `app` — `8000:8000`. API on http://localhost:8000, Swagger on http://localhost:8000/docs.
- `mysql` — `3307:3306`. Use `localhost:3307` from your host. **Inside** the `app` container the hostname is `mysql` on the internal port `3306`.
- `ngrok` — `4040:4040`. Dashboard on http://localhost:4040, which shows your current public `https://*.ngrok-free.app` URL.

---

## First run

From a clean checkout:

```bash
cp .env.docker.example .env.docker
# fill in the required values — see GETTING_STARTED.md
docker-compose up --build
```

The first build takes several minutes (Docker downloads the MySQL and Python base images, then installs Python dependencies). Subsequent runs start in ~10–30 seconds because everything is cached.

After the stack is healthy, seed the plans table **once**:

```bash
docker-compose exec app python scripts/seed_plans.py
```

---

## Day-to-day commands

### Lifecycle

```bash
docker-compose up                # start (foreground, follow logs)
docker-compose up -d             # start in the background
docker-compose up --build        # rebuild the app image after a dependency change
docker-compose down              # stop and remove containers (keeps the DB volume)
docker-compose down -v           # stop and remove containers AND the DB volume — fresh DB
docker-compose restart app       # restart just the app
docker-compose ps                # list running services and health
```

### Logs

```bash
docker-compose logs -f app       # follow app logs
docker-compose logs -f mysql     # follow MySQL logs
docker-compose logs -f ngrok     # follow ngrok — shows the current public URL
docker-compose logs --tail=100 app
```

### Shelling in

```bash
docker-compose exec app bash                 # interactive shell in the app container
docker-compose exec app python               # Python REPL inside the app
docker-compose exec mysql mysql -u ohs_dev_user -pohs_dev_password ohs_remote_dev
```

### Tests, linting, type-checking

All tooling runs **inside** the `app` container so you get the exact dependencies specified in `requirements.txt` / `requirements-dev.txt`:

```bash
docker-compose exec app pytest
docker-compose exec app pytest tests/unit/
docker-compose exec app pytest --cov=app --cov-report=html
docker-compose exec app ruff check app/
docker-compose exec app ruff check app/ --fix
docker-compose exec app mypy app/
```

### Database migrations

Migrations are applied automatically on `app` startup. You only run alembic manually when authoring a new migration or debugging:

```bash
docker-compose exec app alembic current
docker-compose exec app alembic upgrade head
docker-compose exec app alembic downgrade -1
docker-compose exec app alembic revision -m "add foo column to orders"
```

After creating a new revision, edit the generated file under `alembic/versions/` and add both `upgrade()` and `downgrade()` bodies before restarting the app.

### Adding a Python dependency

Dependencies are frozen inside the image. After editing `requirements.txt` you must rebuild:

```bash
docker-compose up --build
```

A plain `docker-compose restart app` is **not** enough — the new package is not in the image yet.

---

## Dockerfile overview

`docker/Dockerfile` starts from `python:3.11-slim`, installs the system libraries needed by `mysqlclient` and `python-docx` (`gcc`, `default-libmysqlclient-dev`, `pkg-config`, etc.), installs Python dependencies from `requirements.txt`, creates the `data/` subdirectories used for runtime file storage, exposes port 8000, and runs `uvicorn app.main:app`.

The dependency install happens **before** the application source is copied so that Docker's layer cache is reused when only application code changes. Editing `app/` code does not invalidate the pip install layer.

---

## Troubleshooting

The most common Docker problems and their fixes live in **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**. Check there before anything else — it covers missing env vars, port conflicts, stale migrations, ngrok auth issues, and database state problems.

Quick first-response commands when something looks wrong:

```bash
docker-compose ps                # is everything actually running and healthy?
docker-compose logs --tail=200 app
docker-compose restart app
docker-compose down && docker-compose up --build   # nuclear rebuild, keeps DB
docker-compose down -v && docker-compose up --build # truly fresh, wipes DB
```

---

## Docker Compose and your `.env.docker` file

Docker Compose automatically loads variables from a file named `.env` in the project root **and** passes whatever is listed under `env_file:` in `docker-compose.yml` into the target container. In this project:

- The `app` service declares `env_file: .env.docker`, so **everything inside `.env.docker` is available to the FastAPI app** as environment variables (which `Pydantic Settings` reads via `app/config.py`).
- The `ngrok` service only needs `NGROK_AUTHTOKEN`, which it reads from the host environment. Because `.env.docker` is the file you populate, make sure `NGROK_AUTHTOKEN` is defined there.
- Production is not configured in this repo. When you deploy, provide each variable through your platform's secret store instead of a file.
