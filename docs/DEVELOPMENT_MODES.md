# Development Environment Setup - Quick Guide

This guide clarifies the separation between Docker and local development environments.

## Environment Files Overview

| File | Purpose | When to Use |
|------|---------|-------------|
| `.env` | Local development | Running app locally, connecting to Docker MySQL on port 3307 |
| `.env.docker` | Docker development | Running full stack in Docker with docker-compose |
| `.env.example` | Template | Copy to create `.env` for local development |

## Development Modes

### Mode 1: Full Docker Stack

**Use Case:** First-time setup, team consistency, minimal configuration

```bash
# Start everything (app + database)
docker-compose up --build

# View logs
docker-compose logs -f app

# Stop everything
docker-compose down

# Remove volumes (fresh start)
docker-compose down -v
```

**Configuration:**
- Uses `.env.docker` automatically
- Database: `mysql://ohs_dev_user:ohs_dev_password@mysql:3306/ohs_remote_dev`
- Database automatically created on first run
- App available at: http://localhost:8000

---

### Mode 2: Local App + Docker Database

**Use Case:** Active development, faster iteration, debugging

```bash
# Terminal 1: Start only database
docker-compose up mysql

# Terminal 2: Run app locally
source venv/bin/activate
uvicorn app.main:app --reload
```

**Configuration:**
- Uses `.env` file
- Database: `mysql://root:root_password@localhost:3307/ohs_remote_dev`
- Connects to Docker MySQL on port 3307
- App available at: http://localhost:8000

**Why this is better for development:**
- Instant code reloads (no container rebuild)
- Direct debugging with breakpoints
- Faster test execution
- Easy access to Python REPL
- IDE integration works perfectly

---

## Database Connection Details

### Docker Development (Full Stack)
```
Host: mysql (Docker internal network)
Port: 3306 (internal)
External Port: 3307 (for tools like MySQL Workbench)
Database: ohs_remote_dev
User: ohs_dev_user
Password: ohs_dev_password
```

### Local Development
```
Host: localhost
Port: 3307 (mapped from Docker)
Database: ohs_remote_dev
User: root
Password: root_password
```

### Production
```
Host: your-cloud-database.region.provider.com
Port: 3306 (or your cloud provider's port)
Database: ohs_remote_prod
User: secure_user (from secrets manager)
Password: secure_password (from secrets manager)
```

---

## Common Commands

### Docker Development

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Rebuild after dependency changes
docker-compose up --build

# View logs
docker-compose logs -f app
docker-compose logs -f mysql

# Execute command in container
docker-compose exec app python -m pytest
docker-compose exec mysql mysql -u root -p

# Stop services
docker-compose down

# Stop and remove volumes (fresh database)
docker-compose down -v
```

### Local Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run app
uvicorn app.main:app --reload

# Run tests
pytest

# Run linting
ruff check app/
mypy app/

# Format code
black app/

# Access database
mysql -h 127.0.0.1 -P 3307 -u root -proot_password ohs_remote_dev
```

---

## Switching Between Modes

### From Docker to Local

```bash
# Stop Docker app (keep database running)
docker-compose stop app

# Activate local environment
source venv/bin/activate

# Run locally
uvicorn app.main:app --reload
```

### From Local to Docker

```bash
# Stop local app (Ctrl+C)

# Start Docker app
docker-compose up app
```

---

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

### Database Connection Failed

```bash
# Check if MySQL is running
docker-compose ps

# Check logs
docker-compose logs mysql

# Restart database
docker-compose restart mysql

# Fresh database start
docker-compose down -v
docker-compose up mysql
```

### Docker Build Issues

```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Python Environment Issues

```bash
# Recreate virtual environment
deactivate
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## Best Practices

1. **Use Docker for database** - Even in local development mode, Docker MySQL is easier than managing a local MySQL installation

2. **Use local mode for development** - Faster iteration, better debugging experience

3. **Use Docker mode for testing** - Ensures your changes work in containerized environment

4. **Never commit `.env` files** - These contain secrets and are gitignored

5. **Update `.env.example`** - When adding new environment variables, document them

6. **Test both modes** - Before pushing, verify your changes work in both Docker and local modes

7. **Keep databases separate** - Use different database names for different modes to avoid conflicts

---

## Quick Reference

| Task | Docker Mode | Local Mode |
|------|-------------|------------|
| Start | `docker-compose up` | `uvicorn app.main:app --reload` |
| Stop | `docker-compose down` | `Ctrl+C` |
| Logs | `docker-compose logs -f` | Terminal output |
| Tests | `docker-compose exec app pytest` | `pytest` |
| Database | Auto-created | Auto-created (first run) |
| Port | 8000 | 8000 |
| Hot Reload | Yes (mounted volumes) | Yes (native) |
| Speed | Slower (container overhead) | Faster (native) |
| Isolation | Complete | Partial (shares host) |
