# Backend API Contract for Frontend

Base URL: `/api/v1`

All authenticated endpoints require the `auth_session` httpOnly cookie (set automatically after OTP verification).
On missing/invalid/expired session, authenticated endpoints return `401 { "detail": "Invalid auth session" }`.

---

## Complete Order Flow (Step by Step)

This is the full happy-path a user goes through. FE steps map to these calls in order.

```
Step 1: Select Plan        →  GET  /plans
Step 1: Create Order       →  POST /orders
Step 2: Company + Logo     →  PATCH /orders/{id}/company-details
Step 3: Industry Intake    →  GET  /industry/intake-questions?naics=...
Step 3: Save Answers       →  PUT  /industry/{order_id}/intake-answers
Step 4: Generate Preview   →  POST /orders/{order_id}/generate-preview
Step 4: View Preview       →  GET  /documents/{document_id}/preview
Step 5: Legal Disclaimer   →  GET  /legal-disclaimers/{plan_id}/{jurisdiction}
Step 5: Acknowledge Terms  →  POST /orders/{order_id}/acknowledge-terms
Step 5: Create Checkout    →  POST /payments/orders/{order_id}/create-checkout-session
Step 5: Redirect to Stripe →  (use checkout_url from response)
  ... Stripe handles payment ...
  ... Webhook auto-triggers: mark paid → generate doc → email delivery ...
Step 5: Success page       →  Stripe redirects to {frontend_url}/orders/{order_id}/success
```

**The `order_id` returned by `POST /orders` is the key that threads through every subsequent call.**

---

## Step 1: Plans + Order Creation

### `GET /plans`
Get available plans.

**Auth:** None
**Response 200:**
```json
{
  "plans": [
    {
      "id": 1,
      "slug": "basic",
      "name": "Basic",
      "description": "Essential health and safety manual",
      "base_price": "99.99"
    },
    {
      "id": 2,
      "slug": "comprehensive",
      "name": "Comprehensive",
      "description": "Full compliance manual",
      "base_price": "199.99"
    }
  ],
  "total": 2
}
```
**Note:** Fields are `id` (not `plan_id`), `base_price` (not `price`). There is no `features` field — features are FE-only display content.

### `POST /orders`
Create a new order. **This must be called first** — the returned `order_id` is used in all subsequent steps.

**Auth:** None
**Body:**
```json
{
  "plan_id": 1,
  "user_email": "user@example.com",
  "full_name": "John Doe",
  "jurisdiction": "ON"
}
```
**Response 201:**
```json
{
  "order_id": 42,
  "status": "draft",
  "created_at": "2026-03-17T04:00:00",
  "message": "Order created successfully"
}
```
**FE must:** Store `order_id` and use it for every subsequent call. If this call hasn't been made, nothing else works.

---

## Step 2: Company Details + Logo Upload

### `PATCH /orders/{order_id}/company-details`
Update company info and optionally upload a logo.

**Auth:** None
**Content-Type:** `multipart/form-data`
**Form fields:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `company_name` | string | yes | |
| `province` | string | yes | 2-50 chars (e.g. "ON") |
| `naics_codes` | string[] | yes | 6-digit codes, can be comma-separated |
| `business_description` | string | no | |
| `logo` | file | no | .png/.jpg/.jpeg/.svg, max 5MB |

**Response 200:** `OrderSummaryResponse` (full order with updated company details)

---

## Step 3: Industry Intake (if applicable)

### `GET /industry/intake-questions?naics={codes}`
Get dynamic intake questions based on NAICS codes.

**Auth:** None
**Query:** `naics` — comma-separated 6-digit NAICS codes (e.g. `236110,238210`)
**Response 200:** `IntakeQuestionsResponse` with questions list

### `PUT /industry/{order_id}/intake-answers`
Save intake answers.

**Auth:** None
**Body:**
```json
{
  "answers": {
    "question_key_1": "answer_value",
    "question_key_2": "answer_value"
  }
}
```
**Response 200:** `IndustryIntakeAnswersResponse`

### `GET /industry/{order_id}/intake-answers`
Retrieve previously saved answers (for back-navigation).

**Auth:** None

---

## Step 4: Document Preview

### `POST /orders/{order_id}/generate-preview`
Generate the document from order data. **Must be called before preview can be viewed.**

