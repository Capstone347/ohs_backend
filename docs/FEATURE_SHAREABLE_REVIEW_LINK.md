---
name: Feature Request
about: Propose a new feature or enhancement
title: 'feat: shareable pre-payment order review link'
labels: enhancement
assignees: ''
---

## Description
Let a customer generate a short-lived, read-only link to their order summary and document preview that they can share with a colleague, manager, or safety officer for sign-off before completing payment — no account or login required.

**Scope:**
- `POST /api/v1/orders/{order_id}/review-link` — generates a signed token and returns the shareable URL
- `GET /api/v1/orders/review/{token}` — public endpoint, returns read-only order summary + document preview metadata
- Two new columns on `Order`: `review_token: CHAR(64)` and `review_token_expires_at: DateTime` (expires 48 hours after creation)
- New Alembic migration for the two columns

**Acceptance Criteria:**
- [ ] `POST` generates a unique `review_token`, persists it on the order, and returns the full shareable URL
- [ ] `GET` with a valid token returns order summary (plan, province, NAICS, document preview reference) — no sensitive payment data
- [ ] `GET` with an expired or unknown token returns `410 Gone`
- [ ] Calling `POST` again on the same order rotates the token and resets the expiry
- [ ] Token is a 64-character random hex string — same generation pattern as `Document.access_token`

**Additional Context**
- No login involved — the token in the URL is the only credential
- Reuses the `access_token` + expiry pattern already established on the `Document` model
- The read-only response intentionally excludes `total_amount` and any payment state
- Useful for businesses where the person filling out the form isn't the one who approves the purchase

