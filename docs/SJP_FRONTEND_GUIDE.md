# SJP (Safe Job Procedures) — Frontend Integration Guide

This document covers everything the frontend team needs to implement the Industry-Specific SJP feature. It describes the three purchase paths, the full API contract, order lifecycle, and admin review workflows.

---

## Table of Contents

1. [Three Purchase Paths](#three-purchase-paths)
2. [Order Creation — Backend Gap](#order-creation--backend-gap)
3. [Customer Flow: Order Lifecycle](#customer-flow-order-lifecycle)
4. [Customer API Endpoints](#customer-api-endpoints)
5. [Admin API Endpoints](#admin-api-endpoints)
6. [Document Download](#document-download)
7. [Enums & Statuses](#enums--statuses)
8. [Schema Reference](#schema-reference)
9. [Polling Strategy](#polling-strategy)
10. [Email Delivery](#email-delivery)

---

## Three Purchase Paths

### Path 1: Manual Only (Basic or Comprehensive)

No changes needed. User selects a Basic or Comprehensive plan, pays, and receives a generated manual DOCX via email. This flow is unchanged.

### Path 2: Manual + SJP Add-On

- User selects **Basic** or **Comprehensive** plan AND enables the **Industry Specific** add-on.
- The order is created with `is_industry_specific = true`.
- After payment, the backend generates **two separate documents**:
  1. The standard manual DOCX (based on the plan)
  2. An AI-generated SJP DOCX (based on NAICS codes, province, and business description)
- **Admin approval is required** before delivery. The admin reviews AI-generated SJP content, can edit individual sections, and then approves.
- The delivery email includes **two download links** (one for the manual, one for the SJP document).

### Path 3: Standalone SJP

- User selects the **Industry Specific** plan only.
- The order is created with `is_industry_specific = true`.
- After payment, only an AI-generated SJP document is produced (no manual).
- **Admin approval is required** before delivery.
- The delivery email includes **one download link** for the SJP document.

---

## Order Creation — Backend Gap

**IMPORTANT**: The current `POST /api/v1/orders/` endpoint hardcodes `is_industry_specific = false` (line 164 in `orders.py`). The `OrderCreateRequest` schema does not include an `is_industry_specific` field.

### What the frontend needs

The backend must be updated to support setting `is_industry_specific`. There are two possible approaches:

**Option A — Explicit field**: Add `is_industry_specific: bool` to `OrderCreateRequest`. The frontend sends it explicitly based on the user's plan selection.

**Option B — Plan-based inference**: The backend infers `is_industry_specific` from the selected plan. If the plan is `industry_specific`, it's always `true`. If the plan is `basic` or `comprehensive` AND the user selected the SJP add-on, it's `true`. This requires either a separate flag or detecting the add-on selection.

Until this is resolved, **coordinate with the backend team** on which approach to use. The rest of this document assumes `is_industry_specific` is correctly set on the order after creation.

### Current Order Creation

```
POST /api/v1/orders/
Content-Type: application/json

{
  "plan_id": 3,            // integer, required — plan ID
  "user_email": "customer@example.com",
  "full_name": "John Doe",
  "jurisdiction": "Ontario"
}
```

Response (`201 Created`):
```json
{
  "order_id": 42,
  "status": "draft",
  "created_at": "2026-04-07T10:00:00Z",
  "message": "Order created successfully"
}
```

### Company Details (Required for SJP Orders)

After order creation, the frontend must submit company details including NAICS codes, province, and optional business description. This data is used by the AI to generate SJP content.

```
PATCH /api/v1/orders/{order_id}/company-details
Content-Type: multipart/form-data

Fields:
  company_name: string (required)
  province: string (required, e.g. "ON", "BC", "AB", "SK", "MB")
  naics_codes: string[] (required, each must be exactly 6 digits)
  business_description: string (optional but recommended — improves AI output quality)
  logo: file (optional, .png/.jpg/.jpeg/.gif/.webp)
```

**Supported provinces for SJP generation**: `ON`, `BC`, `AB`, `SK`, `MB`

Response (`200 OK`): Returns `OrderSummaryResponse` with updated company details.

### Industry Intake Questions (Optional Enhancement)

For industry-specific orders, the frontend can fetch dynamic intake questions based on NAICS codes:

```
GET /api/v1/industry/intake-questions?naics=236110,238210
```

And save answers:
```
PUT /api/v1/industry/{order_id}/intake-answers
```

---

## Customer Flow: Order Lifecycle

### Manual Only (Path 1)
```
DRAFT → (pay) → PAID → AVAILABLE
                  ↓
          (auto-generated, emailed)
```

### Industry-Specific Orders (Paths 2 & 3)
```
DRAFT → (pay) → PAID → PROCESSING → REVIEW_PENDING → AVAILABLE
                          ↓                  ↓              ↓
                    AI generates SJPs   Admin reviews   Email sent
                    (async, pollable)   & approves      with download links
```

### Order Status Values

| Status | Meaning for Frontend |
|--------|---------------------|
| `draft` | Order created, not yet paid |
| `processing` | Payment confirmed, AI is generating SJP content |
| `review_pending` | SJP generation complete, waiting for admin approval |
| `available` | Approved and delivered — documents ready for download |
| `cancelled` | Order was cancelled |

### What the frontend should show per status

- **`draft`**: Show order summary, payment button
- **`processing`**: Show progress indicator. Poll `GET /api/v1/sjp/{order_id}/status` for real-time progress (see [Polling Strategy](#polling-strategy))
- **`review_pending`**: Show "Your order is being reviewed by our team" message. No action required from the customer.
- **`available`**: Show download links for documents. Links are in the order detail or delivered via email.

---

## Customer API Endpoints

All customer SJP endpoints require authentication via the standard auth token (`Authorization: Bearer <token>`).

**Base URL**: `/api/v1/sjp`

### 1. Start SJP Generation (Manual Trigger)

> Note: For most flows, SJP generation starts automatically after payment via the Stripe webhook. This endpoint exists for manual re-triggering or testing.

```
POST /api/v1/sjp/{order_id}/generate
Content-Type: application/json

{
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"  // optional, auto-generated if omitted
}
```

Response (`201 Created`):
```json
{
  "job_id": 1,
  "status": "pending",
  "created_at": "2026-04-07T12:00:00Z"
}
```

Errors:
- `404`: Order not found
- `400`: Order not in correct state (must be paid + industry-specific) or missing industry profile (NAICS codes/province)

### 2. Poll SJP Generation Status

```
GET /api/v1/sjp/{order_id}/status
```

Response (`200 OK`):
```json
{
  "job_id": 10,
  "order_id": 123,
  "status": "generating_sjps",
  "created_at": "2026-04-07T12:00:00Z",
  "updated_at": "2026-04-07T12:11:00Z",
  "toc_generated_at": "2026-04-07T12:03:00Z",
  "completed_at": null,
  "failed_at": null,
  "error_message": null,
  "progress": {
    "completed_sjps": 5,
    "total_sjps": 12,
    "progress_ratio": 0.4167
  },
  "toc_entries": [
    {
      "toc_entry_id": 1,
      "title": "Working at Heights",
      "status": "completed",
      "is_completed": true,
      "generated_at": "2026-04-07T12:10:00Z",
      "error_message": null
    },
    {
      "toc_entry_id": 2,
      "title": "Confined Space Entry",
      "status": "generating",
      "is_completed": false,
      "generated_at": null,
      "error_message": null
    }
  ]
}
```

**Key fields for UI**:
- `status`: Overall job status (see [SJP Generation Statuses](#sjp-generation-statuses))
- `progress.progress_ratio`: Float 0.0–1.0, use for progress bar
- `progress.completed_sjps` / `progress.total_sjps`: "5 of 12 procedures generated"
- `toc_entries`: Individual SJP statuses — show as a checklist

### 3. Get Full SJP Content

Returns all generated SJP content for the order. Available once generation is complete or partially complete.

```
GET /api/v1/sjp/{order_id}/content
```

Response (`200 OK`):
```json
{
  "job_id": 10,
  "order_id": 123,
  "province": "ON",
  "naics_codes": ["236110", "238210"],
  "status": "completed",
  "disclaimer": "This document is intended to reflect Ontario OHS legislation...",
  "entries": [
    {
      "toc_entry_id": 1,
      "title": "Working at Heights",
      "position": 1,
      "status": "completed",
      "sections": {
        "task_description": "A detailed description of the working at heights task...",
        "required_ppe": ["Hard hat", "Safety harness", "Non-slip footwear"],
        "step_by_step_instructions": ["Inspect all fall protection equipment", "Secure anchor points", "..."],
        "identified_hazards": ["Falls from elevation", "Falling objects", "..."],
        "control_measures": ["Use guardrails where possible", "Implement buddy system", "..."],
        "training_requirements": ["Working at Heights certification", "Fall protection training", "..."],
        "emergency_procedures": "In case of a fall: activate emergency response plan...",
        "legislative_references": "Ontario Regulation 213/91, Construction Projects, s. 26.1..."
      },
      "generated_at": "2026-04-07T12:10:00Z",
      "error_message": null
    }
  ]
}
```

### 4. Get Single SJP Entry Content

```
GET /api/v1/sjp/{order_id}/content/{toc_entry_id}
```

Response (`200 OK`): Returns a single `SjpContentResponse` object (same shape as one entry in the `entries` array above).

---

## Admin API Endpoints

All admin endpoints require admin authentication (`Authorization: Bearer <admin_token>`).

**Base URL**: `/api/v1/admin`

### 1. List Pending Review Orders (Existing)

SJP orders that need review appear in the existing pending review list:

```
GET /api/v1/admin/orders/pending-review?page=1&page_size=20
```

Orders with `is_industry_specific = true` should be displayed with an SJP indicator in the admin UI.

### 2. View SJP Content for Review

```
GET /api/v1/admin/orders/{order_id}/sjp-content
```

Response (`200 OK`): Same shape as `SjpFullContentResponse` (see [Get Full SJP Content](#3-get-full-sjp-content) above). Admins see all SJP entries with their 7 sections for review.

### 3. Edit Individual SJP Section

Admins can modify any of the 7 sections of a specific SJP before approving. All fields are optional — only send the fields you want to change.

```
PATCH /api/v1/admin/sjp-content/{toc_entry_id}
Content-Type: application/json

{
  "task_description": "Updated task description with admin corrections...",
  "required_ppe": ["Hard hat", "Safety harness", "Safety glasses"],
  "control_measures": ["Updated control measure 1", "Updated control measure 2"]
}
```

Response (`200 OK`):
```json
{
  "message": "content updated",
  "toc_entry_id": 1
}
```

**Editable fields** (all optional, partial update):
| Field | Type |
|-------|------|
| `task_description` | `string` |
| `required_ppe` | `string[]` |
| `step_by_step_instructions` | `string[]` |
| `identified_hazards` | `string[]` |
| `control_measures` | `string[]` |
| `training_requirements` | `string[]` |
| `emergency_procedures` | `string` |
| `legislative_references` | `string` |

### 4. Regenerate Single SJP

If an admin is unhappy with the AI output for a specific SJP, they can trigger re-generation:

```
POST /api/v1/admin/sjp-content/{toc_entry_id}/regenerate
```

Response (`200 OK`):
```json
{
  "message": "regeneration started",
  "toc_entry_id": 1
}
```

This re-runs the AI generation for that specific SJP entry. The entry's status will cycle through `pending` → `generating` → `completed`/`failed`. The admin should poll or refresh to see the new content.

### 5. Approve Order (Existing, Updated)

The existing approval endpoint now handles SJP orders:

```
POST /api/v1/admin/orders/{order_id}/approve
Content-Type: application/json

{
  "admin_notes": "Reviewed all SJPs, approved for delivery"  // optional
}
```

**Important**: Approval will fail if the SJP generation job is not in `completed` status. The backend validates this before allowing approval.

On approval:
- The SJP document (DOCX) is assembled from the reviewed/edited content
- For add-on orders (Path 2): both the manual and SJP documents are generated
- Delivery email is sent with download link(s)
- Order status transitions to `available`

---

## Document Download

Documents are access-gated via tokens. The download links are included in the delivery email and in the order detail response.

### Download by Document ID

```
GET /api/v1/documents/{document_id}/download?token={access_token}
```

### Download by Order ID (Latest)

```
GET /api/v1/documents/orders/{order_id}/download?token={access_token}
```

**Notes**:
- Access tokens are 64-character hex strings
- Tokens expire after 30 days
- For add-on orders (Path 2), there are 2 separate documents with 2 separate tokens and download links
- The `documents` array in `OrderDetailResponse` contains all document records with their `document_id`, `access_token`, and `token_expires_at`

---

## Enums & Statuses

### Order Status (`OrderStatusEnum`)

| Value | Description |
|-------|-------------|
| `draft` | Order created, payment not initiated |
| `processing` | Payment confirmed, AI generation in progress |
| `review_pending` | Generation complete, awaiting admin approval |
| `available` | Approved and delivered |
| `cancelled` | Order cancelled |

### Payment Status (`PaymentStatus`)

| Value | Description |
|-------|-------------|
| `pending` | Payment not yet received |
| `paid` | Payment confirmed |
| `failed` | Payment failed |
| `refunded` | Payment was refunded |

### SJP Generation Job Status (`SjpGenerationStatus`)

| Value | Description | Frontend Action |
|-------|-------------|-----------------|
| `pending` | Job created, not started | Show spinner |
| `generating_toc` | AI generating table of contents | Show "Generating procedure list..." |
| `generating_sjps` | AI generating individual SJP content | Show progress bar using `progress_ratio` |
| `completed` | All SJPs generated successfully | Show "Waiting for review" |
| `failed` | Generation failed | Show error message from `error_message` field |

### SJP Content Status (per entry)

| Value | Description |
|-------|-------------|
| `pending` | Not yet started |
| `generating` | AI currently generating |
| `completed` | Content generated successfully |
| `failed` | Generation failed for this entry |

### Plan Slugs

| Slug | Name | SJP Behavior |
|------|------|-------------|
| `basic` | Basic | Manual only (unless `is_industry_specific`) |
| `comprehensive` | Comprehensive | Manual only (unless `is_industry_specific`) |
| `industry_specific` | Industry Specific | SJP only, always `is_industry_specific = true` |

---

## Schema Reference

### SjpContentSections

The 7 sections that make up each Safe Job Procedure:

```typescript
interface SjpContentSections {
  task_description: string;           // Detailed description of the task
  required_ppe: string[];             // Personal Protective Equipment list
  step_by_step_instructions: string[]; // Ordered procedure steps
  identified_hazards: string[];        // List of identified hazards
  control_measures: string[];          // Hazard control measures
  training_requirements: string[];     // Required training/certifications
  emergency_procedures: string;        // Emergency response text
  legislative_references: string | null; // Province-specific legal references
}
```

### SjpContentResponse

```typescript
interface SjpContentResponse {
  toc_entry_id: number;
  title: string;
  position: number;
  status: "pending" | "generating" | "completed" | "failed";
  sections: SjpContentSections | null; // null if not yet generated
  generated_at: string | null;         // ISO 8601 timestamp
  error_message: string | null;
}
```

### SjpFullContentResponse

```typescript
interface SjpFullContentResponse {
  job_id: number;
  order_id: number;
  province: string;          // e.g. "ON"
  naics_codes: string[];     // e.g. ["236110", "238210"]
  status: string;            // SJP generation job status
  disclaimer: string;        // Legal disclaimer text for the province
  entries: SjpContentResponse[];
}
```

### SjpGenerationStatusResponse

```typescript
interface SjpGenerationStatusResponse {
  job_id: number;
  order_id: number;
  status: "pending" | "generating_toc" | "generating_sjps" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  toc_generated_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  progress: {
    completed_sjps: number;
    total_sjps: number;
    progress_ratio: number;  // 0.0 to 1.0
  };
  toc_entries: Array<{
    toc_entry_id: number;
    title: string;
    status: string;
    is_completed: boolean;
    generated_at: string | null;
    error_message: string | null;
  }>;
}
```

### SjpContentEditRequest (Admin)

```typescript
interface SjpContentEditRequest {
  task_description?: string;
  required_ppe?: string[];
  step_by_step_instructions?: string[];
  identified_hazards?: string[];
  control_measures?: string[];
  training_requirements?: string[];
  emergency_procedures?: string;
  legislative_references?: string;
}
```

### OrderDetailResponse (Updated Fields)

The existing `OrderDetailResponse` now includes:
- `is_industry_specific: boolean` — indicates if the order has SJP generation
- `documents: DocumentSummary[]` — may contain 1 document (standalone SJP or manual) or 2 documents (manual + SJP for add-on orders)

---

## Polling Strategy

When an order is in `processing` status, the frontend should poll the SJP generation status endpoint to show real-time progress.

### Recommended Approach

```
GET /api/v1/sjp/{order_id}/status
```

**Polling intervals**:
- Poll every **3 seconds** while `status` is `generating_toc` (fast phase, usually < 30s)
- Poll every **5 seconds** while `status` is `generating_sjps` (slower phase, depends on number of SJPs)
- **Stop polling** when `status` is `completed` or `failed`

### UI Progression

1. **`pending`** → "Starting generation..."
2. **`generating_toc`** → "Analyzing your industry and generating procedure list..."
3. **`generating_sjps`** → Show progress bar:
   - Use `progress.progress_ratio` (0.0–1.0) for the bar fill
   - Show `progress.completed_sjps` / `progress.total_sjps` as text (e.g. "8 of 15 procedures generated")
   - Optionally show the `toc_entries` list as a checklist with checkmarks for completed items
4. **`completed`** → "Generation complete! Your order is now under review."
5. **`failed`** → Show `error_message` with a retry option (call `POST /sjp/{order_id}/generate`)

---

## Email Delivery

The backend sends delivery emails automatically when an admin approves the order. No frontend action is needed for this.

### Standalone SJP (Path 3)
- Email contains 1 download link for the SJP document
- Shows the number of SJPs generated

### Manual + SJP Add-On (Path 2)
- Email contains 2 download links: one for the manual, one for the SJP document
- Shows the SJP count alongside the manual download

### Admin Resend Email

Admins can resend the delivery email:
```
POST /api/v1/admin/orders/{order_id}/resend-email
```

---

## Frontend Implementation Checklist

### Customer-Facing

- [ ] Update plan selection UI to support Industry Specific plan and add-on toggle for Basic/Comprehensive
- [ ] Ensure `is_industry_specific` is correctly set on order creation (coordinate with backend)
- [ ] Show company details form with NAICS codes, province, and business description fields
- [ ] Implement SJP generation progress page with polling (for `processing` status)
- [ ] Show "Under Review" state for `review_pending` orders
- [ ] Display download links for both documents on `available` orders (add-on has 2 links)

### Admin-Facing

- [ ] Add SJP indicator badge on order list items where `is_industry_specific = true`
- [ ] Build SJP content review page: show all 7 sections for each SJP entry
- [ ] Implement inline editing for each SJP section (PATCH endpoint)
- [ ] Add "Regenerate" button per SJP entry (POST endpoint)
- [ ] Ensure approve button is only enabled when SJP generation status is `completed`
- [ ] Handle the case where some entries failed — show error and offer regenerate
