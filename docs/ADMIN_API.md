# Admin Panel API Documentation

Base URL: `{API_BASE_URL}/api/v1/admin`

All admin endpoints are under the `/admin` prefix. The admin system is **completely separate** from the customer system — different database table, different auth mechanism, different session cookie.

---

## Table of Contents

- [Authentication](#authentication)
- [Order Management](#order-management)
- [Approval Workflow](#approval-workflow)
- [Customers](#customers)
- [Plans](#plans)
- [Templates](#templates)
- [Dashboard Stats](#dashboard-stats)
- [Email Logs](#email-logs)
- [Staff Management](#staff-management)
- [Enums & Constants](#enums--constants)
- [Error Handling](#error-handling)

---

## Authentication

Admin auth uses **email + password** (not OTP). The session is stored in an HTTP-only cookie named `admin_session` (8-hour expiry). The frontend does **not** need to manage tokens — the browser sends the cookie automatically on every request.

> The admin cookie (`admin_session`) is completely separate from the customer cookie (`auth_session`). A customer token cannot be used on admin endpoints and vice versa.

### Admin Roles

| Role | Access Level |
|------|-------------|
| `owner` | Full access. Can manage staff, change plan settings, upload templates. |
| `manager` | Can manage orders, view customers, view stats, approve orders. |
| `support` | Same as manager. |

### Login

```
POST /admin/auth/login
```

**Request Body:**
```json
{
  "email": "admin@ohsremote.com",
  "password": "your_password"
}
```

**Response `200`:**
```json
{
  "admin": {
    "id": 1,
    "email": "admin@ohsremote.com",
    "full_name": "System Admin",
    "role": "owner"
  }
}
```

**Response `401`:** Invalid credentials.

**Side effect:** Sets `admin_session` cookie (httpOnly, secure, sameSite=lax, maxAge=28800s).

### Get Current Admin

```
GET /admin/auth/me
```

**Response `200`:**
```json
{
  "id": 1,
  "email": "admin@ohsremote.com",
  "full_name": "System Admin",
  "role": "owner"
}
```

**Response `401`:** Not authenticated or session expired.

### Logout

```
POST /admin/auth/logout
```

**Response `200`:**
```json
{
  "message": "logged out"
}
```

**Side effect:** Deletes `admin_session` cookie.

### Change Password

```
POST /admin/auth/change-password
```

**Auth:** Any authenticated admin.

**Request Body:**
```json
{
  "current_password": "old_password",
  "new_password": "new_password_min_8_chars"
}
```

**Response `200`:**
```json
{
  "message": "password changed"
}
```

**Response `400`:** Current password incorrect or new password too short (min 8 chars).

---

## Order Management

### List All Orders

```
GET /admin/orders
```

**Auth:** Any admin role.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number (min 1) |
| `page_size` | int | 20 | Items per page (1-100) |
| `order_status` | string | null | Filter: `draft`, `processing`, `review_pending`, `available`, `cancelled` |
| `payment_status` | string | null | Filter: `pending`, `paid`, `failed`, `refunded` |
| `plan_id` | int | null | Filter by plan ID |
| `query` | string | null | Search by order ID (numeric) or company name (text) |

**Response `200`:**
```json
{
  "items": [
    {
      "order_id": 42,
      "created_at": "2026-04-01T14:30:00",
      "order_status": "review_pending",
      "payment_status": "paid",
      "total_amount": "99.99",
      "currency": "CAD",
      "jurisdiction": "ON",
      "company_name": "Acme Corp",
      "plan_name": "Basic",
      "user_email": "customer@example.com",
      "user_full_name": "John Doe",
      "is_industry_specific": false,
      "admin_notes": null
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

### List Orders Pending Review

```
GET /admin/orders/pending-review
```

**Auth:** Any admin role.

**Query Parameters:** `page`, `page_size` (same as above).

**Response:** Same shape as `GET /admin/orders`. Only returns orders with `order_status = "review_pending"`. Sorted oldest first (FIFO queue).

### Get Order Detail

```
GET /admin/orders/{order_id}
```

**Auth:** Any admin role.

**Response `200`:**
```json
{
  "order_id": 42,
  "created_at": "2026-04-01T14:30:00",
  "completed_at": null,
  "reviewed_at": null,
  "reviewed_by_admin_id": null,
  "jurisdiction": "ON",
  "total_amount": "99.99",
  "is_industry_specific": false,
  "admin_notes": null,
  "company_name": "Acme Corp",
  "plan_name": "Basic",
  "order_status": "review_pending",
  "payment_status": "paid",
  "currency": "CAD",
  "user_email": "customer@example.com",
  "user_full_name": "John Doe",
  "documents": [
    {
      "document_id": 15,
      "access_token": "abc123...",
      "token_expires_at": "2026-05-01T14:30:00",
      "generated_at": "2026-04-01T14:35:00",
      "file_format": "docx",
      "downloaded_count": 3
    }
  ],
  "email_logs": [
    {
      "id": 8,
      "order_id": 42,
      "recipient_email": "customer@example.com",
      "subject": "Your documents are ready",
      "status": "delivered",
      "sent_at": "2026-04-01T14:36:00",
      "failure_reason": null
    }
  ]
}
```

### Update Order Notes

```
PATCH /admin/orders/{order_id}/notes
```

**Auth:** Any admin role.

**Request Body:**
```json
{
  "admin_notes": "Reviewed company registration, all clear."
}
```

**Response `200`:** Full `AdminOrderDetailResponse` (same as GET detail).

### Resend Delivery Email

```
POST /admin/orders/{order_id}/resend-email
```

**Auth:** Any admin role. Order must have `payment_status = "paid"`.

**Response `200`:**
```json
{
  "message": "delivery email resent"
}
```

This re-triggers document generation (if no document exists) and sends the delivery email to the customer again. Useful when the customer reports they didn't receive it.

### Regenerate Document

```
POST /admin/orders/{order_id}/regenerate-document
```

**Auth:** Any admin role. Order must have `payment_status = "paid"`.

**Response `200`:**
```json
{
  "message": "document regenerated"
}
```

Use this after uploading an updated template. Generates a fresh document for the order using the current template.

---

## Approval Workflow

This is the core admin feature. When a plan has `requires_approval = true`, orders under that plan will **not** auto-deliver documents after payment. Instead, they enter `review_pending` status and wait for an admin to approve.

### How It Works

```
Customer pays
    |
    v
Plan has requires_approval?
    |               |
   YES              NO
    |               |
    v               v
Status: review_pending    Auto-generate doc + send email
    |                         Status: available
    v
Admin reviews order in dashboard
    |
    v
Admin clicks Approve
    |
    v
Document generated + email sent
Status: available
```

### Approve Order

```
POST /admin/orders/{order_id}/approve
```

**Auth:** Any admin role. Order must be in `review_pending` status.

**Request Body (optional):**
```json
{
  "admin_notes": "Approved after verifying company details."
}
```

**Response `200`:** Full `AdminOrderDetailResponse` with updated status.

**What happens on approve:**
1. Records which admin approved and when (`reviewed_by_admin_id`, `reviewed_at`)
2. Generates the document from the template
3. Sends the delivery email to the customer
4. Sets order status to `available` and records `completed_at`

**Response `400`:** Order is not in `review_pending` status.

---

## Customers

Read-only view of customers (the `users` table). Admins cannot modify customer data.

### List Customers

```
GET /admin/customers
```

**Auth:** Any admin role.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (1-100) |
| `query` | string | null | Search by email or full name |

**Response `200`:**
```json
{
  "items": [
    {
      "id": 5,
      "email": "customer@example.com",
      "full_name": "John Doe",
      "created_at": "2026-03-15T10:00:00",
      "last_login": "2026-04-05T09:30:00",
      "order_count": 3
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

### Get Customer Detail

```
GET /admin/customers/{user_id}
```

**Auth:** Any admin role.

**Response `200`:** Same shape as a single `AdminCustomerListItem` above.

---

## Plans

### List Plans

```
GET /admin/plans
```

**Auth:** Any admin role.

**Response `200`:**
```json
[
  {
    "id": 1,
    "slug": "basic",
    "name": "Basic",
    "description": "Basic OHS manual",
    "base_price": "99.99",
    "requires_approval": false
  },
  {
    "id": 2,
    "slug": "comprehensive",
    "name": "Comprehensive",
    "description": "Comprehensive OHS manual",
    "base_price": "199.99",
    "requires_approval": true
  }
]
```

### Toggle Approval Setting

```
PATCH /admin/plans/{plan_id}/approval-setting
```

**Auth:** `owner` only. Returns `403` for `manager`/`support`.

**Request Body:**
```json
{
  "requires_approval": true
}
```

**Response `200`:** Updated `AdminPlanResponse`.

This controls whether orders under this plan auto-deliver or require admin approval. Changing this only affects **future** orders — existing orders keep their current status.

---

## Templates

Document templates are `.docx` files used to generate customer documents. Each plan has one template named `{plan_slug}_manual_template.docx`.

### List Templates

```
GET /admin/templates
```

**Auth:** Any admin role.

**Response `200`:**
```json
[
  {
    "plan_slug": "basic",
    "filename": "basic_manual_template.docx",
    "file_size_bytes": 45678,
    "last_modified": "2026-03-20T15:00:00"
  },
  {
    "plan_slug": "comprehensive",
    "filename": "comprehensive_manual_template.docx",
    "file_size_bytes": 89012,
    "last_modified": "2026-03-20T15:00:00"
  }
]
```

### Upload Template

```
POST /admin/templates/{plan_slug}
```

**Auth:** `owner` only.

**Request:** `multipart/form-data` with a `file` field containing a `.docx` file.

```
Content-Type: multipart/form-data
file: (binary .docx file)
```

**Response `200`:**
```json
{
  "message": "template basic_manual_template.docx uploaded",
  "filename": "basic_manual_template.docx"
}
```

**Response `400`:** File is not `.docx`.

After uploading a new template, use `POST /admin/orders/{order_id}/regenerate-document` to regenerate documents for specific orders that should use the updated template.

### Download Template

```
GET /admin/templates/{plan_slug}/download
```

**Auth:** Any admin role.

**Response `200`:** Binary `.docx` file download.

**Response `404`:** Template not found.

---

## Dashboard Stats

### Get Dashboard Stats

```
GET /admin/stats/dashboard
```

**Auth:** Any admin role.

**Response `200`:**
```json
{
  "total_revenue": "15249.50",
  "total_orders": 203,
  "orders_by_status": {
    "draft": 12,
    "processing": 3,
    "review_pending": 5,
    "available": 180,
    "cancelled": 3
  },
  "orders_by_plan": {
    "Basic": 120,
    "Comprehensive": 83
  },
  "revenue_by_plan": {
    "Basic": "5999.40",
    "Comprehensive": "9250.10"
  },
  "pending_review_count": 5
}
```

`pending_review_count` is useful for a notification badge on the dashboard — it tells the admin how many orders are waiting for approval.

All monetary values are strings representing `Decimal` values in CAD.

---

## Email Logs

### List Email Logs

```
GET /admin/logs/emails
```

**Auth:** Any admin role.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (1-100) |
| `email_status` | string | null | Filter: `pending`, `sent`, `delivered`, `failed` |
| `order_id` | int | null | Filter by order ID |

**Response `200`:**
```json
{
  "items": [
    {
      "id": 8,
      "order_id": 42,
      "recipient_email": "customer@example.com",
      "subject": "Your documents are ready",
      "status": "delivered",
      "sent_at": "2026-04-01T14:36:00",
      "failure_reason": null
    }
  ],
  "total": 312,
  "page": 1,
  "page_size": 20,
  "total_pages": 16
}
```

---

## Staff Management

All staff endpoints require `owner` role. Non-owner admins get `403`.

### List Admin Staff

```
GET /admin/staff
```

**Response `200`:**
```json
[
  {
    "id": 1,
    "email": "admin@ohsremote.com",
    "full_name": "System Admin",
    "role": "owner",
    "is_active": true,
    "created_at": "2026-01-15T10:00:00",
    "last_login": "2026-04-06T08:00:00"
  },
  {
    "id": 2,
    "email": "manager@ohsremote.com",
    "full_name": "Jane Manager",
    "role": "manager",
    "is_active": true,
    "created_at": "2026-02-01T10:00:00",
    "last_login": "2026-04-05T14:30:00"
  }
]
```

### Create Admin Staff

```
POST /admin/staff
```

**Request Body:**
```json
{
  "email": "newadmin@ohsremote.com",
  "full_name": "New Admin",
  "password": "secure_password_min_8",
  "role": "manager"
}
```

Valid roles: `owner`, `manager`, `support`.

**Response `201`:** `AdminStaffListItem` of the created admin.

**Response `400`:** Email already exists, invalid role, or password too short.

### Deactivate Admin

```
PATCH /admin/staff/{admin_id}/deactivate
```

**Response `200`:** Updated `AdminStaffListItem` with `is_active: false`.

**Response `400`:** Cannot deactivate your own account.

Deactivated admins cannot log in. Their existing sessions are invalidated on next request.

---

## Enums & Constants

### Order Status Values
| Value | Description |
|-------|-------------|
| `draft` | Order created, payment not started |
| `processing` | Payment received, being processed |
| `review_pending` | Payment received, waiting for admin approval (when plan has `requires_approval = true`) |
| `available` | Documents generated and delivered to customer |
| `cancelled` | Order cancelled |

### Payment Status Values
| Value | Description |
|-------|-------------|
| `pending` | Awaiting payment |
| `paid` | Payment confirmed via Stripe |
| `failed` | Payment failed or checkout expired |
| `refunded` | Payment refunded |

### Email Status Values
| Value | Description |
|-------|-------------|
| `pending` | Email queued |
| `sent` | Email sent to SMTP server |
| `delivered` | Email delivered successfully |
| `failed` | Email delivery failed (check `failure_reason`) |

### Admin Roles
| Value | Description |
|-------|-------------|
| `owner` | Full access, can manage staff and settings |
| `manager` | Can manage orders, customers, view stats |
| `support` | Same access as manager |

---

## Error Handling

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": {}
  }
}
```

### Common HTTP Status Codes

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `201` | Created (staff creation) |
| `400` | Bad request (validation error, invalid state) |
| `401` | Not authenticated (missing or expired `admin_session` cookie) |
| `403` | Forbidden (insufficient role, e.g., `manager` trying to access `owner`-only endpoint) |
| `404` | Resource not found |
| `422` | Request validation error (missing/malformed fields) |
| `500` | Server error |

---

## Frontend Implementation Notes

### Authentication Flow
1. Show login form (email + password)
2. `POST /admin/auth/login` — cookie is set automatically by the browser
3. On app load, call `GET /admin/auth/me` to check if session is valid
4. If `401`, redirect to login
5. Store the admin's `role` from `/auth/me` to conditionally show owner-only features in the UI

### Cookie Configuration
The `admin_session` cookie is `httpOnly` so JavaScript cannot access it directly. The browser sends it automatically with every request. Make sure your HTTP client (axios, fetch) is configured with:
- `credentials: "include"` (fetch)
- `withCredentials: true` (axios)

### Suggested Dashboard Layout
1. **Top bar:** pending review count badge (from `GET /admin/stats/dashboard` → `pending_review_count`)
2. **Main sections:**
   - Orders table with filters (status, payment, plan, search)
   - Pending Review queue (dedicated view with approve button)
   - Customer list
   - Stats/analytics cards
3. **Settings area (owner only):**
   - Plan approval toggles
   - Template upload
   - Staff management

### Pagination Pattern
All paginated endpoints follow the same pattern:
```
?page=1&page_size=20
```
Response always includes `total`, `page`, `page_size`, `total_pages` for building pagination controls.

### OpenAPI / Swagger
The full interactive API docs are available at:
```
{API_BASE_URL}/docs
```
All admin endpoints are tagged under `admin` and `admin-auth`. You can test requests directly from there.