**Auth:** None
**Response 201:**
```json
{
  "document_id": 7,
  "order_id": 42,
  "message": "Document generated successfully",
  "generated_at": "2026-03-17T04:30:00"
}
```
**FE must:** Store `document_id` — needed for the preview URL.

### `GET /documents/{document_id}/preview`
View the generated document as PDF.

**Auth:** None (public)
**Response 200:** PDF file stream (`application/pdf`)
**Use:** Render in an iframe or PDF viewer, or open as download.

---

## Step 5: Legal + Payment

### `GET /legal-disclaimers/{plan_id}/{jurisdiction}`
Get the legal disclaimer the user must accept.

**Auth:** None
**Path params:** `plan_id` (int), `jurisdiction` (string, e.g. "ON")
**Response 200:** `LegalDisclaimerResponse` with disclaimer content and version

### `POST /orders/{order_id}/acknowledge-terms`
Record that the user accepted legal terms.

**Auth:** None
**Body:**
```json
{
  "jurisdiction": "ON",
  "content": "disclaimer content or hash",
  "version": 1
}
```
**Response 201:** `LegalAcknowledgmentResponse`

### `GET /payments/stripe/config`
Get Stripe publishable key for Stripe.js initialization.

**Auth:** None
**Response 200:** `{ "publishable_key": "pk_..." }`

### `POST /payments/orders/{order_id}/create-checkout-session`
Create a Stripe Checkout session. **Also used for payment retry.**

**Auth:** None
**Response 200:**
```json
{
  "checkout_session_id": "cs_...",
  "checkout_url": "https://checkout.stripe.com/..."
}
```
**FE must:** Redirect the user to `checkout_url`. After payment:
- **Success:** Stripe redirects to `{frontend_url}/orders/{order_id}/success`
- **Cancel:** Stripe redirects to `{frontend_url}/orders/{order_id}/payment`

**What happens automatically after payment:**
1. Stripe sends webhook to our backend
2. Backend marks order as `paid`
3. Backend generates final document (if not already generated)
4. Backend emails the user a download link

---

## Auth Endpoints

### `POST /auth/request-otp`
**Auth:** None
**Body:** `{ "email": "user@example.com" }`
**Response 200:** `{ "message": "If the email is registered, an OTP has been sent." }`
**Notes:** Generic response (no user enumeration). Rate-limited: 5/email, 6/IP per 15 min. Resend cooldown: 60s.

### `POST /auth/verify-otp`
**Auth:** None
**Body:** `{ "email": "user@example.com", "otp": "123456" }`
**Response 200:** `{ "user": { "id": 1, "email": "user@example.com", "full_name": "John Doe" } }` + sets `auth_session` cookie
**Response 401:** `{ "detail": "Invalid email or OTP" }`
**Cookie:** `auth_session`, httpOnly, Secure (prod), SameSite=lax, Max-Age=3600, Path=/

### `GET /auth/me`
**Auth:** Cookie
**Response 200:** `{ "id": 1, "email": "user@example.com", "full_name": "John Doe" }`
**Response 401:** `{ "detail": "Invalid auth session" }`

### `POST /auth/logout`
**Auth:** None (idempotent)
**Response 200:** `{ "message": "Logged out" }`

---

## Dashboard Endpoints (Post-Purchase)

### `GET /orders`
List authenticated user's orders (paginated).

**Auth:** Cookie
**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string? | null | Search by order ID (numeric) or company name (text) |
| `order_status` | string? | null | Filter: `draft`, `processing`, `review_pending`, `available`, `cancelled` |
| `page` | int | 1 | Page number (1-based) |
| `page_size` | int | 20 | Items per page (max 100) |

**Response 200:**
```json
{
  "items": [
    {
      "order_id": 1,
      "created_at": "2026-03-16T10:00:00",
      "order_status": "draft",
      "payment_status": "pending",
      "total_amount": "199.99",
      "currency": "CAD",
      "jurisdiction": "ON",
      "company_name": "Acme Corp",
      "plan_name": "Basic",
      "naics_codes": ["238220"]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```
**Sorting:** Newest first (`created_at DESC`), not configurable.

### `GET /orders/{order_id}`
Full order detail with timeline and documents.

