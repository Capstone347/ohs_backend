# Capstone347 — Git Repositories

The OHS Remote project is split across two repositories under the **Capstone347** GitHub organization: a FastAPI backend and a React/TypeScript frontend. Both repositories contain their own `README.md` with a project overview, setup instructions, and a list of key features, per the rubric.

## Organization

- **GitHub organization:** https://github.com/Capstone347

## Repositories

| Repo | URL | What it contains |
|---|---|---|
| Backend | https://github.com/Capstone347/ohs_backend | FastAPI application, SQLAlchemy + Alembic models and migrations, Stripe/OpenAI/SMTP integrations, DOCX document generation, admin API, SJP generation pipeline, Docker Compose dev stack. |
| Frontend | https://github.com/Capstone347/ohs_frontend | React 18 + Vite 5 + TypeScript SPA, Tailwind + shadcn/ui, the customer order wizard, user dashboard, admin dashboard, SJP progress polling. |

## Root-level documents in the backend repo

Every item the rubric asks a README to contain is already in the backend's root `README.md`:

- **Project overview** — first section of `README.md`.
- **Setup instructions** — `README.md` routes to `GETTING_STARTED.md` for the full first-run walkthrough and to `docs/DOCKER_GUIDE.md` for Docker-specific guidance.
- **Key features** — tech stack table and feature list in `README.md`, expanded in `CHANGELOG.md` under the `[Unreleased]` section.

The same applies to the frontend repo, which ships its own `README.md`, `GETTING_STARTED.md`, and `docs/` folder.

## Organization and commit quality

- Both repos use Conventional-style commit messages and merged feature branches via pull requests (never direct pushes to `main`).
- Issues on the shared GitHub Project board (https://github.com/orgs/Capstone347/projects/2) link to the pull requests that closed them.
- Folder structure in each repo follows the layered architecture documented in `docs/ARCHITECTURE.md` (backend) and `docs/ARCHITECTURE.md` (frontend).
