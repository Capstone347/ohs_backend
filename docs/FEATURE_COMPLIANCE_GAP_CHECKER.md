---
name: Feature Request
about: Propose a new feature or enhancement
title: 'feat: compliance gap checker endpoint'
labels: enhancement
assignees: ''
---

## Description
After a user saves their industry intake answers, expose an endpoint that cross-references their submitted risk flags and province against a known ruleset and returns a list of gaps or recommended sections before they proceed to payment.

For example: a user in Ontario who flags "working at heights" would receive a warning that a written fall protection plan is required under ON Reg 213/91 and is not covered by their selected plan.

**Scope:**
- `POST /api/v1/orders/{order_id}/compliance-check` — runs the check and returns flagged gaps
- A static ruleset registry in `services/` mapping `(province, hazard_flag) → required_section + regulatory_reference`
- Response schema with a list of `ComplianceGap` objects (`section`, `reason`, `severity: advisory | required`)
- Endpoint reads from the already-persisted intake answers — no new user input needed

**Acceptance Criteria:**
- [ ] Returns `200` with an empty `gaps` list if no issues are found
- [ ] Returns at least one gap entry for a known province + hazard combination (e.g. ON + `working_at_heights`)
- [ ] Each gap includes a `severity` field: `required` (plan doesn't cover it) or `advisory` (recommended addition)
- [ ] Raises `404` if the order has no saved intake answers yet
- [ ] Ruleset lives in a dedicated module — not hardcoded inside the endpoint or service method

**Additional Context**
- Intake answers are already persisted via `PUT /orders/{order_id}/intake-answers`
- `jurisdiction` is already stored on the `Order` model
- No new database models or migrations needed for Phase 1 — ruleset is a static in-memory registry
- This runs before payment, so it's a read-only advisory call — nothing is mutated