**Auth:** Cookie (returns 404 if not your order)
**Response 200:**
```json
{
  "order_id": 1,
  "created_at": "2026-03-16T10:00:00",
  "completed_at": null,
  "jurisdiction": "ON",
  "total_amount": "199.99",
  "is_industry_specific": false,
  "company": {
    "id": 1,
    "name": "Acme Corp",
    "logo_id": null,
    "province": "ON",
    "business_description": null,
    "naics_codes": ["238220"]
  },
  "plan_name": "Basic",
  "order_status": "draft",
  "payment_status": "pending",
  "currency": "CAD",
  "documents": [
    {
      "document_id": 1,
      "access_token": "abc123...64chars",
      "token_expires_at": "2026-03-17T10:00:00",
      "generated_at": "2026-03-16T12:00:00",
      "file_format": "docx"
    }
  ],
  "timeline": [
    { "step": "Order Placed", "status": "completed", "timestamp": "2026-03-16T10:00:00" },
    { "step": "Payment", "status": "pending", "timestamp": null },
    { "step": "Processing", "status": "pending", "timestamp": null },
    { "step": "Completed", "status": "pending", "timestamp": null }
  ],
  "naics_codes": ["238220"]
}
```

### `GET /orders/{order_id}/documents`
List documents for an order. (Note: no `/documents` prefix — this is under `/api/v1/orders/`)

**Auth:** Cookie (ownership enforced)
**Response 200:**
```json
[
  {
    "document_id": 1,
    "order_id": 1,
    "file_path": "data/documents/order_1/...",
    "file_format": "docx",
    "access_token": "abc123...64chars",
    "token_expires_at": "2026-03-17T10:00:00",
    "generated_at": "2026-03-16T12:00:00"
  }
]
```

### `GET /documents/{document_id}/download?token={access_token}`
Download document file (DOCX).

**Auth:** None (public, protected by access_token)
**Response 200:** File download (DOCX)
**Response 403:** Token invalid or expired
**Response 404:** Document not found

### `GET /orders/{order_id}/download?token={access_token}`
Download latest document for order.

**Auth:** Cookie + token

### `POST /documents/{document_id}/refresh-token`
Generate a new access token for an expired document.

**Auth:** Cookie (must own the order)
**Response 200:** `DocumentResponse` with new `access_token` and `token_expires_at`

---

## Status Enums

### Order Status
| Value | Description |
|-------|-------------|
| `draft` | Order created, awaiting payment |
| `processing` | Payment confirmed, documents being generated |
| `review_pending` | Documents under review |
| `available` | Documents ready for download |
| `cancelled` | Order cancelled |

### Payment Status
| Value | Description |
|-------|-------------|
| `pending` | Awaiting payment |
| `paid` | Payment confirmed |
| `failed` | Payment failed or checkout expired |
| `refunded` | Payment refunded |

---

## FE Action → BE Endpoint Mapping

| FE Action | Endpoint | Notes |
|-----------|----------|-------|
| Load plans | `GET /plans` | Fields: `id`, `base_price` (no `plan_id`, `price`, or `features`) |
| Create order | `POST /orders` | **Must be called first — returns `order_id`** |
| Save company details | `PATCH /orders/{id}/company-details` | multipart/form-data |
| Get intake questions | `GET /industry/intake-questions?naics=...` | |
| Save intake answers | `PUT /industry/{id}/intake-answers` | |
| Generate preview | `POST /orders/{id}/generate-preview` | Returns `document_id` |
| View preview PDF | `GET /documents/{document_id}/preview` | Public, no auth |
| Get legal disclaimer | `GET /legal-disclaimers/{plan_id}/{jurisdiction}` | |
| Accept legal terms | `POST /orders/{id}/acknowledge-terms` | |
| Start payment | `POST /payments/orders/{id}/create-checkout-session` | Redirect to `checkout_url` |
| Retry payment | `POST /payments/orders/{id}/create-checkout-session` | Same endpoint |
| Login (request OTP) | `POST /auth/request-otp` | |
| Verify OTP | `POST /auth/verify-otp` | Sets cookie |
| Hydrate user state | `GET /auth/me` | Call on app load |
| Logout | `POST /auth/logout` | |
| View orders list | `GET /orders` | Auth required |
| View order detail | `GET /orders/{id}` | Auth required, includes timeline + docs |
| Download document | `GET /documents/{id}/download?token=` | Use `access_token` from order detail |
| Refresh expired token | `POST /documents/{id}/refresh-token` | Auth required |
| Poll for status | `GET /orders/{id}` | Re-fetch order detail |
| Check session | `GET /auth/me` | 401 = expired |
