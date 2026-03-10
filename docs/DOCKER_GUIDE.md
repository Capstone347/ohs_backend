# Docker Setup Guide

This guide explains the Docker configuration for the OHS Remote backend and how to work with it effectively.

---

## What is Docker?

Docker allows you to run applications in isolated containers - think of them as lightweight virtual machines. This ensures everyone on the team has the exact same development environment.

### Key Concepts

**Container:**
A running instance of your application with all its dependencies. Isolated from your host machine.

**Image:**
A blueprint for containers. Built from a Dockerfile.

**Volume:**
Shared storage between your host machine and container. Changes persist even when container stops.

**Network:**
Allows containers to communicate with each other.

---

## Project Docker Setup

### docker-compose.yml

Our project uses Docker Compose to run multiple services:

1. **MySQL Database** - Stores application data
2. **FastAPI Application** - Runs the backend API
3. **Ngrok Tunnel** - Exposes the API publicly for frontend and webhook access

### Services Breakdown

#### MySQL Service

```yaml
mysql:
  image: mysql:8.0
  ports:
    - "3306:3306"
  environment:
    MYSQL_DATABASE: ohs_remote
    MYSQL_USER: ohs_user
    MYSQL_PASSWORD: ohs_password
  volumes:
    - mysql_data:/var/lib/mysql
```

**What this does:**
- Downloads MySQL 8.0 image
- Exposes port 3306 so you can connect from host
- Creates database and user automatically
- Stores data in a volume (persists between restarts)
- Has health check to ensure it's ready before app starts

#### App Service

```yaml
app:
  build:
    context: .
    dockerfile: docker/Dockerfile
  ports:
    - "8000:8000"
  volumes:
    - ./data:/app/data
    - ./templates:/app/templates
  depends_on:
    mysql:
      condition: service_healthy
```

**What this does:**
- Builds application from [docker/Dockerfile](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/docker/Dockerfile:0:0-0:0)
- Exposes port 8000 for API access
- Mounts local directories for hot reload
- Waits for MySQL to be healthy before starting
- Runs with auto-reload for development

#### Ngrok Service

```yaml
ngrok:
  image: ngrok/ngrok:latest
  environment:
    NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN}
  command: http app:8000 --log stdout
  ports:
    - "4040:4040"
  depends_on:
    - app
```

**What this does:**
- Creates a public HTTPS tunnel to the backend API running on port 8000
- Exposes ngrok's inspection dashboard on `http://localhost:4040`
- Reads your auth token from the `NGROK_AUTHTOKEN` environment variable
- Waits for the app service to start before creating the tunnel
- The public URL changes on each restart (unless you have a paid ngrok plan with a static domain)

