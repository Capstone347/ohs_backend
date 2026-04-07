from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AdminOrderListItem(BaseModel):
    order_id: int
    created_at: datetime
    order_status: str
    payment_status: str
    total_amount: Decimal
    currency: str
    jurisdiction: str
    company_name: str | None = None
    plan_name: str | None = None
    user_email: str | None = None
    user_full_name: str | None = None
    is_industry_specific: bool
    admin_notes: str | None = None


class AdminPaginatedOrdersResponse(BaseModel):
    items: list[AdminOrderListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminEmailLogItem(BaseModel):
    id: int
    order_id: int
    recipient_email: str
    subject: str
    status: str
    sent_at: datetime
    failure_reason: str | None = None

    model_config = {"from_attributes": True}


class AdminDocumentSummary(BaseModel):
    document_id: int
    access_token: str
    token_expires_at: datetime
    generated_at: datetime
    file_format: str
    downloaded_count: int

    model_config = {"from_attributes": True}


class AdminOrderDetailResponse(BaseModel):
    order_id: int
    created_at: datetime
    completed_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_admin_id: int | None = None
    jurisdiction: str
    total_amount: Decimal
    is_industry_specific: bool
    admin_notes: str | None = None
    company_name: str | None = None
    plan_name: str | None = None
    order_status: str
    payment_status: str
    currency: str
    user_email: str | None = None
    user_full_name: str | None = None
    documents: list[AdminDocumentSummary] = []
    email_logs: list[AdminEmailLogItem] = []


class OrderApproveRequest(BaseModel):
    admin_notes: str | None = None


class AdminNotesUpdateRequest(BaseModel):
    admin_notes: str


class AdminCustomerListItem(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime | None = None
    last_login: datetime | None = None
    order_count: int = 0


class AdminPaginatedCustomersResponse(BaseModel):
    items: list[AdminCustomerListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminPlanResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None = None
    base_price: Decimal
    requires_approval: bool

    model_config = {"from_attributes": True}


class PlanApprovalSettingRequest(BaseModel):
    requires_approval: bool


class AdminStatsResponse(BaseModel):
    total_revenue: Decimal
    total_orders: int
    orders_by_status: dict[str, int]
    orders_by_plan: dict[str, int]
    revenue_by_plan: dict[str, Decimal]
    pending_review_count: int


class AdminPaginatedEmailLogsResponse(BaseModel):
    items: list[AdminEmailLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class TemplateListItem(BaseModel):
    plan_slug: str
    filename: str
    file_size_bytes: int
    last_modified: datetime


class CreateAdminUserRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "manager"


class AdminStaffListItem(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}
