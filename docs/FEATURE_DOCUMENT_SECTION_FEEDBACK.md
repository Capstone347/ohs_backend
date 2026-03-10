---
name: Feature Request
about: Propose a new feature or enhancement
title: 'feat: post-delivery document section feedback'
labels: enhancement
assignees: ''
---

## Description
After a document is delivered, allow the customer to flag a specific section as incorrect or needing a change by submitting feedback tied to their document. The customer authenticates using their existing `access_token` so no login is required. Admins can view all outstanding feedback to act on it.

**Scope:**
- `POST /api/v1/documents/{document_id}/feedback` — submit feedback for a section, authenticated by `access_token` in the request body
- `GET /api/v1/admin/feedback` — paginated list of all submitted feedback (admin only for now, no auth guard needed in Phase 1)
- New `document_feedback` table: `id`, `document_id` (FK), `section_name`, `notes`, `submitted_at`
- New Alembic migration for the table
- `DocumentFeedback` SQLAlchemy model, repository, and schema

**Acceptance Criteria:**
- [ ] `POST` validates that `access_token` matches the document — returns `403` if it doesn't
- [ ] `POST` returns `403` if `token_expires_at` has passed (token no longer valid means the customer's access window has closed)
- [ ] `section_name` is a non-empty string (max 100 chars); `notes` is required (max 1000 chars)
- [ ] A document can have multiple feedback entries (one per section)
- [ ] `GET /admin/feedback` returns entries ordered by `submitted_at` descending, supports `?document_id=` filter
- [ ] `submitted_at` is set server-side — not accepted from the request body

**Additional Context**
- Customers already have `access_token` from the document delivery email — no new credential needed
- Right now there is no structured channel for post-delivery corrections; customers email support with zero context
- The `document_feedback` table is a clean addition — no changes to existing models
- `section_name` values do not need to be validated against a fixed enum in Phase 1; free-text is fine