**Setup:**
1. Sign up at [https://dashboard.ngrok.com](https://dashboard.ngrok.com)
2. Copy your auth token from the dashboard
3. Add `NGROK_AUTHTOKEN=your_token` to your `.env.docker` file

**Getting the public URL:**
- Open the ngrok dashboard at `http://localhost:4040` to see the assigned public URL
- Or run: `docker-compose logs ngrok` and look for the `Forwarding` line
- Use this URL as your `APP_BASE_URL` and in your frontend API config
- Use this URL for external webhook endpoints (e.g., Stripe webhook URL)

---

## Common Commands

### Starting the Application

```bash
# Start all services
docker-compose up

# Start in background (detached mode)
docker-compose up -d

# Rebuild and start (after dependency changes)
docker-compose up --build
```

**First run takes 3-5 minutes** as Docker:
1. Downloads MySQL image (~200MB)
2. Builds application image
3. Installs Python dependencies
4. Starts services

**Subsequent runs take 10-30 seconds** as images are cached.

### Viewing Logs

```bash
# Follow all logs
docker-compose logs -f

# Follow specific service
docker-compose logs -f app

# View last 100 lines
docker-compose logs --tail=100 app
```

### Stopping the Application

```bash
# Stop services (keeps containers)
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove containers and volumes (deletes database!)
docker-compose down -v
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart app
```

### Running Commands in Containers

```bash
# Run command in app container
docker-compose exec app <command>

# Examples:
docker-compose exec app pytest
docker-compose exec app alembic upgrade head
docker-compose exec app python scripts/seed_database.py

# Access MySQL shell
docker-compose exec mysql mysql -u ohs_user -pohs_password ohs_remote
```

---

## Development Workflow

### Making Code Changes

1. **Edit code in your editor** (VS Code, PyCharm, etc.)
2. **Application auto-reloads** (thanks to `--reload` flag)
3. **Test changes** in browser or Postman

No need to restart container for Python code changes!

### Adding New Dependencies

When you add a package to `requirements.txt`:

```bash
# Rebuild the container
docker-compose up --build

# Or rebuild without starting
docker-compose build
```

### Database Changes

After creating a new Alembic migration:

```bash
# Run migration
docker-compose exec app alembic upgrade head

# Check current version
docker-compose exec app alembic current

# Rollback
docker-compose exec app alembic downgrade -1
```

### Running Tests

```bash
# All tests
docker-compose exec app pytest

# Specific test file
docker-compose exec app pytest tests/api/test_health.py

# With coverage
docker-compose exec app pytest --cov=app
```

---

## Troubleshooting

### Port Already in Use

**Error:**
```
ERROR: for ohs-remote-app  Cannot start service app: 
Ports are not available: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solution:**
Stop the application using that port:

```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use port 8001 on host
```

### Container Won't Start

**Error:**
```
ERROR: Service 'app' failed to build
```

**Solution:**
Check build logs for specific error:

```bash
# Clean build
docker-compose build --no-cache

# View detailed logs
docker-compose up --build
```

### Database Connection Failed

**Error:**
```
Can't connect to MySQL server on 'mysql'
```

**Solutions:**

1. **Wait longer** - MySQL takes ~30 seconds to fully initialize on first run

2. **Check MySQL is running:**
```bash
docker-compose ps
# Should show mysql as "healthy"
```

3. **Restart MySQL:**
```bash
docker-compose restart mysql
docker-compose logs -f mysql
```

### Changes Not Reflecting

If code changes aren't showing:

1. **Check auto-reload is working:**
```bash
docker-compose logs -f app
# Should see "Reloading..." when you save files
```

2. **Verify volume mounting:**
```bash
docker-compose exec app ls -la /app
# Should show your project files
```

3. **Restart container:**
```bash
docker-compose restart app
```

### Out of Disk Space

Docker images and volumes can consume significant space.

**Check disk usage:**
```bash
docker system df
```

**Clean up:**
```bash
# Remove unused containers, networks, images
docker system prune

# Remove all stopped containers and unused images
docker system prune -a

# Remove volumes (WARNING: deletes data!)
docker volume prune
```

---

## Understanding the Dockerfile

[docker/Dockerfile](cci:7://file:///Users/gustavocamargo/Developer/University/ohs_remote/docker/Dockerfile:0:0-0:0) explains how to build the application image:

```dockerfile
FROM python:3.11-slim
```
Start with Python 3.11 base image (lightweight version)

```dockerfile
WORKDIR /app
```
Set `/app` as the working directory inside container

```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config
```
Install system dependencies needed for MySQL Python driver

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
Copy requirements file and install Python dependencies

```dockerfile
COPY . .
```
Copy entire project into container

```dockerfile
RUN mkdir -p /app/data/uploads/logos \
    /app/data/documents/generated \
    /app/data/documents/previews
```
Create directories for file storage

```dockerfile
EXPOSE 8000
```
Document that container listens on port 8000

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Default command to run when container starts

---

## Docker Best Practices

### 1. Use .dockerignore

Prevents copying unnecessary files into container:
```
.git
.venv
__pycache__
*.pyc
.env
```

### 2. Layer Caching

Docker caches each instruction. Order matters:

**Good - requirements rarely change:**
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

**Bad - invalidates cache on every code change:**
```dockerfile
COPY . .
RUN pip install -r requirements.txt
```

### 3. Volume Mounting for Development

Development: Mount code as volume (changes reflect immediately)
```yaml
volumes:
  - .:/app
```

Production: Copy code into image (immutable)
```dockerfile
COPY . .
```

### 4. Multi-Stage Builds

For production, use multi-stage builds to reduce image size:
```dockerfile
# Build stage
FROM python:3.11 as builder
# Install dependencies

# Production stage
FROM python:3.11-slim
COPY --from=builder /app /app
```

---

## Environment-Specific Configuration

### Development (Current Setup)

- Auto-reload enabled
- Debug mode on
- Volumes mounted for hot reload
- Detailed logging

### Production (Future)

Changes for production:
- Disable auto-reload
- Disable debug mode
- Use environment variables from secret manager
- Enable proper logging and monitoring
- Use production database with SSL
- Run multiple workers: `--workers 4`

---

## Quick Reference

### Essential Commands

```bash
# Start
docker-compose up

# Stop
docker-compose down

# Rebuild
docker-compose up --build

# Logs
docker-compose logs -f app

# Run command
docker-compose exec app <command>

# Clean everything
docker-compose down -v
docker system prune -a
```

### Health Checks

```bash
# Check all containers running
docker-compose ps

# Check app health
curl http://localhost:8000/api/v1/health

# Check MySQL
docker-compose exec mysql mysqladmin ping -h localhost
```

### Database Access

```bash
# MySQL shell
docker-compose exec mysql mysql -u ohs_user -pohs_password ohs_remote

# Run SQL file
docker-compose exec -T mysql mysql -u ohs_user -pohs_password ohs_remote < backup.sql

# Dump database
docker-compose exec mysql mysqldump -u ohs_user -pohs_password ohs_remote > backup.sql
```

---

## Next Steps

Now that you understand Docker setup:

1. **Start the application** - `docker-compose up`
2. **Verify it works** - Visit http://localhost:8000/docs
3. **Make a code change** - Watch it auto-reload
4. **Run tests** - `docker-compose exec app pytest`
5. **Explore the containers** - `docker-compose exec app bash`

Docker takes care of the environment setup so you can focus on writing code!
